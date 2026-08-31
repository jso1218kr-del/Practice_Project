from pathlib import Path

import pandas as pd
import pytest

from real_estate_price_checker.data_loader import AddressNotFoundError, load_transactions
from real_estate_price_checker.evaluator import evaluate_property

SAMPLE_DATA_PATH = Path(__file__).parents[1] / "data" / "sample" / "transactions.csv"
TARGET_ADDRESS = "서울시 학습구 평가로 1"


def make_evaluation_transactions(count: int = 3) -> pd.DataFrame:
    """㎡당 가격이 500만·600만·700만원인 비교 거래를 순서대로 만든다."""
    prices = [500_000_000, 600_000_000, 700_000_000]
    rows = []
    for index, price in enumerate(prices[:count], start=1):
        rows.append(
            {
                "transaction_id": f"evaluation-{index}",
                "address": TARGET_ADDRESS if index == 1 else f"서울시 학습구 평가로 {index}",
                "latitude": 37.5665 + index * 0.001,
                "longitude": 126.9780,
                "contract_date": pd.Timestamp(f"2025-0{index + 2}-01"),
                "price_krw": price,
                "exclusive_area_m2": 100.0,
                "floor": 10,
                "build_year": 2015,
                "property_type": "아파트",
                "transaction_type": "매매",
                "is_cancelled": False,
            }
        )
    return pd.DataFrame(rows)


def evaluate(expected_price_krw: int, *, count: int = 3) -> dict[str, object]:
    return evaluate_property(
        make_evaluation_transactions(count),
        address=TARGET_ADDRESS,
        expected_price_krw=expected_price_krw,
        exclusive_area_m2=100.0,
        floor=10,
        build_year=2015,
        valuation_date="2025-12-31",
    )


def test_expected_price_inside_quantile_range_is_fair() -> None:
    # 20·80분위수 사이의 가격이 적정으로 분류되는지 확인한다.
    result = evaluate(600_000_000)

    assert result["status"] == "FAIR"
    assert result["estimated_price_krw"] == 600_000_000
    assert result["lower_price_krw"] == 540_000_000
    assert result["upper_price_krw"] == 660_000_000


def test_expected_price_below_quantile_range_is_underpriced() -> None:
    # 하한보다 낮은 가격은 저평가로 구분되어야 한다.
    result = evaluate(500_000_000)

    assert result["status"] == "UNDERPRICED"


def test_expected_price_above_quantile_range_is_overpriced() -> None:
    # 상한보다 높은 가격은 고평가로 구분되어야 한다.
    result = evaluate(700_000_000)

    assert result["status"] == "OVERPRICED"


def test_fewer_than_three_comparables_is_insufficient_data() -> None:
    # 작은 표본으로 단정적인 가격 판정을 내리지 않게 막는다.
    result = evaluate(600_000_000, count=2)

    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["estimated_price_krw"] is None
    assert result["comparable_count"] == 2


def test_unknown_address_explains_current_learning_limit() -> None:
    # 주소 API가 없는 단계에서 지원하지 않는 주소를 조용히 잘못 처리하면 안 된다.
    with pytest.raises(AddressNotFoundError, match="샘플 데이터에 등록된 주소만"):
        evaluate_property(
            make_evaluation_transactions(),
            address="샘플에 없는 주소",
            expected_price_krw=600_000_000,
            exclusive_area_m2=100.0,
            floor=10,
            build_year=2015,
            valuation_date="2025-12-31",
        )


def test_sample_csv_is_read_with_dates_and_cancellation_flags() -> None:
    # 실제 실행 경로에서 CSV 타입 변환이 정상이어야 필터가 정확히 동작한다.
    transactions = load_transactions(SAMPLE_DATA_PATH)

    assert not transactions.empty
    assert pd.api.types.is_datetime64_any_dtype(transactions["contract_date"])
    assert transactions["is_cancelled"].dtype == bool

