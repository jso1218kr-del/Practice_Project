"""학습용 거래 CSV를 읽고 주소 좌표를 찾는다."""

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "transaction_id",
    "address",
    "latitude",
    "longitude",
    "contract_date",
    "price_krw",
    "exclusive_area_m2",
    "floor",
    "build_year",
    "property_type",
    "transaction_type",
    "is_cancelled",
}


class AddressNotFoundError(ValueError):
    """입력 주소가 학습용 샘플 데이터에 없을 때 발생한다."""


def load_transactions(csv_path: str | Path) -> pd.DataFrame:
    """CSV를 읽고 이후 계산에 필요한 날짜와 취소 여부 타입을 정리한다."""
    transactions = pd.read_csv(csv_path, parse_dates=["contract_date"])

    missing_columns = REQUIRED_COLUMNS - set(transactions.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"CSV에 필수 컬럼이 없습니다: {missing}")

    # CSV 작성 방식에 따라 True/False가 문자열로 읽힐 수 있어 한 번 명시적으로 정규화한다.
    if transactions["is_cancelled"].dtype != bool:
        normalized = transactions["is_cancelled"].astype(str).str.strip().str.lower()
        valid_values = {"true", "false"}
        if not set(normalized.unique()).issubset(valid_values):
            raise ValueError("is_cancelled 값은 true 또는 false여야 합니다.")
        transactions["is_cancelled"] = normalized.eq("true")

    return transactions


def find_address_coordinates(transactions: pd.DataFrame, address: str) -> tuple[float, float]:
    """샘플 거래 중 입력 주소와 정확히 일치하는 첫 좌표를 반환한다."""
    normalized_address = address.strip()
    matches = transactions.loc[transactions["address"].str.strip() == normalized_address]

    if matches.empty:
        raise AddressNotFoundError(
            "현재 학습용 버전에서는 샘플 데이터에 등록된 주소만 사용할 수 있습니다. "
            "실제 주소 좌표 변환은 이후 단계에서 추가합니다."
        )

    first_match = matches.iloc[0]
    return float(first_match["latitude"]), float(first_match["longitude"])

