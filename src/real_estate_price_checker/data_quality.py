"""국토교통부 아파트 매매 CSV를 탐색하고 학습용 표준 형태로 정리한다."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pandas as pd

ENCODING_CANDIDATES = ("utf-8-sig", "cp949")

# 내려받기 시점이나 제공 화면에 따라 달라지는 헤더를 내부 표준 이름으로 모은다.
COLUMN_ALIASES = {
    "district": ("시군구",),
    "lot_number": ("번지",),
    "complex_name": ("단지명",),
    "exclusive_area_m2": ("전용면적(㎡)", "전용면적", "전용면적(m2)"),
    "contract_year_month": ("계약년월",),
    "contract_day": ("계약일",),
    "price_10k_krw": ("거래금액(만원)", "거래금액"),
    "floor": ("층",),
    "build_year": ("건축년도", "건축연도"),
    "road_name": ("도로명",),
    "cancellation_date": ("해제사유발생일", "해제사유 발생일"),
    "cancellation_flag": ("해제여부", "취소여부"),
}

REQUIRED_STANDARD_COLUMNS = {
    "district",
    "complex_name",
    "exclusive_area_m2",
    "contract_year_month",
    "contract_day",
    "price_10k_krw",
    "floor",
    "build_year",
}


@dataclass(frozen=True)
class DataQualityResult:
    """원본 탐색 결과와 정제된 거래를 함께 전달한다."""

    cleaned: pd.DataFrame
    report: dict[str, object]


def _normalize_header(value: object) -> str:
    """BOM, 줄바꿈, 중복 공백을 제거해 헤더 비교가 가능하게 만든다."""
    return "".join(str(value).replace("\ufeff", "").split())


def read_molit_csv(csv_path: str | Path) -> tuple[pd.DataFrame, str]:
    """UTF-8 우선, 실패 시 CP949로 원본 값을 문자열 그대로 읽는다."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {path}")

    for encoding in ENCODING_CANDIDATES:
        try:
            frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding=encoding)
        except UnicodeDecodeError:
            continue
        frame.columns = [_normalize_header(column) for column in frame.columns]
        return frame, encoding

    tried = ", ".join(ENCODING_CANDIDATES)
    raise ValueError(f"CSV 인코딩을 읽을 수 없습니다. 시도한 인코딩: {tried}")


def inspect_columns(frame: pd.DataFrame) -> list[dict[str, object]]:
    """각 원본 컬럼의 비어 있는 값과 대표 값을 반환한다."""
    profiles: list[dict[str, object]] = []
    for column in frame.columns:
        values = frame[column].fillna("").astype(str).str.strip()
        non_empty = values[values.ne("")]
        profiles.append(
            {
                "column": column,
                "dtype": str(frame[column].dtype),
                "missing_count": int(values.eq("").sum()),
                "unique_count": int(non_empty.nunique()),
                "sample_values": non_empty.drop_duplicates().head(3).tolist(),
            }
        )
    return profiles


def standardize_molit_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """알고 있는 국토교통부 컬럼명을 영문 내부 표준 이름으로 바꾼다."""
    normalized_to_actual = {_normalize_header(column): column for column in frame.columns}
    rename_map: dict[str, str] = {}

    for standard_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            actual = normalized_to_actual.get(_normalize_header(alias))
            if actual is not None:
                rename_map[actual] = standard_name
                break

    standardized = frame.rename(columns=rename_map).copy()
    missing = REQUIRED_STANDARD_COLUMNS - set(standardized.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"정제에 필요한 컬럼을 찾지 못했습니다: {missing_text}")
    return standardized


def _clean_numeric(series: pd.Series) -> pd.Series:
    """천 단위 쉼표와 공백을 제거한 뒤 숫자로 변환한다."""
    normalized = series.astype(str).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(normalized, errors="coerce")


def _cancelled_mask(frame: pd.DataFrame) -> pd.Series:
    cancelled = pd.Series(False, index=frame.index)
    if "cancellation_date" in frame:
        dates = frame["cancellation_date"].fillna("").astype(str).str.strip()
        cancelled |= dates.ne("")
    if "cancellation_flag" in frame:
        values = frame["cancellation_flag"].fillna("").astype(str).str.strip().str.lower()
        cancelled |= values.isin({"y", "yes", "true", "1", "취소", "해제"})
    return cancelled


def _transaction_ids(frame: pd.DataFrame) -> pd.Series:
    """원본에 거래 ID가 없어 주요 값의 해시로 재현 가능한 ID를 만든다."""
    if frame.empty:
        return pd.Series(index=frame.index, dtype=str)

    identity_columns = [
        "district",
        "lot_number",
        "complex_name",
        "contract_date",
        "price_krw",
        "exclusive_area_m2",
        "floor",
    ]

    def make_id(row: pd.Series) -> str:
        text = "|".join(str(row.get(column, "")) for column in identity_columns)
        return f"MOLIT-{sha256(text.encode('utf-8')).hexdigest()[:12].upper()}"

    return frame.apply(make_id, axis=1)


