"""평가 대상과 조건이 비슷한 과거 거래를 찾는다."""

from datetime import date, datetime

import pandas as pd

from real_estate_price_checker.distance import haversine_distance_m


def find_comparables(
    transactions: pd.DataFrame,
    *,
    target_latitude: float,
    target_longitude: float,
    exclusive_area_m2: float,
    build_year: int,
    valuation_date: str | date | datetime | pd.Timestamp,
    property_type: str,
    transaction_type: str,
    radius_m: float = 1_000,
    area_tolerance_ratio: float = 0.10,
    build_year_tolerance: int = 10,
    lookback_months: int = 24,
) -> pd.DataFrame:
    """1단계의 단순 규칙을 모두 만족하는 비교 거래만 반환한다."""
    valuation_timestamp = pd.Timestamp(valuation_date)
    earliest_contract_date = valuation_timestamp - pd.DateOffset(months=lookback_months)
    minimum_area = exclusive_area_m2 * (1 - area_tolerance_ratio)
    maximum_area = exclusive_area_m2 * (1 + area_tolerance_ratio)

    candidates = transactions.copy()
    candidates["distance_m"] = candidates.apply(
        lambda row: haversine_distance_m(
            target_latitude,
            target_longitude,
            float(row["latitude"]),
            float(row["longitude"]),
        ),
        axis=1,
    )

    mask = (
        (candidates["distance_m"] <= radius_m)
        & (candidates["property_type"] == property_type)
        & (candidates["transaction_type"] == transaction_type)
        & (candidates["contract_date"] < valuation_timestamp)
        & (candidates["contract_date"] >= earliest_contract_date)
        & candidates["exclusive_area_m2"].between(minimum_area, maximum_area)
        & ((candidates["build_year"] - build_year).abs() <= build_year_tolerance)
        & (~candidates["is_cancelled"])
    )

    comparables = candidates.loc[mask].copy()
    comparables["price_per_m2"] = comparables["price_krw"] / comparables["exclusive_area_m2"]
    return comparables.sort_values(["distance_m", "contract_date"]).reset_index(drop=True)

