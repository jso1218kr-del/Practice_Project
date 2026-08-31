import pandas as pd

from real_estate_price_checker.comparable_search import find_comparables


def make_transaction(transaction_id: str, **changes: object) -> dict[str, object]:
    """각 테스트가 확인할 조건만 눈에 띄게 바꿀 수 있게 기본 거래를 만든다."""
    transaction: dict[str, object] = {
        "transaction_id": transaction_id,
        "address": "서울시 학습구 테스트로 1",
        "latitude": 37.5665,
        "longitude": 126.9780,
        "contract_date": pd.Timestamp("2025-06-01"),
        "price_krw": 500_000_000,
        "exclusive_area_m2": 84.0,
        "floor": 10,
        "build_year": 2015,
        "property_type": "아파트",
        "transaction_type": "매매",
        "is_cancelled": False,
    }
    transaction.update(changes)
    return transaction


def search(*transactions: dict[str, object]) -> pd.DataFrame:
    """모든 검색 테스트가 동일한 평가 조건을 사용하게 한다."""
    return find_comparables(
        pd.DataFrame(transactions),
        target_latitude=37.5665,
        target_longitude=126.9780,
        exclusive_area_m2=84.0,
        build_year=2015,
        valuation_date="2025-12-31",
        property_type="아파트",
        transaction_type="매매",
    )


def test_transaction_inside_one_kilometer_is_selected() -> None:
    # 정상 비교 거래가 검색 결과에 실제로 들어오는지 확인한다.
    result = search(make_transaction("inside", latitude=37.5710))

    assert result["transaction_id"].tolist() == ["inside"]


def test_transaction_outside_one_kilometer_is_excluded() -> None:
    # 너무 먼 거래가 지역 시세를 왜곡하지 않아야 한다.
    result = search(
        make_transaction("inside"),
        make_transaction("outside", latitude=37.5865),
    )

    assert result["transaction_id"].tolist() == ["inside"]


def test_future_transaction_is_excluded() -> None:
    # 평가 시점에 알 수 없던 미래 거래를 사용하면 데이터 누수가 생긴다.
    result = search(
        make_transaction("past"),
        make_transaction("future", contract_date=pd.Timestamp("2026-01-01")),
    )

    assert result["transaction_id"].tolist() == ["past"]


def test_cancelled_transaction_is_excluded() -> None:
    # 실제로 성립하지 않은 취소 가격은 시세 근거가 될 수 없다.
    result = search(
        make_transaction("valid"),
        make_transaction("cancelled", is_cancelled=True),
    )

    assert result["transaction_id"].tolist() == ["valid"]


def test_transaction_with_large_area_difference_is_excluded() -> None:
    # 면적이 크게 다른 주택은 총가격을 직접 비교하기 어렵다.
    result = search(
        make_transaction("similar-area"),
        make_transaction("different-area", exclusive_area_m2=100.0),
    )

    assert result["transaction_id"].tolist() == ["similar-area"]


def test_transaction_with_large_build_year_difference_is_excluded() -> None:
    # 연식 차이가 큰 주택은 상태와 상품성이 달라질 가능성이 높다.
    result = search(
        make_transaction("similar-age"),
        make_transaction("different-age", build_year=2000),
    )

    assert result["transaction_id"].tolist() == ["similar-age"]

