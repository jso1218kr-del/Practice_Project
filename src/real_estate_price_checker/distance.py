"""위도·경도로 두 지점 사이의 거리를 계산한다."""

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_000


def haversine_distance_m(
    latitude1: float,
    longitude1: float,
    latitude2: float,
    longitude2: float,
) -> float:
    """두 좌표 사이의 대원 거리를 미터 단위로 반환한다."""
    latitude1_rad = radians(latitude1)
    latitude2_rad = radians(latitude2)
    latitude_difference = radians(latitude2 - latitude1)
    longitude_difference = radians(longitude2 - longitude1)

    haversine_value = (
        sin(latitude_difference / 2) ** 2
        + cos(latitude1_rad) * cos(latitude2_rad) * sin(longitude_difference / 2) ** 2
    )
    central_angle = 2 * asin(sqrt(haversine_value))
    return EARTH_RADIUS_M * central_angle

