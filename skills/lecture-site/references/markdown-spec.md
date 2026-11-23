# 원고 형식(빌더 입력 계약)

## 차례
1. 폴더 구조 · 2. lecture.md · 3. chapters/*.md · 4. 그림(fig) 블록 · 5. deck.md · 6. sources.md · 7. 자주 하는 실수

## 1. 폴더 구조
```
<강의>/
├ lecture.md        강의 정보(머리말만 씀)
├ plan.md           기획서(빌드에 안 쓰임)
├ chapters/         장 하나 = 파일 하나. 파일 이름 순서가 장 순서(01-a.md, 02-b.md …)
├ deck.md           발표 덱(없으면 빌드 때 본문에서 자동 초안)
├ sources.md        근거 목록
├ assets/           (선택) hero.jpg, 그림용 이미지
└ site/             빌드 결과(매번 새로 만듦)
```

## 2. lecture.md
머리말은 `key: value` 한 줄씩만 쓴다(중첩·목록 없음).

| 키 | 뜻 |
|---|---|
| title, subtitle | 홈 히어로 제목과 한 줄 |
| author, date | 지은이(바닥·덱 표지·판권), 날짜 |
| cta | 히어로 버튼 글자(기본 "1장부터 읽기") |
| toc_label | 홈 장 목록 위 작은 제목 |
| vol1, vol2 … | 권 제목. 장의 `vol:` 번호와 짝 |
| hero | (선택) 히어로 뒤 이미지. 없으면 덱의 첫 그림을 흐리게 깔아 씀 |
| sources_lede | 근거 쪽 머리 문단 |

## 3. chapters/*.md
```markdown
---
id: a              # 쪽 주소(/a/). 영문 소문자 한두 글자 권장
title: 여는 부분
lede: 장을 한 문장으로
vol: 1
---

첫 '##' 앞은 장 도입(장면 → 질문 → 예고).

## 꼭지 제목 = 주장 문장 {#a-01}        ← id 생략 시 a-01, a-02 … 자동
## 깊이 들어가는 꼭지 {#a-02 .deep}     ← 「더 깊이」: 덱 ?core=1 에서 빠짐
### 소제목(같은 꼭지의 두 번째 그림 앞에)
```

본문에서 쓸 수 있는 것: 문단, `**굵게**`, `*기울임*`, `` `코드` ``, `[링크](url)`, `-`/`1.` 목록, `>` 인용, 표(`| a | b |`), 코드 블록, 그리고 다음 세 가지.

- **근거**: 문장 끝 `[^F-1001]`, 여러 개는 `[^F-1001][^F-1002]`
- **조건과 한계**(접는 칸): `:::cond 조건과 한계` … `:::` (안에 목록)
- **상자**: `:::key 기억할 것` / `:::tip` / `:::warn` / `:::note` … `:::`

## 4. 그림(fig) 블록
````markdown
```fig a-01-a          ← 그림 id(강의 전체에서 유일). 덱의 fig= 와 같은 값
type: bars
tone: dark            ← (선택) 어두운 판. 덱에서도 어두운 장이 됨
steps: yes            ← (선택) 덱에서 둘째 행부터 누를 때마다 하나씩
note: 그림 위 작은 설명  ← (선택)
caption: 그림이 말하는 것 한 문장(접근성·alt, 필수에 가깝게)
- 이름 | 값 | 표시값 | hl      ← 행. hl(또는 *) = 구리색 강조, 한 그림에 하나만
```
````

| type | 키 | 행 형식 | 쓰는 때 |
|---|---|---|---|
| stat | value, label, grid(칸 수), grid_note, mark | `- 이름 \| 값 \| hl` (보조 수치) | 숫자 하나가 주인공 |
| bars | unit, max | `- 이름 \| 값 \| 표시값 \| hl` | 크기 비교 |
| stack | total | `- 이름 \| 값 \| 설명 \| hl` | 전체 중 몫(구성) |
| compare | arrow: yes | `- 제목 \| 큰 값 \| 설명 \| hl` | 전후·선택지 2~4개 |
| flow | | `- 단계 \| 설명 \| hl` | 순서·과정(7개 넘으면 세로) |
| list | | `- 항목 \| 설명 \| hl` | 요점 목록(5개 넘으면 두 단) |
| statement | text(`==강조==`), by, size | | 큰 문장 하나 |
| table | head: `a \| b \| c` | `- 칸 \| 칸 \| 칸` | 정확한 값을 나란히 |
| sankey | target(기둥 이름), callout, callout_sub, show_values: no | `- 이름 \| 값 \| 설명 \| hl 또는 rest` | 여러 몫이 한 전체로 흘러 들어감(원본 「입력 전부터 들어 있는 세 항목」 꼴). rest = 빗금 「그 밖의 것」, callout = hl 묶음 옆 큰 말 |
| timeline | | `- 시점 \| 사건 \| 설명 \| hl` | 시간 순서(휴대폰에서는 세로) |
| terminal | title | `- $ 명령` / `- 출력 줄` / `- 줄 \| hl` | 명령과 결과 화면. `$ `·`> `로 시작하면 입력 줄 |
| image | src(assets/ 기준), ratio(16:9) | | 사진·스크린샷(데이터 URI로 넣음) |
| illust | prompt(장면 묘사), ratio, tone, style(선택), src(기본 `assets/illust/<id>.png`) | | 삽화. 파일이 없으면 점선 「삽화 자리」가 나오고 빌드가 경고함. 만드는 법은 아래 4-1 |
| (raw) | 블록 안에 `<svg viewBox="0 0 1760 H" …>` | | 위 형식으로 안 되는 그림 |

### 4-1. 삽화(illust) 만들기
````markdown
```fig a-00-i
type: illust
prompt: A presenter hands a single glowing link card to attendees while printed slides lie unused on the table
caption: 슬라이드 묶음 대신 링크 하나를 건네는 장면
```
````
1. `python3 scripts/illust.py gen <강의폴더>` — ChatGPT 이미지(codex CLI, ChatGPT 로그인)로 없는 삽화를 최대 5장씩 동시에 만들어 `assets/illust/<id>.png`에 저장한다. 한 장에 1~2분.
2. 안 되면(codex 없음·로그인 안 됨·사용량 한도·시간 초과) 스크립트가 이유를 보여 주고 `<강의폴더>/illustrations.md`에 **완성 프롬프트와 저장 경로**를 적는다. 사용자가 ChatGPT에서 직접 만들어 그 경로에 저장한다.
3. `build`를 다시 돌리면 본문·덱·책에 들어간다. 프롬프트 시트만 필요하면 `illust.py sheet <폴더>`.

완성 프롬프트 = 덱 색 규칙(남색 4단계 + 구리색 하나, 흰 바탕 또는 tone: dark면 남색 바탕, 글자·숫자·로고 없음) + `Scene:` 장면 묘사. `style:`을 주면 색 규칙 대신 그 문장을 쓴다.

**carry 전환을 살리는 법**: 같은 꼭지의 glance 그림과 explain 그림에 **같은 이름의 행**을 두면, 덱에서 넘길 때 그 행이 막대→카드처럼 제자리로 옮겨 간다(data-key = 행 이름). raw SVG에서는 `<g data-key="이름">`을 직접 단다.

## 5. deck.md
```markdown
## 슬라이드 제목 {kind=glance chapter=a topic=a-01 fig=a-01-a}

발표 스크립트 문단(발표자 노트에 나옴).

- 목록은 「조건과 한계」로 노트에 들어감

근거: F-8201, F-1025

## 다음 장 {kind=explain chapter=a topic=a-01 fig=a-01-b}
```

| 속성 | 값 |
|---|---|
| kind | `title` 표지 카드 · `cover` 장 표지(어두움, `> 질문`) · `glance` 한눈 그림 · `explain` 설명 그림 · `statement` 큰 문장(그림 없음) |
| chapter | 장 id. 앞 장과 다르면 wipe 전환 |
| topic | 꼭지 id. 같은 topic의 glance→explain이면 carry 전환 |
| fig | 그림 id(본문의 그림 재사용). 슬라이드 안에 ```fig 블록을 직접 써도 됨 |
| dark / .deep | 어두운 장 / 「더 깊이」(?core=1에서 빠짐) |
| `> 한 줄` | title=부제, cover·statement=질문, 그 밖=제목 아래 부제 |

## 6. sources.md
```markdown
### F-1001
- 주장: 근거가 말하는 사실 한 문장
- 종류: 공식 | 직접 잰 값 | 계산값 | 문헌 | 인터뷰 | 관찰
- 출처: https://… (URL이 아니면 글자로 보임)
- 확인: 2026-11-12
- 메모: 측정 조건·한계(선택)
```
ID 접두는 자유(`F-`, `O-`, `S-` …). 본문 `[^id]`, 덱 `근거: id`와 글자가 같아야 한다. 근거 쪽은 그 근거를 처음 쓴 장 아래에 묶이고, 아무 데서도 안 쓰면 「그 밖의 근거」로 간다.

## 7. 자주 하는 실수
- 머리말 값에 `:`가 또 들어가면 첫 `:`만 키 구분으로 쓰므로 괜찮다. 다만 줄바꿈은 안 된다.
- 그림 id 중복 → 뒤의 것이 이김(check가 경고).
- `hl`을 여러 행에 → 강조가 사라진다. 한 그림에 하나만.
- glance와 explain의 행 이름이 조금씩 다르면("디졸브" vs "디졸브 전환") carry가 안 걸린다.
