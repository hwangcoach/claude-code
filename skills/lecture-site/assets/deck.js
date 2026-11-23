/* 덱 엔진. 원본 엔진(GSAP)의 전환 표를 Web Animations API 로 옮김. 외부 라이브러리 없음.
   전환: crossfade(기본, 뒤로) · wipe(장이 바뀔 때, 구리색 경계선) · carry(같은 꼭지 glance→explain: 같은 data-key/같은 글자는 제자리로 옮겨 감)
   단계: 그림 안 .beat[data-beat] 가 한 번 누를 때마다 하나씩(fade-slide y24, 0.5s, 0.06s 간격)
   조작: → Space PageDown Enter 다음 · ← PageUp Backspace 이전 · Home End · 숫자+Enter 이동 · N 노트 · F 전체 화면 · ? 도움말 · 클릭/스와이프
   주소: #번호 동기화 · ?still=1 움직임 끔 · ?motion=1 동작 줄이기 설정이어도 움직임 켬 · ?core=1 「더 깊이」 장 빼기 */
(function () {
  'use strict';
  var Q = new URLSearchParams(location.search), STILL = Q.get('still') === '1', CORE = Q.get('core') === '1', FORCE = Q.get('motion') === '1';
  var RM = matchMedia('(prefers-reduced-motion: reduce)');
  var stage = document.getElementById('stage'), num = document.getElementById('num'), bar = document.getElementById('bar'),
      edge = document.getElementById('edge'), panel = document.getElementById('notesPanel'), help = document.getElementById('help');
  var slides = [].slice.call(document.querySelectorAll('.slide'));
  if (CORE) slides = slides.filter(function (s) { if (s.dataset.level === '더 깊이') { s.parentNode.removeChild(s); return false; } return true; });
  var N = slides.length, cur = -1, step = 1, running = [], typed = '', K = 1;
  var T = { fade: 300, carry: 600, out: 250, inAt: 350, inDur: 250, wipe: 900, hierAt: 600, hierY: 18, hierDur: 400, hierGap: 120,
            stepY: 24, stepDur: 500, stagger: 60 };
  var EZ = { p2o: 'cubic-bezier(.25,.46,.45,.94)', p3o: 'cubic-bezier(.215,.61,.355,1)', p2io: 'cubic-bezier(.455,.03,.515,.955)' };
  function motion() { return !STILL && (FORCE || !RM.matches) && !!Element.prototype.animate; }
  function A_(el, kf, o) { var a = el.animate(kf, Object.assign({ fill: 'both' }, o)); running.push(a); return a; }

  function fit() {
    K = Math.min(innerWidth / 1920, innerHeight / 1080);
    stage.style.transform = 'translate(' + ((innerWidth - 1920 * K) / 2) + 'px,' + ((innerHeight - 1080 * K) / 2) + 'px) scale(' + K + ')';
  }
  // 제목이 두 줄을 넘으면 62 → 56 → 44px 까지 2px 씩 줄임
  function fitTitle(sl) {
    var h = sl.querySelector('h1[data-title]'); if (!h) return;
    var cs = getComputedStyle(document.documentElement), mx = parseFloat(cs.getPropertyValue('--title-max')), fl = parseFloat(cs.getPropertyValue('--title-floor'));
    var s = mx; h.style.fontSize = s + 'px';
    var lines = function () { return Math.round(h.getBoundingClientRect().height / K / (s * 1.2)); };
    while (lines() > 2 && s > fl) { s -= 2; h.style.fontSize = s + 'px'; }
  }

  // ---- 단계 ----
  function beatGroups(sl) {
    var m = {};
    [].forEach.call(sl.querySelectorAll('svg .beat'), function (e) { var k = +e.getAttribute('data-beat') || 1; (m[k] = m[k] || []).push(e); });
    return Object.keys(m).map(Number).sort(function (a, b) { return a - b; }).map(function (k) { return m[k]; });
  }
  function maxStep(i) { return beatGroups(slides[i]).length + 1; }
  function applyStep(sl, st, animate) {
    var g = beatGroups(sl), fresh = null;
    g.forEach(function (els, k) { var on = k < st - 1; els.forEach(function (e) { e.style.visibility = on ? '' : 'hidden'; }); if (on && k === st - 2) fresh = els; });
    if (animate && fresh && motion()) {
      fresh.forEach(function (e, j) { A_(e, [{ opacity: 0, transform: 'translateY(' + T.stepY + 'px)' }, { opacity: 1, transform: 'none' }], { duration: T.stepDur, delay: j * T.stagger, easing: EZ.p2o }); });
    }
  }

  function mark(i) {
    slides.forEach(function (s, k) { s.classList.toggle('on', k === i); s.classList.remove('top'); });
    var sl = slides[i];
    num.textContent = (i + 1); bar.style.width = ((i + 1) / N * 100) + '%';
    stage.classList.toggle('ondark', sl.classList.contains('dark'));
    var nt = sl.querySelector('.notes'); panel.innerHTML = nt ? nt.innerHTML : '';
    history.replaceState(null, '', location.pathname + location.search + '#' + (i + 1));
  }
  function finish() {
    var r = running; running = [];
    r.forEach(function (a) { try { a.finish(); } catch (e) { /* 이미 끝남 */ } });
    r.forEach(function (a) { try { a.cancel(); } catch (e) { /* 무시 */ } });
    if (stage.__done) { var f = stage.__done; stage.__done = null; f(); }
  }
  function clean(el) {
    if (!el) return;
    el.style.opacity = ''; el.style.clipPath = ''; el.style.backgroundColor = '';
    [].forEach.call(el.querySelectorAll('[data-carry-hide]'), function (e) { e.style.visibility = ''; e.removeAttribute('data-carry-hide'); });
  }

  function show(i, st, how) {
    finish(); i = Math.max(0, Math.min(N - 1, i));
    var A = cur >= 0 ? slides[cur] : null, B = slides[i];
    if (A === B) { step = st; applyStep(B, st, false); return; }
    cur = i; step = st;
    B.classList.add('on'); fitTitle(B); applyStep(B, st, false);
    if (!A || !how || !motion()) { mark(i); clean(A); clean(B); return; }
    B.classList.add('top');
    num.textContent = (i + 1); bar.style.width = ((i + 1) / N * 100) + '%';
    var done = function () { mark(i); clean(A); clean(B); edge.style.display = 'none'; };
    stage.__done = done;
    if (how === 'chunk') wipe(A, B); else if (how === 'pair') carry(A, B); else crossfade(A, B);
    Promise.all(running.map(function (a) { return a.finished; })).then(function () { if (stage.__done === done) { stage.__done = null; running = []; done(); } }, function () {});
  }
  function crossfade(A, B) {
    A_(B, [{ opacity: 0 }, { opacity: 1 }], { duration: T.fade, easing: 'linear' });
    A_(A, [{ opacity: 1 }, { opacity: 0 }], { duration: T.fade, easing: 'linear' });
  }
  function wipe(A, B) {
    edge.style.display = 'block';
    A_(B, [{ clipPath: 'inset(0% 100% 0% 0%)' }, { clipPath: 'inset(0% 0% 0% 0%)' }], { duration: T.wipe, easing: 'linear' });
    A_(edge, [{ transform: 'translateX(0)' }, { transform: 'translateX(1916px)' }], { duration: T.wipe, easing: 'linear' });
    [].forEach.call(B.querySelectorAll('[data-anim]'), function (e, k) {
      A_(e, [{ opacity: 0, transform: 'translateY(' + T.hierY + 'px)' }, { opacity: 1, transform: 'none' }], { duration: T.hierDur, delay: T.hierAt + k * T.hierGap, easing: EZ.p3o });
    });
  }

  // ---- carry: FLIP. B 의 짝 요소를 A 자리에서 출발시켜 제자리로 ----
  function inside(e, set) { for (var x = e; x && x !== document; x = x.parentNode) if (set.has(x)) return true; return false; }
  function pairsOf(A, B) {
    var pairs = [], usedA = new Set(), usedB = new Set();
    [].forEach.call(B.querySelectorAll('svg [data-key]'), function (b) {
      if (inside(b.parentNode, usedB)) return;
      var k = b.getAttribute('data-key'), a = null;
      [].some.call(A.querySelectorAll('svg [data-key]'), function (x) { if (x.getAttribute('data-key') === k && !usedA.has(x)) { a = x; return true; } return false; });
      if (!a || a.style.visibility === 'hidden' || b.style.visibility === 'hidden') return;
      pairs.push([a, b, b.tagName.toLowerCase() === 'rect']); usedA.add(a); usedB.add(b);
    });
    // 키 없는 글자: 같은 글자 · 같은 크기 · 같은 굵기면 짝
    var sig = function (e) { return e.textContent + '|' + e.getAttribute('font-size') + '|' + e.getAttribute('font-weight'); };
    var pool = {};
    [].forEach.call(A.querySelectorAll('svg text, h1'), function (a) { if (inside(a, usedA)) return; (pool[sig(a)] = pool[sig(a)] || []).push(a); });
    [].forEach.call(B.querySelectorAll('svg text, h1'), function (b) {
      if (inside(b, usedB) || b.style.visibility === 'hidden') return;
      var l = pool[sig(b)]; if (!l || !l.length) return;
      var a = l.shift(); pairs.push([a, b, false]); usedA.add(a); usedB.add(b);
    });
    return { pairs: pairs, usedA: usedA, usedB: usedB };
  }
  function carry(A, B) {
    var P = pairsOf(A, B);
    if (!P.pairs.length) { crossfade(A, B); return; }
    var bgA = getComputedStyle(A).backgroundColor, bgB = getComputedStyle(B).backgroundColor;
    B.style.backgroundColor = 'transparent';
    P.pairs.forEach(function (p) {
      var a = p[0], b = p[1], ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      if (!(rb.width > 0 && rb.height > 0)) return;
      var bb = b.getBBox ? b.getBBox() : { width: rb.width / K }, u = bb.width > 0 ? rb.width / bb.width : K;
      var dx = (ra.left + ra.width / 2 - rb.left - rb.width / 2) / u, dy = (ra.top + ra.height / 2 - rb.top - rb.height / 2) / u;
      var sx = ra.width / rb.width || 1, sy = ra.height / rb.height || 1;
      if (!p[2]) { sx = sy = Math.max(.4, Math.min(2.5, Math.sqrt(sx * sy))); }
      b.style.transformBox = 'fill-box'; b.style.transformOrigin = '50% 50%';
      A_(b, [{ transform: 'translate(' + dx + 'px,' + dy + 'px) scale(' + sx + ',' + sy + ')' }, { transform: 'none' }], { duration: T.carry, easing: EZ.p2io });
      a.style.visibility = 'hidden'; a.setAttribute('data-carry-hide', '');
    });
    // 짝 없는 것: A 는 사라지고, B 는 0.35s 뒤에 나타남
    var leaves = 'svg rect, svg text, svg circle, svg path, svg polygon, svg line, svg image, h1, p';
    [].forEach.call(A.querySelectorAll(leaves), function (e) { if (!inside(e, P.usedA)) A_(e, [{ opacity: 1 }, { opacity: 0 }], { duration: T.out, easing: 'linear' }); });
    [].forEach.call(B.querySelectorAll(leaves), function (e) {
      if (inside(e, P.usedB) || e.closest('.notes')) return;
      if (e.tagName.toLowerCase() === 'rect' && e.parentNode.tagName.toLowerCase() === 'svg' && !e.previousElementSibling) return; // 판 바탕
      A_(e, [{ opacity: 0 }, { opacity: 1 }], { duration: T.inDur, delay: T.inAt, easing: 'linear' });
    });
    if (bgA !== bgB) A_(A, [{ backgroundColor: bgA }, { backgroundColor: bgB }], { duration: T.carry, easing: EZ.p2io });
  }

  function kindOf(a, b) {
    var A = slides[a], B = slides[b];
    if (b < a) return 'fade';
    if (B.dataset.kind === 'cover' || B.dataset.kind === 'title') return 'chunk';
    if (B.dataset.chunk && A.dataset.chunk && B.dataset.chunk !== A.dataset.chunk) return 'chunk';
    if (B.dataset.kind === 'explain' && B.dataset.topic && B.dataset.topic === A.dataset.topic) return 'pair';
    return 'fade';
  }
  function next() {
    if (stage.__done) { finish(); return; }   // 전환 중이면 먼저 끝까지
    finish();
    if (step < maxStep(cur)) { step++; applyStep(slides[cur], step, true); }
    else if (cur < N - 1) show(cur + 1, 1, kindOf(cur, cur + 1));
  }
  function prev() {
    if (running.length) finish();
    if (step > 1) { step--; applyStep(slides[cur], step, false); }
    else if (cur > 0) { var j = cur - 1; show(j, maxStep(j), null); }
  }
  function go(n) { if (n >= 1 && n <= N) show(n - 1, maxStep(n - 1), null); }

  addEventListener('keydown', function (e) {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    var k = e.key;
    if (/^[0-9]$/.test(k)) { typed = (typed + k).slice(-3); num.textContent = typed + ' →'; return; }
    if (k === 'Enter' && typed) { e.preventDefault(); var n = parseInt(typed, 10); typed = ''; go(n); num.textContent = cur + 1; return; }
    if (k === 'Escape') { typed = ''; num.textContent = cur + 1; document.body.classList.remove('shownotes'); help.hidden = true; return; }
    if (k === 'Backspace' && typed) { typed = typed.slice(0, -1); num.textContent = typed ? typed + ' →' : cur + 1; return; }
    typed = '';
    if (k === 'ArrowRight' || k === ' ' || k === 'PageDown' || k === 'Enter' || k === 'ArrowDown') { e.preventDefault(); next(); }
    else if (k === 'ArrowLeft' || k === 'PageUp' || k === 'Backspace' || k === 'ArrowUp') { e.preventDefault(); prev(); }
    else if (k === 'Home') { e.preventDefault(); show(0, 1, null); }
    else if (k === 'End') { e.preventDefault(); go(N); }
    else if (k === 'n' || k === 'N') document.body.classList.toggle('shownotes');
    else if (k === '?') help.hidden = !help.hidden;
    else if (k === 'f' || k === 'F') { if (document.fullscreenElement) document.exitFullscreen(); else if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen(); }
    num.textContent = cur + 1;
  });
  stage.addEventListener('click', function (e) { if (!panel.contains(e.target)) next(); });
  var tx = null;
  addEventListener('touchstart', function (e) { tx = e.touches[0].clientX; }, { passive: true });
  addEventListener('touchend', function (e) { if (tx === null) return; var dx = e.changedTouches[0].clientX - tx; tx = null; if (Math.abs(dx) > 50) { if (dx < 0) next(); else prev(); } }, { passive: true });
  addEventListener('resize', fit);
  addEventListener('hashchange', function () { var n = parseInt(location.hash.slice(1), 10); if (n && n - 1 !== cur) go(n); });
  fit();
  window.__deck = { count: N, go: go, next: next, prev: prev, cur: function () { return cur + 1; }, step: function () { return step; }, T: T };
  var start = function () { var h = parseInt(location.hash.slice(1), 10); if (h) go(h); else show(0, 1, null); document.documentElement.dataset.ready = '1'; };
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(start); else start();
})();
