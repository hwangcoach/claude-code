/* 화면 편집기(serve.py 로 띄웠을 때만 들어감). 블록의 data-src="파일:시작-끝" 으로 원고 마크다운을 찾아 고친다.
   본문·근거·홈: 블록을 누르면 편집 창. 덱: E 키(또는 편집 막대의 「이 장 편집」).
   저장 Ctrl/Cmd+Enter · 닫기 Esc · 편집 끄기/켜기(막대) · 되돌리기(막대) */
(function () {
  'use strict';
  var d = document, isDeck = !!d.getElementById('stage');
  var API = '/__edit/';
  var on = true;
  try { on = sessionStorage.getItem('ed-off') !== '1'; } catch (e) { /* 저장소 없음 */ }

  var css = '' +
    '.ed-on [data-src]{cursor:text;transition:outline-color .2s}' +
    '.ed-on [data-src]:hover{outline:1.5px dashed #828fff;outline-offset:6px;border-radius:4px}' +
    '.ed-sel{outline:2px solid #828fff!important;outline-offset:6px;border-radius:4px}' +
    '#ed-bar{position:fixed;left:14px;bottom:14px;z-index:9999;display:flex;gap:6px;align-items:center;flex-wrap:wrap;max-width:calc(100vw - 28px);' +
    'background:#141516;border:1px solid #34343a;border-radius:10px;padding:6px 8px;font:500 13px/1.3 Pretendard,system-ui,sans-serif;color:#d0d6e0;box-shadow:0 10px 30px rgba(0,0,0,.5)}' +
    '#ed-bar b{color:#f7f8f8;font-weight:600;margin-right:4px}' +
    '.ed-btn{font:inherit;color:#f7f8f8;background:#23252a;border:1px solid #34343a;border-radius:7px;padding:5px 10px;cursor:pointer}' +
    '.ed-btn:hover{background:#34343a}.ed-btn.pri{background:#5e6ad2;border-color:#5e6ad2}.ed-btn.pri:hover{background:#828fff}' +
    '.ed-btn.warn{color:#ffb38a}.ed-btn:disabled{opacity:.4;cursor:default}' +
    '#ed-warn{color:#ffb38a;cursor:pointer}' +
    '#ed-panel{position:fixed;top:0;right:0;bottom:0;width:min(560px,100vw);z-index:10000;background:#0f1011;border-left:1px solid #34343a;' +
    'display:flex;flex-direction:column;font:400 14px/1.5 Pretendard,system-ui,sans-serif;color:#d0d6e0;box-shadow:-20px 0 60px rgba(0,0,0,.6)}' +
    '#ed-panel header{padding:14px 16px 10px;border-bottom:1px solid #23252a}' +
    '#ed-panel h3{margin:0;font-size:15px;font-weight:600;color:#f7f8f8}#ed-panel .ed-loc{margin-top:2px;color:#8a8f98;font-size:12px}' +
    '#ed-panel textarea{flex:1;margin:12px 16px;resize:none;background:#010102;color:#f7f8f8;border:1px solid #34343a;border-radius:8px;padding:12px;' +
    'font:14px/1.65 D2Coding,ui-monospace,Menlo,monospace;white-space:pre-wrap;outline:none}#ed-panel textarea:focus{border-color:#5e6ad2}' +
    '#ed-panel .ed-row{display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding:0 16px 10px}' +
    '#ed-panel .ed-row span{color:#8a8f98;font-size:12px;margin-right:2px}' +
    '#ed-panel .ed-msg{padding:0 16px 12px;font-size:13px;min-height:18px}.ed-msg.err{color:#ff9b8a}.ed-msg.ok{color:#9fd8b0}' +
    '#ed-panel .ed-help{padding:0 16px 14px;color:#62666d;font-size:12px}' +
    '#ed-warns{position:fixed;left:14px;bottom:62px;z-index:9999;max-width:min(640px,calc(100vw - 28px));max-height:40vh;overflow:auto;background:#141516;' +
    'border:1px solid #34343a;border-radius:10px;padding:10px 14px;font:13px/1.55 Pretendard,system-ui,sans-serif;color:#ffb38a}#ed-warns li{margin:2px 0 2px 16px}';
  var st = d.createElement('style'); st.textContent = css; d.head.appendChild(st);

  // ---- 편집 막대 ----
  var bar = d.createElement('div'); bar.id = 'ed-bar';
  bar.innerHTML = '<b>편집 모드</b><button class="ed-btn" data-a="toggle"></button>' +
    (isDeck ? '<button class="ed-btn" data-a="slide">이 장 편집 (E)</button>' : '') +
    '<button class="ed-btn" data-a="undo">되돌리기</button><span id="ed-warn"></span>';
  d.body.appendChild(bar);
  var warnBox = null;
  function setOn(v) {
    on = v; d.documentElement.classList.toggle('ed-on', on);
    bar.querySelector('[data-a="toggle"]').textContent = on ? '편집 끄기(읽기만)' : '편집 켜기';
    try { sessionStorage.setItem('ed-off', on ? '0' : '1'); } catch (e) { /* 무시 */ }
  }
  setOn(on);
  bar.addEventListener('click', function (e) {
    var a = e.target.getAttribute('data-a');
    if (a === 'toggle') setOn(!on);
    if (a === 'slide') openSlide();
    if (a === 'undo') post('undo', {}).then(function (r) { if (r.ok) reload(); else alert(r.error); });
  });
  function showWarn(list, err) {
    var w = d.getElementById('ed-warn');
    var n = (list || []).length + (err ? 1 : 0);
    w.textContent = err ? '빌드 오류 · 눌러서 보기' : (n ? '확인할 것 ' + n + '건' : '확인할 것 없음');
    w.style.color = n ? '#ffb38a' : '#9fd8b0';
    w.onclick = function () {
      if (warnBox) { warnBox.remove(); warnBox = null; return; }
      warnBox = d.createElement('div'); warnBox.id = 'ed-warns';
      warnBox.innerHTML = (err ? '<pre style="white-space:pre-wrap;margin:0 0 8px">' + esc(err) + '</pre>' : '') +
        '<ul style="margin:0;padding:0">' + (list || []).map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>';
      d.body.appendChild(warnBox);
    };
  }
  function esc(s) { return String(s).replace(/[&<>]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; }); }

  // ---- 서버 ----
  function post(path, body) {
    return fetch(API + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (r) { return r.json().then(function (j) { if (!r.ok) j.ok = false; return j; }); })
      .catch(function () { return { ok: false, error: '편집 서버에 닿지 않습니다(serve 가 꺼졌나요?)' }; });
  }
  function reload() {
    try { sessionStorage.setItem('ed-scroll', String(scrollY)); } catch (e) { /* 무시 */ }
    location.reload();
  }
  try { var y = sessionStorage.getItem('ed-scroll'); if (y) { sessionStorage.removeItem('ed-scroll'); addEventListener('load', function () { scrollTo(0, +y); }); } } catch (e) { /* 무시 */ }

  // ---- 원고 바뀜 감시(Obsidian 에서 고쳐도 따라옴) ----
  var vm = d.querySelector('meta[name="ed-v"]'), V = vm ? +vm.content : null, dirty = false;
  function poll() {
    fetch(API + 'version', { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (j) {
      if (V === null) V = j.v; else if (j.v !== V && !dirty) return reload();
      showWarn(j.warn, j.err);
    }).catch(function () { var w = d.getElementById('ed-warn'); w.textContent = '편집 서버 꺼짐'; w.style.color = '#ff9b8a'; })
      .then(function () { setTimeout(poll, 1500); });
  }
  poll();

  // ---- 편집 창 ----
  var panel = null, cur = null;
  function parse(v) { var m = /^(.*):(\d+)-(\d+)$/.exec(v || ''); return m ? { f: m[1], a: +m[2], b: +m[3] } : null; }
  function kindOf(el, s) {
    if (s.f === 'deck.md') return '슬라이드';
    if (s.f === 'sources.md') return '근거';
    if (s.f === 'lecture.md') return '강의 정보(머리말)';
    if (el.classList.contains('doc-head')) return '장 정보(머리말)';
    if (el.tagName === 'H2') return '꼭지 제목';
    if (el.tagName === 'H3') return '소제목';
    if (el.tagName === 'FIGURE') return '그림';
    if (el.tagName === 'DETAILS') return '조건과 한계';
    if (el.tagName === 'UL' || el.tagName === 'OL') return '목록';
    if (el.tagName === 'ASIDE') return '상자';
    return '문단';
  }
  function uid(el) {
    var t = el.closest('[id]'); var base = t && /^[a-z]+-\d+/.test(t.id) ? t.id.match(/^[a-z]+-\d+/)[0] : 'new';
    return base + '-' + Date.now().toString(36).slice(-4);
  }
  function today() { var t = new Date(); return t.getFullYear() + '-' + String(t.getMonth() + 1).padStart(2, '0') + '-' + String(t.getDate()).padStart(2, '0'); }
  function templates(el, s) {
    if (s.f === 'deck.md') return [['새 슬라이드', '## 새 슬라이드 제목 {kind=statement}\n\n> 화면에 보일 한 줄\n\n발표 스크립트를 구어체로 씁니다.\n', 'section']];
    if (s.f === 'sources.md') return [['새 근거', '### X-' + Date.now().toString().slice(-4) + '\n- 주장: \n- 종류: 공식\n- 출처: \n- 확인: ' + today() + '\n', 'section']];
    if (s.f === 'lecture.md' || el.classList.contains('doc-head')) return [];
    return [['문단', '새 문단을 씁니다.'], ['소제목', '### 새 소제목'],
      ['그림', '```fig ' + uid(el) + '\ntype: bars\n- 항목 A | 3\n- 항목 B | 5 | hl\ncaption: 그림이 말하는 것 한 문장\n```'],
      ['삽화', '```fig ' + uid(el) + '-i\ntype: illust\nprompt: (장면을 영어로 묘사)\ncaption: 삽화 설명 한 문장\n```'],
      ['조건과 한계', ':::cond 조건과 한계\n- 잰 환경, 횟수, 확인하지 못한 것\n:::'],
      ['새 꼭지', '## 새 꼭지 제목(주장 문장)\n\n설명 문단을 씁니다.', 'topic']];
  }
  function close() {
    if (dirty && !confirm('저장하지 않은 내용이 있습니다. 닫을까요?')) return;
    if (panel) panel.remove(); panel = null; dirty = false;
    if (cur) cur.el.classList.remove('ed-sel'); cur = null;
  }
  function open(el) {
    var s = parse(el.getAttribute('data-src')); if (!s) return;
    if (panel) { if (dirty && !confirm('저장하지 않은 내용이 있습니다. 다른 블록을 열까요?')) return; panel.remove(); if (cur) cur.el.classList.remove('ed-sel'); }
    dirty = false;
    var art = el.tagName === 'H2' && el.closest('[data-sec]');
    var sec = art ? parse(art.getAttribute('data-sec')) : null;
    var unit = (s.f === 'deck.md' || s.f === 'sources.md') ? 'section' : 'block';
    var meta = s.f === 'lecture.md' || el.classList.contains('doc-head');
    cur = { el: el, s: s, sec: sec, unit: unit, orig: '' };
    el.classList.add('ed-sel');
    panel = d.createElement('div'); panel.id = 'ed-panel';
    var tpl = templates(el, s);
    panel.innerHTML = '<header><h3>' + kindOf(el, s) + ' 고치기</h3><div class="ed-loc">' + esc(s.f) + ' · ' + (s.a + 1) + '–' + s.b + '줄</div></header>' +
      '<textarea spellcheck="false" aria-label="원고 마크다운"></textarea>' +
      '<div class="ed-row"><button class="ed-btn pri" data-a="save">저장 (⌘/Ctrl+Enter)</button>' +
      (meta ? '' : '<button class="ed-btn warn" data-a="delete">삭제</button><button class="ed-btn" data-a="up">위로</button><button class="ed-btn" data-a="down">아래로</button>') +
      '<button class="ed-btn" data-a="close">닫기 (Esc)</button></div>' +
      (sec ? '<div class="ed-row"><span>꼭지 전체</span><button class="ed-btn warn" data-a="sdel">꼭지 삭제</button><button class="ed-btn" data-a="sup">꼭지 위로</button><button class="ed-btn" data-a="sdown">꼭지 아래로</button></div>' : '') +
      (tpl.length ? '<div class="ed-row"><span>아래에 추가</span>' + tpl.map(function (t, i) { return '<button class="ed-btn" data-t="' + i + '">' + t[0] + '</button>'; }).join('') + '</div>' : '') +
      '<div class="ed-msg"></div>' +
      '<div class="ed-help">원고 마크다운을 그대로 고칩니다. 근거는 [^F-1001], 강조는 **굵게**. 그림 형식: stat · bars · stack · sankey · compare · flow · timeline · list · table · terminal · statement · image · illust</div>';
    d.body.appendChild(panel);
    var ta = panel.querySelector('textarea'), msg = panel.querySelector('.ed-msg');
    ta.value = '불러오는 중…'; ta.disabled = true;
    fetch(API + 'src?f=' + encodeURIComponent(s.f) + '&a=' + s.a + '&b=' + s.b, { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (j) {
      if (j.error) { msg.className = 'ed-msg err'; msg.textContent = j.error; return; }
      cur.orig = j.text; ta.value = j.text; ta.disabled = false; ta.focus();
    });
    ta.addEventListener('input', function () { dirty = ta.value !== cur.orig; });
    function run(op, extra, confirmMsg) {
      if (confirmMsg && !confirm(confirmMsg)) return;
      msg.className = 'ed-msg'; msg.textContent = '저장하고 다시 만드는 중…';
      var body = Object.assign({ op: op, f: s.f, a: s.a, b: s.b, orig: cur.orig }, extra || {});
      post('op', body).then(function (r) {
        if (!r.ok) { msg.className = 'ed-msg err'; msg.textContent = r.error || '실패'; return; }
        dirty = false; reload();
      });
    }
    panel.addEventListener('click', function (e) {
      var a = e.target.getAttribute('data-a'), t = e.target.getAttribute('data-t');
      if (a === 'save') run('replace', { text: ta.value });
      if (a === 'delete') run('delete', null, '이 ' + kindOf(el, s) + '을(를) 원고에서 지울까요? (되돌리기로 살릴 수 있음)');
      if (a === 'up' || a === 'down') run('move', { dir: a, unit: unit });
      if (a === 'close') close();
      if (sec && (a === 'sdel' || a === 'sup' || a === 'sdown')) {
        var body = { f: sec.f, a: sec.a, b: sec.b, orig: undefined };
        if (a === 'sdel') { if (!confirm('이 꼭지 전체(제목부터 다음 꼭지 전까지)를 지울까요?')) return; post('op', Object.assign({ op: 'delete' }, body)).then(done); }
        else post('op', Object.assign({ op: 'move', unit: 'section', dir: a === 'sup' ? 'up' : 'down' }, body)).then(done);
      }
      if (t !== null) {
        var tp = tpl[+t], at = s.b;
        if (tp[2] === 'topic') { var ar = el.closest('[data-sec]'); if (ar) at = parse(ar.getAttribute('data-sec')).b; }
        post('op', { op: 'insert', f: s.f, a: at, b: at, text: tp[1] + '\n' }).then(done);
      }
      function done(r) { if (!r.ok) { msg.className = 'ed-msg err'; msg.textContent = r.error || '실패'; return; } dirty = false; reload(); }
    });
    ta.addEventListener('keydown', function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); run('replace', { text: ta.value }); }
    });
  }
  function openSlide() { var sl = d.querySelector('.slide.on[data-src]'); if (sl) open(sl); else alert('이 장은 deck.md 에서 온 것이 아니라 고칠 수 없습니다(draft-deck 으로 deck.md 를 먼저 만드세요).'); }

  // 화면 클릭 → 편집 창(덱 제외: 덱은 클릭이 「다음 장」)
  d.addEventListener('click', function (e) {
    if (!on || isDeck) return;
    if (e.target.closest('#ed-panel,#ed-bar,#ed-warns,.nav,.rail,.toc-m,.pn,.chview,.flip-go')) return;
    var el = e.target.closest('[data-src]'); if (!el) return;
    if (el.tagName === 'DETAILS' && e.target.closest('summary') && !e.altKey) { /* 접는 칸 열기는 그대로, Alt+클릭이면 편집 */ return; }
    e.preventDefault(); e.stopPropagation(); open(el);
  }, true);
  // 편집 창에서 치는 키는 덱 단축키로 가지 않게(문서 capture 단계에서 막음)
  d.addEventListener('keydown', function (e) {
    var inPanel = panel && panel.contains(e.target);
    if (e.key === 'Escape' && panel) { e.preventDefault(); e.stopPropagation(); close(); return; }
    if (inPanel) { e.stopPropagation(); return; }
    if (isDeck && on && (e.key === 'e' || e.key === 'E') && !e.metaKey && !e.ctrlKey && !e.altKey) { e.preventDefault(); e.stopPropagation(); openSlide(); }
  }, true);
  addEventListener('beforeunload', function (e) { if (dirty) { e.preventDefault(); e.returnValue = ''; } });
})();
