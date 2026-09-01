from pathlib import Path

import pandas as pd
import pytest

from real_estate_price_checker.data_quality import (
    clean_molit_transactions,
    load_and_clean_molit_csv,
    read_molit_csv,
    standardize_molit_columns,
)

SAMPLE_MOLIT_PATH = Path(__file__).parents[1] / "data" / "sample" / "molit_transactions.csv"


def test_sample_report_explains_why_rows_were_excluded() -> None:
    result = load_and_clean_molit_csv(SAMPLE_MOLIT_PATH)

    assert result.report["raw_row_count"] == 8
    assert result.report["duplicate_count"] == 1
    assert result.report["invalid_count"] == 1
    assert result.report["cancelled_count"] == 1
    assert result.report["cleaned_row_count"] == 5
    assert result.report["price_outlier_count"] == 1
    assert result.report["cleaned_dtypes"]["contract_date"].startswith("datetime64")


def test_cleaned_transactions_have_model_friendly_types() -> None:
    result = load_and_clean_molit_csv(SAMPLE_MOLIT_PATH)
    cleaned = result.cleaned

    assert pd.api.types.is_datetime64_any_dtype(cleaned["contract_date"])
    assert pd.api.types.is_integer_dtype(cleaned["price_krw"])
    assert pd.api.types.is_float_dtype(cleaned["exclusive_area_m2"])
    assert cleaned["is_cancelled"].eq(False).all()
    assert cleaned["transaction_id"].is_unique
    assert cleaned.loc[0, "price_krw"] == 500_000_000


def test_price_outlier_is_flagged_instead_of_deleted() -> None:
    result = load_and_clean_molit_csv(SAMPLE_MOLIT_PATH)
    outliers = result.cleaned.loc[result.cleaned["is_price_outlier"]]

    assert len(outliers) == 1
    assert outliers.iloc[0]["complex_name"] == "검토아파트"


def test_cp949_csv_is_read_when_utf8_fails(tmp_path: Path) -> None:
    cp949_path = tmp_path / "cp949.csv"
    cp949_path.write_bytes(SAMPLE_MOLIT_PATH.read_text(encoding="utf-8").encode("cp949"))

    frame, encoding = read_molit_csv(cp949_path)

    assert encoding == "cp949"
    assert frame.iloc[0]["단지명"] == "학습아파트"


def test_missing_required_column_has_clear_error() -> None:
    frame = pd.DataFrame({"시군구": ["서울특별시 학습구"]})

    with pytest.raises(ValueError, match="정제에 필요한 컬럼"):
        standardize_molit_columns(frame)


def test_header_whitespace_and_aliases_are_normalized() -> None:
    frame = pd.DataFrame(
        {
            " 시군구 ": ["서울특별시 학습구"],
            "단지명": ["학습아파트"],
            "전용면적": ["84"],
            "계약년월": ["202501"],
            "계약일": ["1"],
            "거래금액": ["50,000"],
            "층": ["10"],
            "건축연도": ["2015"],
        }
    )

    result = clean_molit_transactions(frame)

    assert len(result.cleaned) == 1
    assert result.cleaned.iloc[0]["price_krw"] == 500_000_000


def test_all_invalid_rows_return_an_empty_result() -> None:
    frame = pd.DataFrame(
        {
            "시군구": ["서울특별시 학습구"],
            "단지명": ["결측아파트"],
            "전용면적": [None],
            "계약년월": ["202501"],
            "계약일": ["1"],
            "거래금액": ["50,000"],
            "층": ["10"],
            "건축연도": ["2015"],
        }
    )

    result = clean_molit_transactions(frame)

    assert result.cleaned.empty
    assert result.report["missing_by_required_column"]["exclusive_area_m2"] == 1
    assert result.report["invalid_count"] == 1
