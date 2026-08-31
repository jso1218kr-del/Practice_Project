"""학습용 비교 거래 기준선을 터미널에서 실행한다."""

from pathlib import Path

from real_estate_price_checker.data_loader import AddressNotFoundError, load_transactions
from real_estate_price_checker.evaluator import evaluate_property

SAMPLE_DATA_PATH = Path(__file__).parent / "data" / "sample" / "transactions.csv"

STATUS_LABELS = {
    "FAIR": "적정",
    "UNDERPRICED": "저평가",
    "OVERPRICED": "고평가",
    "INSUFFICIENT_DATA": "데이터 부족",
}


def format_krw(amount: int | None) -> str:
    """원 단위 정수를 억·만원 중심의 읽기 쉬운 문자열로 바꾼다."""
    if amount is None:
        return "계산하지 않음"

    sign = "-" if amount < 0 else ""
    absolute_amount = abs(amount)
    eok, remainder = divmod(absolute_amount, 100_000_000)
    man = remainder // 10_000

    parts: list[str] = []
    if eok:
        parts.append(f"{eok:,}억")
    if man:
        parts.append(f"{man:,}만")
    if not parts:
        parts.append(f"{absolute_amount:,}")
    return f"{sign}{' '.join(parts)} 원"


def print_result(expected_price_krw: int, result: dict[str, object]) -> None:
    """평가 결과와 그 근거를 사람이 읽을 수 있게 출력한다."""
    print("\n=== 비교 거래 가격 평가 결과 ===")
    print(f"판정: {STATUS_LABELS[str(result['status'])]}")
    print(f"예상 거래가격: {format_krw(expected_price_krw)}")
    print(f"추정 중앙가격: {format_krw(result['estimated_price_krw'])}")
    print(
        "적정가격 범위: "
        f"{format_krw(result['lower_price_krw'])} ~ {format_krw(result['upper_price_krw'])}"
    )
    print(f"중앙가격과의 차이: {format_krw(result['difference_amount_krw'])}")
    if result["difference_percent"] is not None:
        print(f"중앙가격 대비 차이율: {result['difference_percent']:+.2f}%")
    print(f"사용한 유사 거래: {result['comparable_count']}건")
    print(f"방법: {result['methodology']}")
    for warning in result["warnings"]:
        print(f"주의: {warning}")

    if result["comparables"]:
        print("\n판정에 사용한 유사 거래:")
        for comparable in result["comparables"]:
            print(
                f"- {comparable['transaction_id']} | {comparable['contract_date']} | "
                f"{format_krw(comparable['price_krw'])} | "
                f"{comparable['exclusive_area_m2']:.1f}㎡ | {comparable['distance_m']:.1f}m"
            )


def main() -> None:
    """입력을 받아 아파트 매매 기준으로 1단계 평가를 실행한다."""
    print("학습용 가상 데이터로 아파트 매매가격을 평가합니다.")
    address = input("주소: ").strip()

    try:
        expected_price_krw = int(input("예상 매매가격(원): ").replace(",", "").strip())
        exclusive_area_m2 = float(input("전용면적(㎡): ").strip())
        floor = int(input("층: ").strip())
        build_year = int(input("건축년도: ").strip())
        valuation_date = input("평가 기준일(YYYY-MM-DD): ").strip()

        transactions = load_transactions(SAMPLE_DATA_PATH)
        result = evaluate_property(
            transactions,
            address=address,
            expected_price_krw=expected_price_krw,
            exclusive_area_m2=exclusive_area_m2,
            floor=floor,
            build_year=build_year,
            valuation_date=valuation_date,
        )
    except AddressNotFoundError as error:
        print(f"\n주소 오류: {error}")
        return
    except (ValueError, TypeError) as error:
        print(f"\n입력 오류: 입력 형식과 값을 확인해 주세요. ({error})")
        return

    print_result(expected_price_krw, result)


if __name__ == "__main__":
    main()

