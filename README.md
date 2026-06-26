# 비트코인 일일 온체인 분석 리포트

Claude Code 예약 루틴(클라우드에서 자동 실행되는 스케줄 에이전트)을 통해 매일 비트코인 시황과 온체인 데이터를 수집·분석하고, 투자 적절성에 대한 휴리스틱 신호를 생성해 텔레그램으로 전송하는 시스템입니다.

## 동작 방식
1. 매일 정오(12:00 KST)에 Claude Code 예약 루틴이 자동 실행됩니다. PC가 꺼져 있어도 클라우드에서 동작합니다.
2. [ANALYSIS_PROMPT.md](ANALYSIS_PROMPT.md)에 정의된 절차에 따라 무료 공개 API(CoinGecko, blockchain.com, mempool.space, alternative.me, CoinMetrics Community)에서 가격·온체인·심리 데이터를 수집합니다.
3. 투명한 룰 기반 점수표로 매수/중립/매도(차익실현) 신호를 산출합니다 (점수표는 ANALYSIS_PROMPT.md 2절 참고).
4. 결과를 [reports/](reports/)에 날짜별 상세 리포트(`YYYY-MM-DD.md`)로 저장하고, [reports/SUMMARY.md](reports/SUMMARY.md)에 한 줄 요약을 누적합니다.
5. 요약 메시지와 전체 리포트 파일을 텔레그램으로 전송합니다.

## 파일 구조
- `ANALYSIS_PROMPT.md` — 매일 실행되는 분석 절차 전체 (데이터 소스 URL, 추출 필드, 스코어링 규칙, 리포트 템플릿, 텔레그램 전송 방법)
- `reports/YYYY-MM-DD.md` — 날짜별 상세 리포트
- `reports/SUMMARY.md` — 날짜·가격·신호 누적 요약 테이블
- `.env` — 텔레그램 봇 토큰/chat_id (git에 커밋되지 않음, `.gitignore`에 등록됨)

## 일정 변경 / 즉시 실행
- 실행 시각을 바꾸려면: "비트코인 리포트 스케줄을 OO시로 바꿔줘"
- 지금 바로 리포트가 필요하면: "오늘 비트코인 리포트 지금 만들어줘"
- 둘 다 Claude Code 대화에서 요청하면 됩니다.

## 데이터 소스 (전부 무료, API 키 불필요)
- CoinGecko — 가격, 시가총액, 거래량
- blockchain.com Charts API — 해시레이트, 난이도, 활성주소, 트랜잭션수, 멤풀, 채굴자수익
- mempool.space — 수수료, 난이도 조정 예상
- alternative.me — Fear & Greed Index
- CoinMetrics Community API — MVRV (best-effort, 무료 한도로 인해 일부 날짜는 미수집될 수 있음)

## ⚠️ 안내
이 시스템이 생성하는 모든 리포트와 신호는 공개 데이터를 활용한 규칙 기반 정보 제공용 콘텐츠이며, **투자 자문이 아닙니다**. 투자 판단과 그 결과에 대한 책임은 전적으로 투자자 본인에게 있습니다.
