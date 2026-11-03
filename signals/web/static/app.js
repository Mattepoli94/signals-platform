/* Signals: saves edits either to the local server (python -m signals serve) or, on the hosted
   site, to your GitHub repository via its API (a workflow then rebuilds the site). */
(function () {
  'use strict';
  var root = document.body.getAttribute('data-root') || '';
  var KEY = 'signals.gh';
  var mode = null; // 'local' | 'github'

  function toast(msg, ms) {
    var t = document.getElementById('toast');
    t.textContent = msg; t.style.display = 'block';
    clearTimeout(t._h); t._h = setTimeout(function () { t.style.display = 'none'; }, ms || 5000);
  }
  function gh() {
    var v = {};
    try { v = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { v = {}; }
    if (!v.owner || !v.repo) {
      var m = location.hostname.match(/^([^.]+)\.github\.io$/);
      if (m) { v.owner = v.owner || m[1]; v.repo = v.repo || (location.pathname.split('/')[1] || ''); }
    }
    return v;
  }
  function saveGh(v) { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) { toast('This browser blocks local storage; the token cannot be remembered.'); } }

  function detect() {
    return fetch(root + 'api/ping', { cache: 'no-store' }).then(function (r) {
      mode = r.ok ? 'local' : 'github';
    }).catch(function () { mode = 'github'; });
  }

  function ghApi(path, method, body) {
    var c = gh();
    if (!c.token || !c.owner || !c.repo) {
      return Promise.reject(new Error('Connect GitHub first: Settings → How edits are saved.'));
    }
    return fetch('https://api.github.com/repos/' + c.owner + '/' + c.repo + path, {
      method: method || 'GET',
      headers: { 'Authorization': 'Bearer ' + c.token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' },
      body: body ? JSON.stringify(body) : undefined
    }).then(function (r) {
      if (r.status === 204 || r.status === 201 || r.status === 200) { return r.status === 204 ? {} : r.json(); }
      return r.text().then(function (t) { throw new Error('GitHub ' + r.status + ': ' + t.slice(0, 160)); });
    });
  }
  function dispatch(workflow, inputs) {
    return ghApi('/actions/workflows/' + workflow + '/dispatches', 'POST', { ref: 'main', inputs: inputs || {} });
  }
  function local(path, body) {
    return fetch(root + 'api/' + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) })
      .then(function (r) { return r.json().then(function (j) { if (!r.ok || j.ok === false) { throw new Error(j.error || ('HTTP ' + r.status)); } return j; }); });
  }

  function apply(op) {
    if (mode === 'local') {
      return local('op', op).then(function (j) { toast((j.message || 'Saved') + '. Reloading…'); setTimeout(function () { location.reload(); }, 900); });
    }
    return dispatch('manage.yml', { op: JSON.stringify(op) }).then(function () {
      toast('Saved to GitHub. The site rebuilds in about 2 minutes; refresh the page then.', 9000);
    });
  }

  function formData(form) {
    var o = { op: form.getAttribute('data-op') };
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name) { return; }
      if (el.type === 'checkbox') { o[el.name] = el.checked; } else if (el.value !== '') { o[el.name] = el.value; }
    });
    return o;
  }
  function busy(btn, on) { if (btn) { btn.disabled = on; } }

  document.addEventListener('submit', function (ev) {
    var form = ev.target;
    if (form.id === 'ghform') {
      ev.preventDefault();
      saveGh({ owner: form.owner.value.trim(), repo: form.repo.value.trim(), token: form.token.value.trim() });
      ghState(); toast('GitHub connection saved in this browser.');
      return;
    }
    if (form.id === 'upload') { ev.preventDefault(); upload(form); return; }
    if (!form.hasAttribute('data-op')) { return; }
    ev.preventDefault();
    var msg = form.getAttribute('data-confirm');
    if (msg && !window.confirm(msg)) { return; }
    var btn = form.querySelector('button[type=submit]');
    busy(btn, true);
    apply(formData(form)).catch(function (e) { toast(e.message, 9000); }).then(function () { busy(btn, false); });
  });

  document.addEventListener('click', function (ev) {
    var b = ev.target.closest('[data-action=refresh]');
    if (!b) { return; }
    busy(b, true); toast('Downloading the latest data…', 20000);
    var p = mode === 'local'
      ? local('refresh').then(function (j) { toast(j.message || 'Data refreshed. Reloading…'); setTimeout(function () { location.reload(); }, 900); })
      : dispatch('daily.yml', { mode: 'close' }).then(function () { toast('Refresh started on GitHub. New data in about 2–3 minutes.', 9000); });
    p.catch(function (e) { toast(e.message, 9000); }).then(function () { busy(b, false); });
  });

  function upload(form) {
    var f = form.file.files[0], asset = form.asset.value;
    if (!f) { return; }
    var btn = form.querySelector('button[type=submit]'); busy(btn, true);
    f.text().then(function (text) {
      if (mode === 'local') {
        return local('upload', { asset: asset, text: text }).then(function (j) { toast(j.message + '. Reloading…'); setTimeout(function () { location.reload(); }, 1200); });
      }
      var path = '/contents/data/uploads/' + asset + '.csv';
      var b64 = btoa(unescape(encodeURIComponent(text)));
      return ghApi(path).then(function (j) { return j.sha; }).catch(function () { return undefined; }).then(function (sha) {
        var body = { message: 'Upload ' + asset + ' prices', content: b64, branch: 'main' };
        if (sha) { body.sha = sha; }
        return ghApi(path, 'PUT', body);
      }).then(function () { return dispatch('manage.yml', { op: JSON.stringify({ op: 'import' }) }); })
        .then(function () { toast('Uploaded. The site rebuilds in about 2 minutes.', 9000); });
    }).catch(function (e) { toast(e.message, 9000); }).then(function () { busy(btn, false); });
  }

  function ghState() {
    var el = document.getElementById('gh-state'); if (!el) { return; }
    var c = gh();
    document.getElementById('gh-owner').value = c.owner || '';
    document.getElementById('gh-repo').value = c.repo || '';
    el.textContent = c.token ? 'Connected as ' + c.owner + '/' + c.repo + ' (token saved in this browser).' : 'Not connected: edits cannot be saved from this browser yet.';
  }

  detect().then(function () {
    var l = document.getElementById('mode-local'), g = document.getElementById('mode-gh');
    if (l && g) { (mode === 'local' ? l : g).style.display = 'block'; }
    var clr = document.getElementById('gh-clear');
    if (clr) { clr.addEventListener('click', function () { var c = gh(); delete c.token; saveGh(c); ghState(); toast('Token removed from this browser.'); }); }
    ghState();
  });
})();
