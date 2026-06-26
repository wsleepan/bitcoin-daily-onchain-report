# 비트코인 일일 온체인 분석 — 실행 절차

이 문서는 매일 예약 루틴으로 실행되는 작업의 전체 절차입니다. 아래 단계를 순서대로, 빠짐없이 수행하세요. 이 작업은 무인으로 실행되므로 추측이나 생략 없이 명시된 규칙만 따르세요.

작업 디렉토리: 이 파일이 있는 프로젝트 루트 (`reports/` 폴더가 같은 위치에 있어야 함)

## 0. 사전 준비
- 이 디렉토리가 git 저장소라면 먼저 `git pull`로 origin의 최신 상태(과거 리포트 누적분 포함)를 받아오세요.
- 오늘 날짜를 KST(한국 표준시) 기준 `YYYY-MM-DD` 형식으로 확정합니다. (시스템 컨텍스트의 현재 날짜 사용)
- `reports/` 폴더가 없으면 생성합니다.
- 오늘 날짜의 리포트가 이미 `reports/YYYY-MM-DD.md`로 존재하면, 새로 덮어쓰기 전에 기존 파일 내용을 참고하지 말고 그냥 새로 생성합니다(매일 독립적으로 분석).

## 1. 데이터 수집

아래 각 URL을 WebFetch로 호출하세요. JSON API이므로 WebFetch 프롬프트에 "Return the raw JSON response verbatim, do not summarize or omit fields"와 같이 명시해서 가공 없이 원본 수치를 받아오세요.

**중요**: 특정 소스가 실패(네트워크 오류, 429, 403 등)하면 해당 항목만 "데이터 수집 실패"로 표기하고 나머지는 정상 진행하세요. 절대 숫자를 추측해서 채우지 마세요.

### 1-A. 가격/시장 데이터 — CoinGecko
```
https://api.coingecko.com/api/v3/coins/bitcoin?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false
```
추출할 필드 (`market_data` 하위):
- `current_price.usd`, `current_price.krw`
- `market_cap.usd`
- `total_volume.usd`
- `price_change_percentage_24h`
- `price_change_percentage_7d`
- `price_change_percentage_30d`
- `ath.usd`, `ath_change_percentage.usd`
- `circulating_supply`
- 최상위 `market_cap_rank`

### 1-B. 온체인 네트워크 데이터 — blockchain.com Charts API
각 차트는 `{"values":[{"x":unix_ts,"y":value}, ...]}` 형태입니다. **최신값(배열 마지막 원소)**과 **약 30일 전 값**을 비교해 추세(상승/하락/보합)를 판단하세요.

- 해시레이트: `https://api.blockchain.info/charts/hash-rate?timespan=40days&format=json`
- 난이도: `https://api.blockchain.info/charts/difficulty?timespan=70days&format=json`
- 활성 주소수: `https://api.blockchain.info/charts/n-unique-addresses?timespan=40days&format=json`
- 트랜잭션 수: `https://api.blockchain.info/charts/n-transactions?timespan=40days&format=json`
- 멤풀 크기(미확인 거래 적체): `https://api.blockchain.info/charts/mempool-size?timespan=14days&format=json`
- 채굴자 수익: `https://api.blockchain.info/charts/miners-revenue?timespan=40days&format=json`
- 추정 거래소 거래량: `https://api.blockchain.info/charts/trade-volume?timespan=40days&format=json`

### 1-C. 네트워크 혼잡도 — mempool.space
```
https://mempool.space/api/v1/fees/recommended
https://mempool.space/api/v1/difficulty-adjustment
```

### 1-D. 시장 심리 — Fear & Greed Index
```
https://api.alternative.me/fng/?limit=30&format=json
```
`data[0]`이 오늘 값입니다 (`value`, `value_classification`). 최근 30일 평균도 참고용으로 계산하세요.

### 1-E. 밸류에이션 지표 — CoinMetrics Community API (best-effort, 실패 가능성 있음)
```
https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=CapMVRVCur,AdrActCnt,SplyCur&frequency=1d&page_size=5
```
`CapMVRVCur`(MVRV 비율)를 추출하세요. 무료 API라 접근이 막히거나 값이 없을 수 있습니다 — 이 경우 리포트에 "MVRV: 데이터 소스 제한으로 미수집"이라 명시하고, 아래 스코어링 B 항목은 제외(가중치 0)하고 진행하세요.

