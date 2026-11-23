/* 사이트 움직임. 외부 라이브러리 없이 Web Animations API(WAAPI)만 씀. 원본은 GSAP 3 타임라인이었고 값(시간·이징·순서)은 그대로 옮김.
   스크립트가 없어도 글, 그림은 모두 보임. 움직임 축소(prefers-reduced-motion)면 html.rm 이라 움직임 없이 다 보임.
   1) 위 띠: 스크롤 8px 넘으면 반투명 판 + 밑선   2) 「책으로 보기」 펼침(Esc, 바깥 누르기로 닫음)
   3) 홈: 히어로 등장(뒤 그림 당겨오기 → mask → blur → rise), 뒤 그림 숨쉬기·시차, 장 목록 줄 밝힘, 구역 등장
   4) 장 쪽: 지금 읽는 꼭지 표시(scrollspy), 제목 mask, 구역 등장 */
(function () {
  'use strict';
  var d = document, html = d.documentElement, body = d.body;
  var E = { out: 'cubic-bezier(.22,1,.36,1)', p2o: 'cubic-bezier(.25,.46,.45,.94)', p3o: 'cubic-bezier(.215,.61,.355,1)', sine: 'cubic-bezier(.37,0,.63,1)' };
  var motion = html.classList.contains('js') && !!Element.prototype.animate;

  function anim(el, kf, o) {
    if (!el) return null;
    var a = el.animate(kf, Object.assign({ fill: 'both' }, o));
    return a;
  }

  // ---- 위 띠 ----
  var nav = d.getElementById('nav');
  if (nav) {
    var onBar = function () { nav.classList.toggle('is-scrolled', scrollY > 8); };
    addEventListener('scroll', onBar, { passive: true }); onBar();
  }

  // ---- 책으로 보기 펼침 ----
  d.querySelectorAll('.bm').forEach(function (m) {
    var a = m.querySelector('.bm-a'), b = m.querySelector('.bm-b'), p = m.querySelector('.bm-p');
    if (!a || !b || !p) return;
    a.hidden = true; b.hidden = false;
    function set(open, back) { b.setAttribute('aria-expanded', open ? 'true' : 'false'); p.hidden = !open; if (!open && back) b.focus(); }
    b.addEventListener('click', function () { set(b.getAttribute('aria-expanded') !== 'true'); });
    m.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !p.hidden) { e.preventDefault(); set(false, true); } });
    d.addEventListener('click', function (e) { if (!p.hidden && !m.contains(e.target)) set(false); });
  });

  // ---- 구역 등장(IntersectionObserver) ----
  function reveal(sel, margin) {
    var els = [].slice.call(d.querySelectorAll(sel));
    if (!motion || !('IntersectionObserver' in window)) return;
    els.forEach(function (el) {
      var m = el.hasAttribute('data-media');
      el.style.opacity = '0';
      el.__kf = m ? [{ opacity: 0, transform: 'translateY(48px) scale(.97)' }, { opacity: 1, transform: 'none' }]
                  : [{ opacity: 0, transform: 'translateY(32px)' }, { opacity: 1, transform: 'none' }];
      el.__dur = m ? 1200 : 900;
    });
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        io.unobserve(e.target);
        var el = e.target;
        if (el.classList.contains('shelf')) {
          el.style.opacity = '1';
          [].forEach.call(el.children, function (c, i) {
            anim(c, [{ opacity: 0, transform: 'translateY(40px)' }, { opacity: 1, transform: 'none' }], { duration: 1200, delay: i * 140, easing: E.p3o });
          });
          return;
        }
        anim(el, el.__kf, { duration: el.__dur, easing: E.p3o }).onfinish = function () { el.style.opacity = ''; };
      });
    }, { rootMargin: '0px 0px ' + (margin || '-14%') + ' 0px' });
    els.forEach(function (el) { io.observe(el); });
  }

  // ---- 홈 ----
  if (body.classList.contains('p-home')) {
    var lis = [].slice.call(d.querySelectorAll('.toc li'));
    var bg = d.querySelector('.bg'), wrap = d.querySelector('.bgwrap');
    if (!motion) { lis.forEach(function (li) { li.classList.add('lit'); }); html.classList.add('done'); return; }
    html.classList.add('done');
    // 첫 화면 등장
    var bgIn = anim(bg, [{ opacity: 0, transform: 'scale(1.12)' }, { opacity: .5, transform: 'scale(1.04)' }], { duration: 2600, easing: E.p2o });
    anim(d.querySelector('.hero .mask-in'), [{ transform: 'translateY(110%)' }, { transform: 'translateY(0)' }], { duration: 1050, delay: 350, easing: E.p3o });
    anim(d.querySelector('[data-in="blur"]'), [{ opacity: 0, filter: 'blur(8px)' }, { opacity: 1, filter: 'blur(0)' }], { duration: 800, delay: 800, easing: E.p2o });
    anim(d.querySelector('[data-in="rise"]'), [{ opacity: 0, transform: 'translateY(16px)' }, { opacity: 1, transform: 'none' }], { duration: 600, delay: 1000, easing: E.p2o });
    // 등장 뒤: 뒤 그림이 아주 느리게 숨 쉼(scale 1.04↔1.0, 빛 .5↔.6, 14s 왕복)
    if (bgIn) bgIn.onfinish = function () {
      anim(bg, [{ opacity: .5, transform: 'scale(1.04)' }, { opacity: .6, transform: 'scale(1)' }], { duration: 14000, iterations: Infinity, direction: 'alternate', easing: E.sine });
    };
    reveal('[data-reveal],[data-media]');
    // 스크롤: 뒤 그림 시차(0.3배), 장 목록 줄 밝힘(줄 가운데가 화면 62% 선을 지나면)
    var onScroll = function () {
      var y = scrollY, vh = innerHeight;
      if (wrap && y < vh * 1.2) wrap.style.transform = 'translate3d(0,' + (y * .3).toFixed(1) + 'px,0)';
      lis.forEach(function (li) { var r = li.getBoundingClientRect(); if (r.top + r.height / 2 < vh * .62) li.classList.add('lit'); });
    };
    addEventListener('scroll', onScroll, { passive: true }); addEventListener('resize', onScroll); onScroll();
    return;
  }

  // ---- 장 쪽: 지금 읽는 꼭지(화면 위 3분의 1 선을 지난 마지막 꼭지) ----
  var rail = d.querySelector('.rail');
  var topics = [].slice.call(d.querySelectorAll('.topic[id]'));
  if (rail && topics.length) {
    var links = {};
    rail.querySelectorAll('li a[href^="#"]').forEach(function (a) { links[a.getAttribute('href').slice(1)] = a.parentNode; });
    var cur = null, raf = 0;
    var spy = function () {
      var line = innerHeight / 3, hit = null;
      topics.forEach(function (t) { if (t.getBoundingClientRect().top < line) hit = t.id; });
      if (hit === cur) return;
      if (cur && links[cur]) { links[cur].classList.remove('is-cur'); links[cur].firstChild.removeAttribute('aria-current'); }
      cur = hit;
      var li = cur && links[cur];
      if (!li) return;
      li.classList.add('is-cur'); li.firstChild.setAttribute('aria-current', 'location');
      var r = li.getBoundingClientRect(), rr = rail.getBoundingClientRect();
      if (r.top < rr.top + 40 || r.bottom > rr.bottom - 40) rail.scrollTop += r.top - rr.top - rr.height / 3;
    };
    addEventListener('scroll', function () { if (!raf) raf = requestAnimationFrame(function () { raf = 0; spy(); }); }, { passive: true });
    spy();
  }
  if (!motion) { html.classList.add('done'); return; }
  html.classList.add('done');
  d.querySelectorAll('.mask-in').forEach(function (el) {
    anim(el, [{ transform: 'translateY(110%)' }, { transform: 'translateY(0)' }], { duration: 1050, delay: 150, easing: E.p3o });
  });
  reveal('[data-reveal],[data-media]', '-10%');
})();
