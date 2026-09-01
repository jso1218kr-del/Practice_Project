# 부동산 예상 거래가격 점검기

국토교통부 실거래가 데이터를 활용하는 과정을 단계적으로 배우기 위한 Python 프로젝트입니다.
빠른 완성보다 데이터가 어떻게 정리·선택되고 가격 근거가 어떻게 계산되는지 이해하는 것이
목적입니다.

> `data/sample/`의 주소와 거래는 모두 학습을 위해 만든 가상 데이터입니다.
> 실제 부동산 거래나 투자 판단에 사용하면 안 됩니다.

## 최종 목표

사용자가 입력한 부동산의 예상 거래가격을 반경 내 유사 실거래 통계 및 CatBoost 모델과
비교하여 `적정`, `고평가`, `저평가`, `데이터 부족` 중 하나로 판정하고 근거 거래를 보여줍니다.

## 현재 구현 범위

### 1단계: 최소 비교 거래 기준선

- 샘플 CSV 읽기 및 입력 주소의 샘플 좌표 찾기
- Haversine 공식으로 거래 거리를 미터 단위로 계산
- 반경 1km, 최근 24개월, 면적 ±10%, 건축년도 ±10년 조건 검색
- 같은 주택 유형·거래 유형만 선택하고 미래·취소 거래 제외
- 유사 거래 ㎡당 가격의 중앙값과 20·80분위수 계산
- 적정·저평가·고평가·데이터 부족 판정
- Python `input()` 기반 한국어 CLI와 pytest 테스트

현재 1단계 CLI는 **아파트 매매**를 대상으로 합니다. 입력한 층은 결과에 표시되지만
검색이나 가격 계산에는 아직 반영하지 않습니다.

### 2단계: 실거래가 CSV 품질 점검과 정제

- UTF-8(BOM 포함)과 CP949 CSV 읽기
- 국토교통부 CSV의 한글 헤더와 일부 컬럼명 변형을 내부 표준 이름으로 변환
- 원본 컬럼별 타입, 결측 수, 고유값 수, 대표 값 탐색
- 거래금액(만원), 전용면적, 층, 건축년도와 계약일을 계산 가능한 타입으로 변환
- 완전히 같은 중복 행, 필수값·타입 오류 행, 취소 거래 제외 및 사유별 건수 보고
- ㎡당 가격의 IQR 기준 이상치를 삭제하지 않고 검토 대상으로 표시
- 후속 분석에 쓸 표준 컬럼과 재현 가능한 거래 ID 생성

2단계 정제 결과에는 아직 위도·경도가 없습니다. 실제 주소 좌표 변환을 배우기 전까지는
1단계 반경 검색에 바로 연결하지 않습니다.

## 사용 기술

- Python 3.12: 프로그램과 계산 로직
- pandas: CSV 로딩, 타입 변환, 필터링, 요약 통계
- CSV: 작고 직접 열어볼 수 있는 학습 데이터
- pytest: 조건별 자동 테스트
- Ruff: 코드 오류와 일관성 검사

아직 Jupyter Notebook, NumPy, 시각화, Parquet, FastAPI, Streamlit, CatBoost,
scikit-learn, 데이터베이스, Docker, 실제 주소 API는 사용하지 않습니다. 필요성이 생기는
후속 단계에서 하나씩 도입합니다.

## 설치 방법(Windows PowerShell)

먼저 Python 3.12를 설치하고 새 PowerShell에서 버전을 확인합니다.

```powershell
python --version
```

출력이 `Python 3.12.x`인지 확인한 뒤 저장소 루트에서 가상환경을 만들고 활성화합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

PowerShell 실행 정책 때문에 활성화가 막히면 현재 창에서만 다음 명령을 먼저 실행합니다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 실행 방법

### 1단계 가격 평가

```powershell
python main.py
```

샘플 입력값:

```text
주소: 서울시 학습구 기준로 1
예상 매매가격(원): 500000000
전용면적(㎡): 84
층: 10
건축년도: 2015
평가 기준일(YYYY-MM-DD): 2025-12-31
```

샘플에 없는 주소는 아직 좌표로 변환할 수 없으므로 지원 범위를 설명하는 오류가 나옵니다.

### 2단계 데이터 품질 점검

먼저 학습용 원본 CSV로 보고서를 확인합니다.

```powershell
python phase2.py data/sample/molit_transactions.csv
```

정제된 CSV도 저장하려면 출력 경로를 지정합니다.

```powershell
python phase2.py data/sample/molit_transactions.csv --output data/processed/transactions.csv
```

실제 국토교통부 CSV를 내려받았다면 Git에 포함되지 않는 `data/raw/`에 두고 같은 명령의
입력 경로만 바꿉니다. 원본 파일의 필수 컬럼을 찾지 못하면 누락된 내부 표준 컬럼명이
오류에 표시됩니다. 정제 결과는 UTF-8 BOM 형식으로 저장하므로 Excel에서도 한글을
확인할 수 있습니다.

## 테스트와 코드 검사

```powershell
python -m pytest
python -m ruff check .
```

## 코드 읽는 순서

1단계:

1. `main.py`에서 사용자 입력을 받습니다.
2. `data_loader.py`가 CSV를 읽고 주소의 좌표를 찾습니다.
3. `comparable_search.py`가 `distance.py`를 사용해 유사 거래를 필터링합니다.
4. `evaluator.py`가 중앙값·분위수를 계산하고 가격 상태를 판정합니다.
5. `main.py`가 가격과 근거 거래를 한국어로 출력합니다.

2단계:

1. `phase2.py`가 입력·출력 CSV 경로를 받습니다.
2. `data_quality.py`의 `read_molit_csv()`가 인코딩을 선택합니다.
3. `inspect_columns()`가 원본을 바꾸기 전에 컬럼 품질을 탐색합니다.
4. `standardize_molit_columns()`가 한글 헤더를 내부 표준 이름으로 바꿉니다.
5. `clean_molit_transactions()`가 타입 변환과 제외 조건을 적용하고 보고서를 만듭니다.

## 현재 한계

- 실제 주소를 좌표로 변환하지 않고 샘플에 등록된 주소만 사용합니다.
- 저장소에는 실제 국토교통부 데이터가 아닌 작은 가상 CSV만 있습니다.
- 내려받기 시점에 추가되는 새로운 컬럼명 변형은 별칭 목록에 보완해야 할 수 있습니다.
- IQR 이상치 표시는 전체 데이터 단가 분포를 사용한 첫 검토 기준이며 오류 확정이 아닙니다.
- 층, 거리, 거래시점, 면적, 연식에 가중치를 주지 않습니다.
- 유사 거래가 3건이면 계산하므로 실제 판단에 필요한 표본보다 적습니다.
- 단순 분위수 범위는 통계적 예측구간이나 투자 조언이 아닙니다.

## 2단계에서 이어서 할 일

실제 내려받은 CSV로 품질 보고서를 실행해 컬럼 차이를 확인한 뒤 별칭과 검증 규칙을
보완합니다. 그다음 지역·단지별로 이상치 기준을 세분화하고, 정제 데이터의 분석 규모가
커질 때 CSV와 Parquet의 차이를 학습합니다. Jupyter Notebook, NumPy와 시각화는 실제
탐색 질문이 생긴 뒤 추가합니다.