def _price_outlier_mask(price_per_m2: pd.Series) -> pd.Series:
    """IQR 1.5배 밖의 단가를 검토 대상으로 표시한다."""
    if len(price_per_m2) < 4:
        return pd.Series(False, index=price_per_m2.index)
    first_quartile = price_per_m2.quantile(0.25)
    third_quartile = price_per_m2.quantile(0.75)
    iqr = third_quartile - first_quartile
    lower_bound = first_quartile - 1.5 * iqr
    upper_bound = third_quartile + 1.5 * iqr
    return ~price_per_m2.between(lower_bound, upper_bound)


def clean_molit_transactions(
    frame: pd.DataFrame,
    *,
    encoding: str = "unknown",
) -> DataQualityResult:
    """원본 거래를 표준화하고 제외·검토 건수를 품질 보고서에 남긴다."""
    standardized = standardize_molit_columns(frame)
    raw_row_count = len(standardized)

    missing_by_column = {
        column: int(
            (
                standardized[column].isna()
                | standardized[column].fillna("").astype(str).str.strip().eq("")
            ).sum()
        )
        for column in REQUIRED_STANDARD_COLUMNS
    }

    for column in ("district", "lot_number", "complex_name", "road_name"):
        if column not in standardized:
            standardized[column] = ""
        standardized[column] = standardized[column].fillna("").astype(str).str.strip()

    standardized["exclusive_area_m2"] = _clean_numeric(standardized["exclusive_area_m2"])
    price_10k_krw = _clean_numeric(standardized["price_10k_krw"])
    standardized["price_krw"] = price_10k_krw * 10_000
    standardized["floor"] = _clean_numeric(standardized["floor"])
    standardized["build_year"] = _clean_numeric(standardized["build_year"])

    year_month = standardized["contract_year_month"].astype(str).str.strip()
    day = standardized["contract_day"].astype(str).str.strip().str.zfill(2)
    standardized["contract_date"] = pd.to_datetime(
        year_month + day,
        format="%Y%m%d",
        errors="coerce",
    )
    standardized["is_cancelled"] = _cancelled_mask(standardized)

    duplicate_subset = [
        "district",
        "lot_number",
        "complex_name",
        "exclusive_area_m2",
        "contract_date",
        "price_krw",
        "floor",
        "build_year",
        "is_cancelled",
    ]
    duplicate_mask = standardized.duplicated(subset=duplicate_subset, keep="first")

    invalid_mask = (
        standardized["district"].eq("")
        | standardized["complex_name"].eq("")
        | standardized["contract_date"].isna()
        | standardized["price_krw"].isna()
        | standardized["price_krw"].le(0)
        | standardized["exclusive_area_m2"].isna()
        | standardized["exclusive_area_m2"].le(0)
        | standardized["floor"].isna()
        | standardized["build_year"].isna()
        | standardized["build_year"].le(0)
    )

    cancelled_exclusion_mask = standardized["is_cancelled"] & ~duplicate_mask & ~invalid_mask
    usable_mask = ~duplicate_mask & ~invalid_mask & ~cancelled_exclusion_mask
    cleaned = standardized.loc[usable_mask].copy()
    cleaned["address"] = (
        cleaned["district"]
        + " "
        + cleaned["road_name"].where(cleaned["road_name"].ne(""), cleaned["lot_number"])
    ).str.strip()
    cleaned["price_krw"] = cleaned["price_krw"].astype("int64")
    cleaned["floor"] = cleaned["floor"].astype("int64")
    cleaned["build_year"] = cleaned["build_year"].astype("int64")
    cleaned["price_per_m2"] = cleaned["price_krw"] / cleaned["exclusive_area_m2"]
    cleaned["is_price_outlier"] = _price_outlier_mask(cleaned["price_per_m2"])
    cleaned["transaction_id"] = _transaction_ids(cleaned)
    cleaned["property_type"] = "아파트"
    cleaned["transaction_type"] = "매매"

    output_columns = [
        "transaction_id",
        "address",
        "district",
        "lot_number",
        "road_name",
        "complex_name",
        "contract_date",
        "price_krw",
        "exclusive_area_m2",
        "floor",
        "build_year",
        "property_type",
        "transaction_type",
        "is_cancelled",
        "price_per_m2",
        "is_price_outlier",
    ]
    cleaned = cleaned[output_columns].sort_values("contract_date").reset_index(drop=True)

    report: dict[str, object] = {
        "encoding": encoding,
        "raw_row_count": raw_row_count,
        "raw_column_count": len(frame.columns),
        "missing_by_required_column": dict(sorted(missing_by_column.items())),
        "duplicate_count": int(duplicate_mask.sum()),
        "invalid_count": int((invalid_mask & ~duplicate_mask).sum()),
        "cancelled_count": int(cancelled_exclusion_mask.sum()),
        "cleaned_row_count": len(cleaned),
        "cleaned_dtypes": {column: str(dtype) for column, dtype in cleaned.dtypes.items()},
        "price_outlier_count": int(cleaned["is_price_outlier"].sum()),
        "column_profiles": inspect_columns(frame),
    }
    return DataQualityResult(cleaned=cleaned, report=report)


def load_and_clean_molit_csv(csv_path: str | Path) -> DataQualityResult:
    """CSV 읽기와 정제를 한 번에 실행한다."""
    frame, encoding = read_molit_csv(csv_path)
    return clean_molit_transactions(frame, encoding=encoding)
