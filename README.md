# DN전기 SMART OPS

배전반 스마트공장 통합 관제 시스템 과제 구현입니다.  
정적 HTML 시안을 PostgreSQL, FastAPI, JavaScript 기반의 로컬 동작 시스템으로 연결했습니다.

## 구현 범위

- 통합 관제 KPI, 공정 라인 현황, 주간 생산 실적 조회
- 호기별 수주·공정 진척 조회와 납기 위험 계산
- 자재 재고와 2주 내 예상 소요량 비교
- 견적 전환 확률 예측 모델 연동
- AI 배선 검사 mock 실행 및 검사 결과 저장
- 시험 성적 조회와 호기별 이력 추적
- 재현 가능한 가상 데이터 생성

## 기술 스택

- FastAPI
- PostgreSQL 17
- SQLAlchemy
- scikit-learn
- Docker Compose
- HTML, CSS, JavaScript

## 실행 방법

Docker Compose로 PostgreSQL을 실행하고, FastAPI 서버를 로컬에서 실행합니다.

가상환경 생성 및 패키지 설치:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

환경 파일 생성:

```powershell
copy .env.example .env
```

복사 후 `.env`에서 `POSTGRES_PASSWORD`와 `DATABASE_URL`의 비밀번호 부분을 같은 값으로 수정합니다.  
기본 호스트 포트는 `.env.example` 기준 `5432`입니다.

개발/데모용 설정:

```env
APP_ENV=development
BASE_DATE=2026-08-05
```

`APP_ENV=development`에서는 `BASE_DATE`가 화면과 API의 기본 기준일로 사용됩니다.  
`seed_data.py`는 서버가 development 환경이 아니면 실행을 중단합니다.

PostgreSQL 실행:

```powershell
docker compose up -d
```

API 서버 실행:

```powershell
uvicorn app.main:app --reload
```

화면 접속:

```text
http://127.0.0.1:8000/
```

API 문서:

```text
http://127.0.0.1:8000/docs
```

개발/데모 데이터 입력:

```powershell
python scripts\seed_data.py
```

## 설계 결정 요약

### DBMS

PostgreSQL을 사용했습니다. 수주, 호기, 공정, 자재, 재고, 검사, 시험처럼 관계가 명확한 데이터를 다루기 적합하고, 날짜 계산과 집계 쿼리를 안정적으로 처리할 수 있기 때문입니다. Docker Compose로 로컬 실행 환경을 고정하기 쉬운 점도 고려했습니다.

### 수주와 호기 분리

DN 번호는 수주 번호가 아니라 실제 제작 단위인 호기 번호로 해석했습니다. 하나의 수주에서 여러 호기가 생성될 수 있으므로 `orders`와 `units`를 분리했습니다.

### 공정 구조

공정명과 순서는 `process_masters`에서 관리하고, 실제 호기별 진행 상태는 `unit_processes`에서 관리했습니다. 이를 통해 표준 공정과 개별 진행 이력을 분리했습니다.

### 자재 소요 계산

확정 수주의 BOM은 그대로 반영하고, 진행 견적은 AI 전환 확률을 가중치로 반영했습니다. 자재 계획은 부족을 늦게 발견하는 것보다 보수적으로 계산하는 것이 낫다고 판단했습니다.

### AI 배선 검사

과제에서 실제 비전 모델은 요구하지 않았으므로 mock으로 구현했습니다. 다만 검사 결과, 신뢰도, 판독 시간, 검출 내용을 DB에 저장해 대시보드와 호기별 이력에 반영했습니다.

## AI 모델 학습

학습 데이터 생성:

```powershell
python scripts\generate_quote_training_data.py
```

모델 학습:

```powershell
python ai\training\train_quote_probability.py
```

모델은 견적 전환 확률을 예측하고, 진행 견적의 예상 자재 소요량을 계산할 때 가중치로 사용합니다.  
AI 배선 검사는 과제 범위에 맞춰 실제 비전 모델이 아닌 mock 판정으로 구현했습니다.

## AI 도구 활용

Codex는 설계 검토, 코드 작성 도움, 오류 원인 분석, 화면 연결, 문서 초안 작성에 활용했습니다. 다만 수주와 호기 분리, AI 기능 범위, 주요 설비 가동률 해석처럼 과제 범위와 직접 연결되는 판단은 과제 문서와 HTML 시안을 기준으로 다시 검토하며 결정했습니다.
