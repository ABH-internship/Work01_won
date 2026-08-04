#### API 설계

**수주 - 호기 - 공정 - 실적 조회,**

**자재 - BOM - 재고 계산,**

**검사 - 시험 - 이력 저장 및 조회**

**각 기능을 화면과 시드 스크립트에서 사용할 수 있는 API 설계.**



**# 필요 API**

1. 가상 데이터 입력용 API
* 수요처 입력
* 견적 입력
* 수주 입력
* 호기 입력
* 공정마스터 입력
* 호기공정 입력
* 자재 입력
* 재고 입력
* 수주자재 입력
* 견적자재 입력
* AI검사 입력
* 시험 입력
* 이벤트 입력



2. 화면 조회용 API

* 통합 관제 KPI 조회
* 공정 라인 현황 조회
* 주간 생산실적 조회
* 최근 이벤트 조회
* 호기별 진척 조회
* 납기 역산 경보 조회
* AI검사 결과 조회
* 자재 부족/충분 판정 조회
* 시험성적 조회
* 호기 이력 추적 조회



3. 개발용 API

* 가상 데이터 재생성을 위한 초기화



**# API 목록**

1. 기준/입력 API: 가상 데이터 입력 스크립트에서 사용
2. 통합 관제 API: KPI, 라인 현황, 주간 실적, 이벤트 조회
3. 수주·공정 API: 호기별 진척과 납기 역산 경보 조회
4. AI검사 API: Mock AI 검사 실행 및 결과 조회
5. 자재·재고 API: 수주 BOM 기준 자재 소요와 재고 판정 조회
6. 시험·이력 API: 시험성적과 호기 기준 전체 이력 조회
7. 개발용 API: 로컬 개발 데이터 초기화



**# 명세**

1. 기준/입력 API

   1. POST /api/customers
   2. POST /api/quotes
   3. POST /api/orders
   4. POST /api/units
   5. POST /api/process-masters
   6. POST /api/unit-processes
   7. POST /api/materials
   8. POST /api/inventories
   9. POST /api/order-materials
   10. POST /api/quote-materials
   11. POST /api/ai-inspections
   12. POST /api/tests
   13. POST /api/events
2. 통합 관제 API

   1. GET /api/dashboard/summary
   2. GET /api/dashboard/process-line
   3. GET /api/dashboard/weekly-output
   4. GET /api/events/recent
3. 수주·공정 API

   1. GET /api/progress/units
   2. GET /api/progress/due-risk/{unit_no}
4. AI검사 API

   1. POST /api/ai-inspections/mock
   2. GET /api/ai-inspections/summary
   3. GET /api/ai-inspections/units/{unit_no}
5. 자재·재고 API

   1. GET /api/materials/requirements
   2. GET /api/materials/inventories
6. 시험·이력 API

   1. GET /api/tests
   2. GET /api/tests/units/{unit_no}
   3. GET /api/trace/{unit_no}
7. 개발용 API

   1. POST /api/dev/reset
