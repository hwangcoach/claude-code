# 원본 분석: token-saving-guide.vercel.app

2026-11-12에 원본 HTML·CSS·JS를 직접 받아 읽고 정리한 기록이다. 정적 사이트라 REA는 쓰지 않았다.
이 스킬의 `assets/`와 `scripts/`는 이 구조를 재현한다.

## 1. 정보 구조 (4면 + 홈)

```
index.html              홈: 히어로 → 장 목록 → 본문 읽기 → 발표 덱 → 책으로 보기 → 근거
a/ … g/index.html       본문: 장(chapter) 하나 = 한 쪽. 장 id는 a, b, c …
deck/index.html         발표 덱: 1920×1080 단일 파일(글꼴·그림·엔진 전부 인라인, 약 2MB)
books/index.html        책 서가: 권(volume) 3개, 표지 + 장 목록
books/<n>/index.html    권 첫머리: 표지 · 장 목록 · 표지/차례/판권 쪽 넘김 · PDF 받기
books/<n>/<ch>/         장을 인쇄본 쪽 이미지로 넘겨 보기(가로 스크롤, 스냅)
sources/index.html      근거 목록: F-#### 318개, 장별 묶음, 종류·URL·확인일·쓰인 곳
```

- 위 띠(nav)는 모든 쪽 공통: 강의 이름 | 본문 · 발표 덱 · 책으로 보기(▾ 펼침: 권 → 장) · 근거
- 링크 하나만 공유하면 홈에서 네 면이 모두 보이도록 설계됨. 홈의 각 구역이 그 면의 "실물 한 장"(스크린샷·덱 한 장·표지 3권)을 보여 줌.
- 하나의 원고(장·꼭지·그림·근거 ID)가 네 면에 동시에 쓰임. 같은 그림 id(`a-01-a`)가 본문 도판과 덱 장에 함께 나옴.

## 2. 본문 쪽 (`body.p-chunk`)

```
main.ch  (grid: 248px 왼쪽 단 | 본문 단, 사이 clamp(40px,5vw,88px))
├ aside.rail      sticky 꼭지 목록. 화면 위 1/3 선을 지난 마지막 꼭지에 .is-cur (scrollspy)
└ div.doc
  ├ header.doc-head   kick(1권 · 1장) / h1 mask-reveal / lede(한 줄 요약) / chview(이 장을 책으로 보기 · 1권 1-8쪽)
  │                   details.toc-m (좁은 화면에서 rail 대신)
  ├ div.prose.open    장 도입(가상 인물 장면 → 질문)
  ├ article.topic#a-01 (꼭지 = 주장 하나)
  │   h2.topic-h      주장 문장 그대로 ("인사 한 줄에 입력 51,071토큰")
  │   figure.plate    밝은 도판 판 안에 SVG(넓은 판 .fw / 좁은 판 .fn 두 벌)
  │   div.prose       설명. 수치마다 <sup class="ref"><a href="#r-2">2</a></sup>
  │   h3.sub + figure 같은 꼭지의 두 번째 그림(설명용)
  │   details.cond    「조건과 한계」 접는 단: 측정 환경, 반복 횟수, 확인 못 한 것
  ├ section.refs      이 장의 근거: 번호 · 주장 · 종류(공식/직접 잰 값/계산값) · URL · 확인일 · 근거 목록 링크
  └ nav.pn            다음 장 · N장 / 장 이름
```

본문 글자: 18px, 행간 1.86, 한 줄 최대 40em, `word-break:keep-all`, `text-wrap:pretty`.

## 3. 디자인 토큰 (사이트 = Linear 계열 다크)

```css
--canvas:#010102; --surface-1:#0f1011; --surface-2:#141516; --surface-3:#18191a;
--hairline:#23252a; --hairline-strong:#34343a;
--ink:#f7f8f8; --ink-muted:#d0d6e0; --ink-subtle:#8a8f98; --ink-tertiary:#62666d;
--primary:#5e6ad2; --primary-hover:#828fff; --plate:#f5f6f6; --light:206 214 232;
--t1: clamp(44px,6.1vw,88px)/1.06/-0.035em/600
--t2: clamp(28px,3.4vw,50px)/1.18/-0.028em/600
--t3: clamp(17px,1.35vw,20px)/1.6/-0.008em/400
--container:1320px; --gutter:clamp(20px,4.2vw,60px); --gap-section:clamp(120px,15vw,220px)
--r-btn:8px; --r-plate:12px; --r-frame:16px; --ease-out:cubic-bezier(.22,1,.36,1)
```

- 글꼴: **Pretendard** 400/500/600/700/800(woff2 자체 호스팅), 코드·수치 표는 **D2Coding**.
- 위계는 굵기 600 하나로 거의 다 해결하고 색(ink → muted → subtle → tertiary)으로 나눔.
- 판(plate): 어두운 바탕 위 밝은 도판 판 + 아래로 번지는 차가운 빛 그림자 `0 60px 120px -70px rgb(206 214 232 / .35)`.

## 4. 덱 토큰 (덱 = 밝은 종이 + 남색)

```css
--paper:#FFFFFF; --alt:#EEF2F6; --n100:#D5E4F1; --n300:#7FB2D9; --n500:#3378AD; --n700:#123A63;
--teal:#0E6E62; --copper:#C2662E (글자용 #A9501C); --ink:#0B1F33; --ink60:#4E6074;
--dark:#0B1F33; --on-dark:#F3F6FA; --dark-muted:#9DB3C9;
제목 62px → 56px → 44px(2줄 넘으면 2px씩 줄임), 700, -0.025em
여백 70px 80px 56px, 쪽 번호 26px #8696A7 오른쪽 아래, 진행 막대 4px #7FB2D9 맨 아래
```