## 2. 스코어링 — 투자 적절성 신호 산출

아래 규칙 기반 점수표를 **그대로** 적용하세요. 자의적 해석을 추가하지 말고, 해당 구간에 맞는 점수를 부여하세요. 데이터가 없는 항목은 점수 0으로 처리하고 "제외"로 표시합니다.

| 항목 | 기준 | 점수 |
|---|---|---|
| A. 시장심리 (Fear&Greed, 역발상) | 0–24 극단적 공포 | **+2** |
| | 25–44 공포 | **+1** |
| | 45–55 중립 | 0 |
| | 56–75 탐욕 | **-1** |
| | 76–100 극단적 탐욕 | **-2** |
| B. 밸류에이션 (MVRV) | <1.0 저평가 | **+2** |
| | 1.0–2.0 저평가~정상 | **+1** |
| | 2.0–3.5 정상~다소 과열 | 0 |
| | 3.5–5.0 과열 | **-1** |
| | ≥5.0 극단적 과열 | **-2** |
| C. 네트워크 펀더멘털 (해시레이트 30일 추세) | +2% 초과 상승 | **+1** |
| | ±2% 이내 | 0 |
| | 2% 초과 하락 | **-1** |
| D. 사용자 활동 (활성주소 30일 추세) | 상승 | **+1** |
| | 보합 | 0 |
| | 하락 | **-1** |
| E. 가격 모멘텀 (30일, 약한 역발상) | -15% 이하 (급락) | **+1** |
| | -15%~+15% | 0 |
| | +15% 이상 (급등) | **-1** |

**총점 계산**: 사용 가능한 항목들의 점수를 단순 합산 (이론적 범위 약 -7 ~ +7).

**신호 판정**:
- 총점 ≥ +3 → **매수 우위**
- -2 ~ +2 → **중립/관망**
- 총점 ≤ -3 → **매도(차익실현)/관망 우위**

채굴자 수익(miners-revenue), 멤풀 혼잡도, 수수료는 점수에 반영하지 않고 해설용 참고 지표로만 리포트에 서술하세요.

## 3. 리포트 작성

`reports/YYYY-MM-DD.md` 파일을 아래 템플릿에 맞춰 작성하세요 (숫자는 실제 수집값으로 채우고, 추세는 ▲/▼/▬로 표시).

```markdown
# 비트코인 일일 시황 리포트 — {YYYY-MM-DD}

## 1. 가격 및 시장 개요
| 항목 | 값 |
|---|---|
| 현재가 (USD) | $... |
| 현재가 (KRW) | ₩... |
| 24h 변동 | ...% |
| 7d 변동 | ...% |
| 30d 변동 | ...% |
| 시가총액 | $... (랭크 #...) |
| 24h 거래량 | $... |
| ATH 대비 | ...% (ATH $...) |

## 2. 온체인 지표
- 해시레이트: ... (30일 추세: ▲/▼/▬ ...%) — [한 줄 해설]
- 난이도: ... (다음 조정 예상: ...)
- 활성 주소수: ... (30일 추세: ...) — [한 줄 해설]
- 트랜잭션 수: ...
- 멤풀 적체: ... — 수수료(사토시/vB): 보통 ... / 빠름 ...
- 채굴자 수익: ... (30일 추세: ...) — [한 줄 해설]
- 추정 거래소 거래량: ...

## 3. 밸류에이션
- MVRV: ... [또는 "데이터 소스 제한으로 미수집"]

## 4. 시장 심리
- Fear & Greed Index: ... (...) — 최근 30일 평균: ...

## 5. 종합 분석 및 신호

| 항목 | 값 | 점수 |
|---|---|---|
| A. 시장심리 | ... | +/-... |
| B. 밸류에이션 | ... | +/-... |
| C. 네트워크 펀더멘털 | ... | +/-... |
| D. 사용자 활동 | ... | +/-... |
| E. 가격 모멘텀 | ... | +/-... |
| **총점** | | **...** |

**종합 신호: [매수 우위 / 중립·관망 / 매도(차익실현)·관망 우위]**

[3~5문장으로 위 점수의 근거를 자연어로 요약. 어떤 지표가 신호를 주도했는지, 상충되는 지표가 있다면 무엇인지 명시.]

## 6. 유의사항
⚠️ 본 리포트는 공개 API 데이터를 기반으로 규칙에 따라 자동 생성된 정보 제공용 콘텐츠이며, 투자 자문이 아닙니다. 제시된 신호는 단순 점수 규칙에 의한 휴리스틱 해석이며 미래 수익을 보장하지 않습니다. 투자 결정과 그 결과에 대한 책임은 전적으로 투자자 본인에게 있습니다.

---
데이터 수집 시각: {실행 시각, KST} · 출처: CoinGecko, blockchain.com, mempool.space, alternative.me, CoinMetrics Community API
```

