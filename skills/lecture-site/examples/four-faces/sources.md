# 근거 목록

### O-001
- 주장: 첫 화면 위 띠의 메뉴는 본문, 발표 덱, 책으로 보기, 근거 넷이고 책으로 보기는 권과 장 목록으로 펼쳐짐
- 종류: 관찰
- 출처: https://token-saving-guide.vercel.app/index.html
- 확인: 2026-11-12

### O-002
- 주장: 발표 덱은 슬라이드 70장(밝은 장 65, 어두운 장 4, 표지 1)을 한 HTML 파일에 담았고, 본문 도판과 같은 그림 id(a-01-a 등)를 씀
- 종류: 관찰
- 출처: https://token-saving-guide.vercel.app/deck/index.html
- 확인: 2026-11-12

### O-003
- 주장: 근거 쪽의 근거는 318개이고, 본문은 7장, 책은 3권임
- 종류: 관찰
- 출처: https://token-saving-guide.vercel.app/sources/index.html
- 확인: 2026-11-12

### O-004
- 주장: 근거마다 번호, 주장, 종류(공식·직접 잰 값·계산값), 출처, 확인일, 쓰인 곳이 붙고, 꼭지마다 조건과 한계를 접는 칸에 둠
- 종류: 관찰
- 출처: https://token-saving-guide.vercel.app/a/index.html
- 확인: 2026-11-12

### O-005
- 주장: 사이트는 Pretendard(400~800)와 D2Coding을 쓰고, 글자 위계는 t1 clamp(44px,6.1vw,88px), t2 clamp(28px,3.4vw,50px), t3 clamp(17px,1.35vw,20px)와 글자색 네 단계로 나눔
- 종류: 관찰
- 출처: https://token-saving-guide.vercel.app/assets/tokens.css
- 확인: 2026-11-12

### O-006
- 주장: 덱 토큰은 흰 종이(#FFFFFF), 남색 #123A63·#3378AD·#7FB2D9, 구리색 #C2662E, 글자색 #0B1F33임
- 종류: 관찰
- 출처: https://token-saving-guide.vercel.app/deck/index.html
- 확인: 2026-11-12

### O-007
- 주장: 덱 엔진의 전환 값은 crossfade 0.3초, matching-token-transform 0.6초, wipe 0.9초(4px 경계선), 단계 등장 y24px 0.5초임
- 종류: 관찰
- 출처: https://token-saving-guide.vercel.app/deck/index.html
- 확인: 2026-11-12
- 메모: 엔진 코드의 상수를 읽은 값

### O-008
- 주장: 덱은 N 키로 발표자 노트, F 키로 전체 화면, 숫자와 Enter로 장 이동을 지원함
- 종류: 관찰
- 출처: https://token-saving-guide.vercel.app/deck/index.html
- 확인: 2026-11-12

### O-009
- 주장: 근거 318개의 종류는 공식 248, 직접 잰 값 47, 논문 13, 제3자 9, 계산값 1임
- 종류: 관찰
- 출처: https://token-saving-guide.vercel.app/sources/index.html
- 확인: 2026-11-12
- 메모: 근거 쪽의 종류 표시(m-kind)를 세어 더한 값

### O-010
- 주장: 덱 엔진은 장이 바뀌는 wipe 뒤 0.6초에 제목과 그림을 아래 18px에서 0.4초 동안 0.12초 간격으로 차례로 보여 줌
- 종류: 관찰
- 출처: https://token-saving-guide.vercel.app/deck/index.html
- 확인: 2026-11-12
- 메모: 엔진 상수 hierAt 0.6, hierY 18, hierDur 0.4, hierGap 0.12

### O-011
- 주장: lecture-site 빌더로 이 예제를 빌드하면 장 3, 꼭지 7, 그림 12, 덱 17장, 근거 11, 권 2를 셈(삽화 파일까지 갖추면 확인할 것 없음을 출력함)
- 종류: 직접 잰 값
- 출처: lecture-site 스킬 scripts/build.py 실행 출력
- 확인: 2026-11-12