- 색은 뜻이 고정됨(같은 색 = 같은 뜻). 원본: n300 = 캐시에서 읽음, n700 = 새로 저장, copper = 강조·주의.
- 슬라이드 종류(`data-kind`): `title`(표지 카드) · `cover`(장 표지, 어두움) · `glance`(한눈 그림, 대개 어두움) · `explain`(설명 그림, 단계별) · `nofig`(큰 문장).
- 장마다 `data-chunk`(장 id), `data-topic`(꼭지 id), `data-level`(핵심 / 더 깊이).
- `aside.notes`에 발표 스크립트(구어체 3문장) + 「조건과 한계」 목록 + 근거 id.

## 5. 움직임

### 홈 (GSAP 3.14 타임라인)
| 대상 | 효과 | 값 |
|---|---|---|
| 뒤 이미지 | 당겨 오기 → 숨쉬기 | opacity 0→.5, scale 1.12→1.04, 2.6s power2.out / 그 뒤 scale 1.04↔1.0, opacity .5↔.6, 14s yoyo |
| 제목 | mask reveal | yPercent 110→0, 1.05s power3.out, 0.35s 시작 |
| 한 줄 | blur reveal | blur 8px→0 + 투명→보임, .8s, 0.8s 시작 |
| 버튼 | rise | y16→0, .6s, 1.0s 시작 |
| 구역 제목 | reveal | y32→0, .9s power3.out (IntersectionObserver, -14%) |
| 실물 판 | media | y48→0, scale .97→1, 1.2s |
| 서가 표지 | stagger | y40→0, 1.2s, 0.14s 간격 |
| 뒤 이미지 | 시차 | 스크롤의 0.3배 |
| 장 목록 | 줄 밝힘 | 줄 가운데가 화면 62% 선을 지나면 tertiary → ink, .9s |
| 위 띠 | 스크롤 8px 넘으면 | 반투명 #010102 .78 + blur 14px + hairline |

### 덱 (자체 엔진, 05_덱/틀의 전환 표)
| 전환 | 언제 | 값 |
|---|---|---|
| crossfade | 기본, 뒤로 갈 때 | A 1→0, B 0→1 동시 0.3s linear |
| wipe | 장(chunk)이 바뀔 때 | clip-path inset(0 100% 0 0)→0, 0.9s linear, 4px 구리색 경계선이 함께 지나감. 그 뒤 [data-anim] 위계 등장 y18, .4s power3.out, 0.12s 간격, 0.6s 시작 |
| carry (magic move) | 같은 꼭지 glance → explain | 같은 data-key / 같은 글자·같은 크기의 요소는 남아 제자리로 0.6s power2.inOut 이동·변형, 나머지 0.25s 사라짐, B는 0.35s에 0.25s 등장 |
| step | 한 장 안의 단계 | 새 요소 y24→0, 0.5s power2.out, 0.06s 간격 |

- 조작: →/Space/PageDown/Enter 다음, ←/PageUp/Backspace 이전, Home/End, 숫자+Enter 이동, **N** 발표자 노트, **F** 전체 화면, 클릭 다음, URL `#번호` 동기화.
- 쿼리: `?still=1` 움직임 끔(캡처용), `?core=1` 「더 깊이」 장 빼고 핵심만.
- 1920×1080 무대를 창에 맞춰 scale + 가운데 정렬.
- `prefers-reduced-motion`이면 모든 전환을 즉시 바꿈.

## 6. 책으로 보기
- 인쇄용 PDF(A5 비율 1240×1736)를 쪽 JPG로 잘라 가로 스크롤 `ol.flip`에 나열. 버튼·화살표 키로 한 화면 분량씩 넘김, "1-3쪽 / 모두 8쪽" 표시.
- 권 첫머리에는 표지·차례·판권만, 장 쪽에는 그 장의 쪽만. PDF 파일 받기 링크.
- 이 스킬은 쪽 이미지 대신 **브라우저에서 원고를 A5 쪽으로 직접 나누는 페이지네이터**로 바꿨다(별도 PDF 조판 불필요, 인쇄하면 그대로 A5 PDF).

## 7. 근거 체계
- 사실 문장 하나 = 근거 ID 하나 이상(`F-1001`). 종류: 공식 / 직접 잰 값 / 계산값 (+ 문헌·인터뷰로 확장 가능).
- 본문에서는 장마다 1부터 다시 번호를 매긴 각주, 장 끝에 그 장의 근거, 근거 쪽에는 전체 목록 + 쓰인 곳 역링크.
- 「조건과 한계」를 본문과 분리해 접어 둠: 잰 환경, 반복 횟수, 가상 장면 여부, 확인하지 못한 것.
- 가상 인물·회사 장면을 쓸 때는 "(가상 회사)"를 본문에 바로 밝힘.

## 8. 글쓰기 결
- 제목은 주장 문장 그대로, 숫자를 넣음("출력 토큰의 값은 입력 토큰의 5배").
- 장 도입 = 가상 인물의 구체적 장면 → 독자가 품을 질문 한 줄 → 이 장에서 볼 것.
- 용어는 처음 나올 때 **굵게** + 한 문장 정의.
- 모르는 것은 모른다고 씀("무엇으로 찼는지는 밝히지 못했습니다").
- 발표 스크립트는 슬라이드 제목을 되풀이하지 않고 구어체 3문장 안팎.