## 4. 요약 로그 갱신

`reports/SUMMARY.md`를 열어 표의 **마지막 행 다음**에 새 행을 추가하세요 (없으면 헤더와 함께 새로 생성):

```markdown
# 비트코인 일일 리포트 요약 로그

| 날짜 | 가격(USD) | 24h% | F&G | 총점 | 신호 |
|---|---|---|---|---|---|
| {YYYY-MM-DD} | $... | ...% | ...(...) | ... | ... |
```

## 5. 텔레그램 전송

`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 값을 다음 우선순위로 확보하세요:
1. 프로젝트 루트에 `.env` 파일이 있으면 그 값을 사용 (로컬 실행 시).
2. `.env`가 없는 환경(예: 클라우드 예약 루틴)이라면, 이번 작업을 지시한 프롬프트/태스크 메시지에 직접 포함된 `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` 값을 사용하세요.

**이 값들은 어떤 경우에도 응답 텍스트, 리포트 파일, 커밋 메시지, 로그에 그대로 노출하지 마세요** (전송 명령에만 사용).

### 5-A. 요약 메시지 전송 (sendMessage)
2절 결과를 바탕으로 5~8줄 분량의 plain-text 요약을 작성하세요 (마크다운 특수문자로 인한 전송 오류를 피하기 위해 `parse_mode` 없이 일반 텍스트로 전송). 형식 예시:

```
🟠 비트코인 일일 리포트 — {YYYY-MM-DD}
현재가: $... (24h ...%, 7d ...%)
종합 신호: [매수 우위 / 중립·관망 / 매도(차익실현) 우위] (총점 ...)
근거: [핵심 1줄] / [핵심 1줄]
F&G: ... (...) · MVRV: ... · 해시레이트 추세: ...
⚠️ 투자 자문 아님, 정보 제공용
```

다음 명령으로 전송하세요 (쉘에서 `.env`를 읽어 변수로 사용):

```bash
export $(grep -v '^#' .env | xargs)
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  --data-urlencode chat_id="${TELEGRAM_CHAT_ID}" \
  --data-urlencode text="<위 요약 텍스트>"
```

### 5-B. 전체 리포트 파일 첨부 (sendDocument)
```bash
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument" \
  -F chat_id="${TELEGRAM_CHAT_ID}" \
  -F document=@"reports/{YYYY-MM-DD}.md"
```

두 호출 모두 응답 JSON의 `"ok":true` 여부를 확인하세요. `"ok":false`면 에러 메시지를 확인해 원인(토큰 오류, chat_id 오류, 메시지 형식 오류 등)을 파악하고, 안 되면 사유를 다음 절(마무리)에 보고하되 절대 토큰 값 자체는 출력하지 마세요.

## 6. 변경사항 커밋 및 푸시

이 디렉토리가 git 저장소라면, 작업 결과를 누적 보존하기 위해 반드시 커밋·푸시하세요:

```bash
git add reports/
git commit -m "Daily BTC report {YYYY-MM-DD}"
git push origin HEAD
```

`.env`는 `.gitignore`에 의해 추적되지 않으므로 실수로 커밋되지 않습니다. 혹시라도 `.env`가 staged 상태로 보이면 즉시 `git restore --staged .env`로 제외하세요.

## 7. 마무리
- 작성한 두 파일(`reports/YYYY-MM-DD.md`, `reports/SUMMARY.md`)의 경로를 응답에 명시하세요.
- 텔레그램 전송 성공/실패 여부를 명시하세요.
- 커밋/푸시 성공 여부를 명시하세요.
- 데이터 수집에 실패한 항목이 있었다면 어떤 항목이었는지 간단히 언급하세요.
