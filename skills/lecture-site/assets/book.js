/* 책으로 보기: <template id="bk-src"> 의 원고를 A5(148×210mm) 쪽으로 나누고 가로로 넘겨 봄.
   원본은 인쇄 PDF 를 쪽 JPG 로 잘라 넣었지만, 여기서는 브라우저가 직접 조판함 → 인쇄(Ctrl/Cmd+P)하면 그대로 A5 PDF.
   - 장은 새 쪽에서 시작, 제목이 쪽 끝에 홀로 남지 않게 다음 쪽으로 데려감, 긴 문단은 낱말 단위로 나눔
   - 표지 · 차례(쪽 번호 자동) · 판권
   - 권 첫머리는 표지·차례·판권을, 장 쪽은 그 장의 쪽만 보여 줌. 인쇄할 때는 권 첫머리=권 전체, 장 쪽=그 장 */
(function () {
  'use strict';
  var d = document, tpl = d.getElementById('bk-src'), dataEl = d.getElementById('bk-data');
  if (!tpl || !dataEl) return;
  var data = JSON.parse(dataEl.textContent);
  var flip = d.querySelector('.flip'), info = d.querySelector('.flip-n'), go = d.querySelector('.flip-go');
  var cssLink = d.querySelector('link[href$="book.css"]');
  var assets = cssLink ? cssLink.getAttribute('href').replace(/book\.css$/, '') : '';
  var measure = d.createElement('div'); measure.id = 'bk-measure'; d.body.appendChild(measure);
  var pages = [];

  function el(tag, cls, html) { var e = d.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function newPage(kind, ch) {
    var pg = el('div', 'pg ' + (kind || '')), body = el('div', 'pg-body');
    pg.appendChild(body); measure.appendChild(pg);
    var p = { pg: pg, body: body, ch: ch || '', kind: kind || 'text' };
    pages.push(p); return p;
  }
  function fits(body) { return body.scrollHeight <= body.clientHeight + 1; }
  function isHead(e) { return e && /^(H1|H2|H3|H4)$/.test(e.tagName) || (e && e.classList && (e.classList.contains('b-kick') || e.classList.contains('sub'))); }

  // 문단을 낱말(글 마디)과 꾸밈 요소 단위로 쪼갬
  function tokens(p) {
    var out = [];
    [].forEach.call(p.childNodes, function (n) {
      if (n.nodeType === 3) n.textContent.split(/(\s+)/).forEach(function (t) { if (t) out.push(d.createTextNode(t)); });
      else out.push(n.cloneNode(true));
    });
    return out;
  }
  function splitPara(p, body) {
    var tk = tokens(p), lo = 0, hi = tk.length, best = 0;
    var probe = p.cloneNode(false); body.appendChild(probe);
    while (lo <= hi) {
      var mid = (lo + hi) >> 1; probe.innerHTML = '';
      for (var i = 0; i < mid; i++) probe.appendChild(tk[i].cloneNode(true));
      if (fits(body)) { best = mid; lo = mid + 1; } else hi = mid - 1;
    }
    body.removeChild(probe);
    if (best < 3) return null;                      // 두어 낱말만 남기지 않음
    var a = p.cloneNode(false), b = p.cloneNode(false); b.classList.add('cont');
    tk.forEach(function (t, i) { (i < best ? a : b).appendChild(t); });
    return [a, b];
  }

  function paginate(section) {
    var ch = section.getAttribute('data-ch');
    var cur = newPage('text', ch);
    cur.title = section.getAttribute('data-title');
    var queue = [].slice.call(section.children).map(function (n) { return n.cloneNode(true); });
    while (queue.length) {
      var b = queue.shift();
      if (b.classList && (b.classList.contains('prose') || b.classList.contains('box'))) { queue = [].slice.call(b.children).concat(queue); continue; } // 문단 묶음은 풀어서 문단 단위로
      cur.body.appendChild(b);
      if (fits(cur.body)) continue;
      cur.body.removeChild(b);
      // 목록은 항목 단위로
      if ((b.tagName === 'UL' || b.tagName === 'OL') && b.children.length > 1) {
        var first = b.cloneNode(false), rest = b.cloneNode(true);
        cur.body.appendChild(first);
        while (rest.children.length) { first.appendChild(rest.children[0]); if (!fits(cur.body)) { rest.insertBefore(first.lastChild, rest.firstChild); break; } }
        if (!first.children.length) cur.body.removeChild(first);
        if (rest.children.length) queue.unshift(rest);
        cur = newPage('text', ch); cur.title = section.getAttribute('data-title');
        continue;
      }
      if (b.tagName === 'P') {
        var parts = splitPara(b, cur.body);
        if (parts) { cur.body.appendChild(parts[0]); queue.unshift(parts[1]); cur = newPage('text', ch); cur.title = section.getAttribute('data-title'); continue; }
      }
      // 쪽 끝의 제목은 다음 쪽으로 데려감
      var carry = [];
      while (cur.body.lastElementChild && isHead(cur.body.lastElementChild) && cur.body.children.length > 1) carry.unshift(cur.body.removeChild(cur.body.lastElementChild));
      var empty = !cur.body.children.length;
      if (!empty) { cur = newPage('text', ch); cur.title = section.getAttribute('data-title'); }
      carry.forEach(function (c) { cur.body.appendChild(c); });
      cur.body.appendChild(b);
      if (!fits(cur.body)) {
        var svg = b.querySelector && b.querySelector('svg');
        if (svg) { // 그림이 한 쪽보다 크면 남은 높이에 맞춤
          var room = cur.body.clientHeight - (cur.body.scrollHeight - b.offsetHeight) - 24;
          svg.style.maxHeight = Math.max(room, 120) + 'px'; svg.style.width = 'auto'; svg.style.margin = '0 auto';
        } else if (b.tagName === 'P') {
          cur.body.removeChild(b);
          var pp = splitPara(b, cur.body);
          if (pp) { cur.body.appendChild(pp[0]); queue.unshift(pp[1]); cur = newPage('text', ch); cur.title = section.getAttribute('data-title'); }
          else cur.body.appendChild(b);
        }
      }
    }
  }

  function build() {
    var src = tpl.content;
    // 표지
    var cv = newPage('cover-pg'); cv.pg.removeChild(cv.body);
    var img = el('img'); img.src = assets + 'cover-' + data.vol + '.svg'; img.alt = data.vol + '권 표지'; cv.pg.appendChild(img);
    // 차례(쪽 번호는 나중에)
    var tc = newPage('toc-pg');
    tc.body.appendChild(el('p', 'toc-h', '차례'));
    var tl = el('ol', 'toc-l'); tc.body.appendChild(tl);
    [].forEach.call(src.querySelectorAll('section[data-ch]'), function (s) { paginate(s); });
    // 판권
    var co = newPage('colo-pg');
    co.pg.appendChild(el('div', 'colophon', '<strong>' + esc(data.lecture) + ' ' + data.vol + '권</strong>' + esc(data.title) +
      (data.author ? '<br>지은이 ' + esc(data.author) : '') + (data.date ? '<br>펴낸 날 ' + esc(data.date) : '') +
      '<br>이 책은 강의 원고에서 자동으로 조판했습니다.'));
    // 쪽 번호: 본문 첫 쪽이 1
    var n = 0, starts = {};
    pages.forEach(function (p) {
      if (p.kind === 'text') {
        n++; p.n = n; if (!starts[p.ch]) starts[p.ch] = n;
        p.pg.classList.add(n % 2 ? 'odd' : 'even');
        p.pg.appendChild(el('div', 'pg-run', '<span>' + esc(n % 2 ? p.title : data.lecture) + '</span><span>' + data.vol + '권</span>'));
        p.pg.appendChild(el('div', 'pg-num', String(n)));
      }
    });
    data.chapters.forEach(function (c) {
      tl.appendChild(el('li', '', '<span class="n">' + c.n + '장</span><span>' + esc(c.title) + '</span><span class="p">' + (starts[c.id] || '') + '</span>'));
    });
    render();
  }
  function esc(s) { return String(s || '').replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function shown(p) { return data.only ? p.ch === data.only : p.kind !== 'text'; }
  function label(p) { return p.kind === 'cover-pg' ? '표지' : p.kind === 'toc-pg' ? '차례' : p.kind === 'colo-pg' ? '판권' : String(p.n); }

  function render() {
    flip.innerHTML = '';
    pages.forEach(function (p) {
      var li = el('li'), w = el('div', 'pg-wrap');
      li.setAttribute('data-n', label(p));
      if (!shown(p)) li.hidden = true;
      w.appendChild(p.pg); li.appendChild(w); li.appendChild(el('span', 'pn-l', label(p) + (p.kind === 'text' ? '쪽' : '')));
      flip.appendChild(li); p.li = li;
    });
    measure.remove();
    scale(); show();
  }
  function scale() {
    pages.forEach(function (p) { if (!p.li || p.li.hidden) return; var k = p.li.clientWidth / p.pg.offsetWidth; p.pg.style.transform = 'scale(' + k + ')'; });
  }
  function vis() { return [].slice.call(flip.children).filter(function (li) { return !li.hidden; }); }
  function stepW() { var v = vis(); if (!v.length) return 1; return v[0].getBoundingClientRect().width + (parseFloat(getComputedStyle(flip).columnGap) || 28); }
  function at() { return Math.round(flip.scrollLeft / stepW()); }
  function per() { return Math.max(1, Math.round((flip.clientWidth + 28) / stepW() - 0.15)); }
  function show() {
    var v = vis(), i = Math.min(at(), v.length - 1), last = Math.min(v.length, i + per());
    if (!v.length) { info.textContent = '쪽이 없습니다'; return; }
    var s = v[i].getAttribute('data-n'), e = v[last - 1].getAttribute('data-n');
    var numeric = /^\d+$/.test(s) && /^\d+$/.test(e);
    var total = pages.filter(function (p) { return p.kind === 'text'; }).length;
    var all = data.only ? '이 장 ' + v.length + '쪽' : '권 전체 ' + total + '쪽(인쇄하면 모두 나옴)';
    var here = numeric ? (last > i + 1 ? s + '-' + e + '쪽' : s + '쪽')
                       : v.slice(i, last).map(function (li) { return li.getAttribute('data-n'); }).join(' · ');
    info.textContent = here + ' / ' + all;
    var b = go.querySelectorAll('button'); b[0].disabled = i <= 0; b[1].disabled = last >= v.length;
  }
  function move(dir) { var i = Math.max(0, at() + dir * per()); flip.scrollTo({ left: i * stepW(), behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }); }
  go.querySelectorAll('button').forEach(function (b) { b.addEventListener('click', function () { move(+b.getAttribute('data-go')); }); });
  flip.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight' || e.key === 'PageDown') { e.preventDefault(); move(1); }
    if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); move(-1); }
  });
  var t; flip.addEventListener('scroll', function () { clearTimeout(t); t = setTimeout(show, 80); });
  addEventListener('resize', function () { scale(); show(); });
  // 인쇄: 권 첫머리 = 권 전체, 장 쪽 = 그 장
  var hid = [];
  addEventListener('beforeprint', function () { if (!data.only) { hid = vis().length ? [].slice.call(flip.children).filter(function (li) { return li.hidden; }) : []; hid.forEach(function (li) { li.hidden = false; }); } });
  addEventListener('afterprint', function () { hid.forEach(function (li) { li.hidden = true; }); hid = []; scale(); });
  d.querySelectorAll('[data-print]').forEach(function (b) { b.addEventListener('click', function () { window.print(); }); });
  (d.fonts && d.fonts.ready ? d.fonts.ready : Promise.resolve()).then(build);
})();
