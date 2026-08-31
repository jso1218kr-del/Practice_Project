import pytest

from real_estate_price_checker.distance import haversine_distance_m


def test_same_coordinates_have_almost_zero_distance() -> None:
    # 같은 지점이 0m가 아니면 모든 반경 검색 결과가 왜곡된다.
    distance = haversine_distance_m(37.5665, 126.9780, 37.5665, 126.9780)

    assert distance == pytest.approx(0.0, abs=0.001)


def test_known_seoul_coordinates_have_reasonable_distance() -> None:
    # 서울시청과 서울역의 대략적인 거리를 이용해 미터 단위 변환까지 확인한다.
    distance = haversine_distance_m(37.5665, 126.9780, 37.5547, 126.9707)

    assert 1_300 < distance < 1_600

