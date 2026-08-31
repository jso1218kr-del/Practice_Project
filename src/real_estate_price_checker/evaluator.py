"""유사 거래의 단가 분포로 예상 거래가격을 평가한다."""

from datetime import date, datetime

import pandas as pd

from real_estate_price_checker.comparable_search import find_comparables
from real_estate_price_checker.data_loader import find_address_coordinates

MINIMUM_COMPARABLE_COUNT = 3


def _comparable_records(comparables: pd.DataFrame) -> list[dict[str, object]]:
    """CLI나 후속 화면에서 근거로 보여줄 최소 컬럼만 일반 Python 값으로 바꾼다."""
    records: list[dict[str, object]] = []
    for row in comparables.itertuples(index=False):
        records.append(
            {
                "transaction_id": row.transaction_id,
                "address": row.address,
                "contract_date": row.contract_date.strftime("%Y-%m-%d"),
                "price_krw": int(row.price_krw),
                "exclusive_area_m2": float(row.exclusive_area_m2),
                "distance_m": round(float(row.distance_m), 1),
            }
        )
    return records


def evaluate_property(
    transactions: pd.DataFrame,
    *,
    address: str,
    expected_price_krw: int,
    exclusive_area_m2: float,
    floor: int,
    build_year: int,
    valuation_date: str | date | datetime | pd.Timestamp,
    property_type: str = "아파트",
    transaction_type: str = "매매",
) -> dict[str, object]:
    """비교 거래를 검색하고 예상가격의 적정 여부와 근거를 반환한다."""
    if expected_price_krw <= 0:
        raise ValueError("예상 거래가격은 0보다 커야 합니다.")
    if exclusive_area_m2 <= 0:
        raise ValueError("전용면적은 0보다 커야 합니다.")

    latitude, longitude = find_address_coordinates(transactions, address)
    comparables = find_comparables(
        transactions,
        target_latitude=latitude,
        target_longitude=longitude,
        exclusive_area_m2=exclusive_area_m2,
        build_year=build_year,
        valuation_date=valuation_date,
        property_type=property_type,
        transaction_type=transaction_type,
    )

    warnings = [
        "학습용 가상 데이터 기반 결과입니다.",
        f"입력한 {floor}층 정보는 1단계 가격 계산에 아직 반영하지 않습니다.",
    ]
    result: dict[str, object] = {
        "status": "INSUFFICIENT_DATA",
        "estimated_price_krw": None,
        "lower_price_krw": None,
        "upper_price_krw": None,
        "difference_amount_krw": None,
        "difference_percent": None,
        "comparable_count": len(comparables),
        "comparables": _comparable_records(comparables),
        "methodology": "반경 1km 유사 거래의 ㎡당 가격 중앙값과 20·80분위수",
        "warnings": warnings,
    }

    if len(comparables) < MINIMUM_COMPARABLE_COUNT:
        warnings.append("유사 거래가 3건 미만이므로 가격을 판정하지 않았습니다.")
        return result

    price_per_m2 = comparables["price_per_m2"]
    estimated_price = round(float(price_per_m2.median()) * exclusive_area_m2)
    lower_price = round(float(price_per_m2.quantile(0.20)) * exclusive_area_m2)
    upper_price = round(float(price_per_m2.quantile(0.80)) * exclusive_area_m2)

    if expected_price_krw < lower_price:
        status = "UNDERPRICED"
    elif expected_price_krw > upper_price:
        status = "OVERPRICED"
    else:
        status = "FAIR"

    difference_amount = expected_price_krw - estimated_price
    result.update(
        {
            "status": status,
            "estimated_price_krw": estimated_price,
            "lower_price_krw": lower_price,
            "upper_price_krw": upper_price,
            "difference_amount_krw": difference_amount,
            "difference_percent": round(difference_amount / estimated_price * 100, 2),
        }
    )
    return result

