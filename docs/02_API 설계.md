# API 설계

## 1. 설계 기준

API는 입력 API와 화면 조회 API를 분리했다.

- 입력 API는 seed 데이터 생성과 개발 중 수동 입력을 위해 사용한다.
- 화면 조회 API는 `index.html`에서 필요한 형태로 데이터를 가공해 반환한다.
- AI API는 견적 전환 확률 예측과 AI 배선 검사 mock을 담당한다.
- 개발용 reset API는 로컬 개발 환경에서만 seed 데이터를 다시 넣기 위해 사용한다.

공통 응답은 다음 형태를 기준으로 한다.

```json
{
  "code": "OK",
  "message": "처리 결과 메시지",
  "data": {}
}
```

입력 실패는 `INVALID_INPUT`, 모델 파일이 없을 때는 `MODEL_NOT_READY`처럼 식별 가능한 코드를 사용한다.

## 2. 기본 API

| Method | URL | 설명 |
| --- | --- | --- |
| GET | `/api/health` | 서버 상태 확인 |
| GET | `/api/health/db` | DB 연결 상태 확인 |

## 3. 입력 API

seed 스크립트와 개발 중 데이터 입력을 위한 API이다.  
각 API는 DB에 데이터를 저장하고 생성된 ID를 반환한다.

| Method | URL | 설명 |
| --- | --- | --- |
| POST | `/api/customers` | 고객 입력 |
| POST | `/api/quotes` | 견적 입력 및 AI 전환 확률 저장 |
| POST | `/api/orders` | 확정 수주 입력 |
| POST | `/api/units` | 호기 입력 |
| POST | `/api/process-masters` | 공정 마스터 입력 |
| POST | `/api/unit-processes` | 호기별 공정 상태 입력 |
| POST | `/api/materials` | 자재 마스터 입력 |
| POST | `/api/inventories` | LOT별 재고 입력 |
| POST | `/api/order-materials` | 확정 수주 필요 자재 입력 |
| POST | `/api/quote-materials` | 진행 견적 예상 자재 입력 |
| POST | `/api/ai-inspections` | AI 검사 결과 입력 |
| POST | `/api/tests` | 시험 성적 입력 |
| POST | `/api/events` | 이벤트 입력 |

`POST /api/quotes`는 단순 저장 API가 아니라, 견적 조건을 기반으로 AI 모델을 호출한 뒤 전환 확률을 함께 저장한다.

## 4. 통합 관제 API

| Method | URL | 설명 |
| --- | --- | --- |
| GET | `/api/dashboard/summary` | 금일 실적, 진행 호기, 납기 임박, 월간 납기 준수율, 재작업 요약 조회 |
| GET | `/api/dashboard/equipment-utilization` | 주요 설비 가동률 조회 |
| GET | `/api/dashboard/process-line` | 공정 라인별 완료, 진행, 경고 현황 조회 |
| GET | `/api/dashboard/weekly-output` | 월요일부터 일요일까지 주간 생산 실적 조회 |
| GET | `/api/events/recent` | 최근 이벤트 조회 |

주요 설비 가동률은 별도 설비 테이블을 두지 않고, 과제 화면의 기준에 맞춰 절곡기/CNC 설비와 연결되는 `판금 절곡` 공정 상태를 기준으로 계산한다.

## 5. 수주 공정 진척 API

| Method | URL | 설명 |
| --- | --- | --- |
| GET | `/api/progress/units` | 호기별 공정 진척, 현재 공정, 납기 위험 상태 조회 |
| GET | `/api/progress/due-risk/{unit_no}` | 특정 호기의 납기 위험 계산 결과 조회 |

납기 위험은 남은 공정의 표준 소요일과 납기까지 남은 기간을 비교해 계산한다.  
화면의 D-day 표시는 실제 납기까지 남은 날짜를 의미하고, 위험 판단은 내부 계산값을 사용한다.

## 6. 자재 및 재고 API

| Method | URL | 설명 |
| --- | --- | --- |
| GET | `/api/materials/requirements` | 주요 자재별 현재 재고, 2주 내 예상 소요량, 부족 수량, 발주 메시지 조회 |
| GET | `/api/materials/inventories` | LOT별 재고 목록 조회 |

2주 내 예상 소요량은 확정 수주 필요량과 진행 견적 예상 필요량을 함께 사용한다.  
진행 견적은 AI 전환 확률을 가중치로 반영한다.

## 7. 품질 및 이력 API

| Method | URL | 설명 |
| --- | --- | --- |
| GET | `/api/ai-inspections/summary` | 금일 AI 검사 건수, 검출 건수, 평균 신뢰도, 평균 판독 시간 조회 |
| POST | `/api/ai-inspections/mock` | AI 배선 검사 mock 실행 및 결과 저장 |
| GET | `/api/ai-inspections/units/{unit_no}` | 호기별 AI 검사 이력 조회 |
| GET | `/api/tests` | 시험 성적 목록 조회 |
| GET | `/api/tests/units/{unit_no}` | 호기별 시험 성적 조회 |
| GET | `/api/trace/{unit_no}` | 호기별 전체 이력 추적 조회 |
| GET | `/api/trace/orders/{order_id}` | 수주에 포함된 호기별 이력 조회 |

이력 추적은 별도 이벤트 테이블만 보는 방식이 아니라, 호기 기준으로 공정, 자재, AI 검사, 시험 성적, 이벤트를 모아 타임라인 형태로 반환한다.

## 8. AI API

| Method | URL | 설명 |
| --- | --- | --- |
| POST | `/api/ai/quote-probability` | 견적 조건 기반 전환 확률 예측 |

입력값:

| 필드 | 설명 |
| --- | --- |
| `customer_grade` | 고객 등급 |
| `quote_stage` | 견적 단계 |
| `quantity` | 견적 수량 |
| `estimated_amount` | 견적 금액 |
| `days_until_due` | 예상 납기까지 남은 일수 |

응답값:

| 필드 | 설명 |
| --- | --- |
| `model_probability` | 모델이 예측한 전환 확률 |
| `planning_probability` | 자재 계획에 사용할 보수 계산 확률 |

자재 계획은 결품을 피하는 것이 중요하므로 모델 확률을 그대로 쓰지 않고, 최소값과 보수 계수를 적용한 `planning_probability`를 사용한다.

## 9. 개발용 API

| Method | URL | 설명 |
| --- | --- | --- |
| POST | `/api/dev/reset` | 개발 DB 데이터 초기화 |

이 API는 seed 데이터를 반복 입력하기 위한 개발용 기능이다.  
운영 환경에서는 인증과 접근 제한이 필요하다.

## 10. OpenAPI

FastAPI는 API 구조를 자동으로 문서화한다.

- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`

프론트엔드 연결이나 보고서 작성 시 실제 API 목록과 응답 구조를 확인하는 기준으로 사용할 수 있다.
