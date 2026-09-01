"""2단계: 국토교통부 실거래가 CSV의 품질을 확인하고 정제한다."""

from __future__ import annotations

import argparse
from pathlib import Path

from real_estate_price_checker.data_quality import load_and_clean_molit_csv


def _print_report(report: dict[str, object]) -> None:
    print("\n=== 2단계 데이터 품질 보고서 ===")
    print(f"읽은 인코딩: {report['encoding']}")
    print(f"원본 크기: {report['raw_row_count']}행 x {report['raw_column_count']}열")
    print(f"중복 제외: {report['duplicate_count']}건")
    print(f"필수값/타입 오류 제외: {report['invalid_count']}건")
    print(f"취소 거래 제외: {report['cancelled_count']}건")
    print(f"정제 후 거래: {report['cleaned_row_count']}건")
    print(f"가격 이상치 검토 대상(IQR): {report['price_outlier_count']}건")

    print("\n정제 후 컬럼 타입:")
    for column, dtype in report["cleaned_dtypes"].items():
        print(f"- {column}: {dtype}")

    print("\n필수 컬럼별 결측값:")
    for column, count in report["missing_by_required_column"].items():
        print(f"- {column}: {count}건")

    print("\n원본 컬럼 탐색:")
    for profile in report["column_profiles"]:
        samples = ", ".join(profile["sample_values"]) or "(값 없음)"
        print(
            f"- {profile['column']} | dtype={profile['dtype']} | "
            f"결측={profile['missing_count']} | 고유값={profile['unique_count']} | "
            f"예시={samples}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="국토교통부 아파트 매매 CSV 품질 점검")
    parser.add_argument("csv_path", type=Path, help="국토교통부에서 내려받은 CSV 경로")
    parser.add_argument("--output", type=Path, help="정제 결과를 저장할 CSV 경로")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = load_and_clean_molit_csv(args.csv_path)
    except (FileNotFoundError, ValueError) as error:
        print(f"데이터 오류: {error}")
        return 1

    _print_report(result.report)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        result.cleaned.to_csv(args.output, index=False, encoding="utf-8-sig")
        print(f"\n정제 CSV 저장: {args.output}")
    else:
        print("\n정제 결과는 저장하지 않았습니다. 저장하려면 --output 경로를 지정하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
