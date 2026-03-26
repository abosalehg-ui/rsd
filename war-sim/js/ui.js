// ═══════════════════════════════════════
// ui.js — UI Rendering Functions
// ═══════════════════════════════════════

// ── Animate number ──
function animNum(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  const s = parseInt(el.textContent.replace(/[^0-9\-]/g, '')) || 0;
  const diff = target - s, st = Date.now();
  (function tick() {
    const p = Math.min(1, (Date.now() - st) / 800);
    el.textContent = Math.round(s + diff * (1 - Math.pow(1 - p, 3))).toLocaleString();
    if (p < 1) requestAnimationFrame(tick);
  })();
}

// ── Update top stats ──
function renderStats() {
  animNum('sMis', liveData.missiles);
  document.getElementById('sOil').textContent = '$' + liveData.oil;
  document.getElementById('sDead').textContent = liveData.dead_iran.toLocaleString() + '+';
  document.getElementById('sRisk').textContent = liveData.risk + '/10';

  const hEl = document.getElementById('sHorm');
  hEl.textContent = liveData.hormuz;
  hEl.style.color = liveData.hormuz.includes('مغلق') ? '#ef4444' : '#10b981';

  document.getElementById('sLikely').textContent = liveData.likely;
}

// ── Render military gauges ──
function getGaugeVal(idx, day) {
  const g = GAUGE_DEFS[idx];
  const base = liveData[g.key] || 0;
  const elapsed = Math.max(0, day - WAR_DAY);
  const scenarios = getActiveScenarios();
  const sc = scenarios[selectedScenario] || scenarios[0];
  // Decay rates per scenario (faster depletion = higher rate)
  const probFactor = sc ? (100 - sc.prob) / 100 : 0.5;
  const rates = [
    1.0 + probFactor * 0.5,   // missiles
    1.5 + probFactor * 1.0,   // launchers
    0.03 + probFactor * 0.02, // nuclear
    0.015 + probFactor * 0.01,// airdef
    0.06 + probFactor * 0.04, // navy
  ];
  return Math.max(0, Math.round(base - elapsed * rates[idx]));
}

function renderGauges() {
  const box = document.getElementById('gaugeBox');
  if (!box) return;
  document.getElementById('gDay').textContent = 'SIM:D' + simDay;
  let html = '';
  GAUGE_DEFS.forEach((g, i) => {
    const val = getGaugeVal(i, simDay);
    const pct = Math.max(0, Math.min(100, (val / g.max) * 100));
    const danger = pct < 15;
    html += `
      <div class="gauge-wrap">
        <div class="gauge-hd">
          <span>${g.icon} ${g.label}</span>
          <span style="color:${danger ? '#ef4444' : ''};${danger ? 'font-weight:700' : ''}">
            ${Math.round(pct)}%
          </span>
        </div>
        <div class="gauge-trk">
          <div class="gauge-fill" style="
            width:${pct}%;
            background:linear-gradient(90deg, ${g.color}, ${g.color}99);
            box-shadow:0 0 6px ${g.color}40;
          "></div>
        </div>
      </div>`;
  });
  box.innerHTML = html;
}

// ── Get active scenarios (from AI or fallback) ──
function getActiveScenarios() {
  return liveData.scenarios || FALLBACK_SCENARIOS;
}

// ── Render scenario buttons ──
function renderScenarioButtons() {
  const box = document.getElementById('scBtns');
  if (!box) return;
  const scenarios = getActiveScenarios();
  let html = '';

  // Show AI badge if scenarios are from Claude
  const isAI = !!liveData.scenarios;
  if (isAI) {
    html += `<div class="ai-badge">🤖 سيناريوهات مولّدة بالذكاء الاصطناعي بناءً على أحداث اليوم</div>`;
  }

  scenarios.forEach((s, i) => {
    const on = selectedScenario === i;
    html += `
      <button class="sc-btn ${on ? 'sel' : ''}" onclick="selectScenario(${i})"
        style="${on ? 'border-color:' + s.color + '60;background:var(--surface)' : ''}">
        <div style="display:flex;align-items:center;gap:8px">
          <span style="font-size:22px">${s.icon}</span>
          <div>
            <div style="font-size:13px;font-weight:700">${s.name}</div>
            <div class="mono" style="font-size:9px;color:var(--t3)">${s.en}</div>
          </div>
        </div>
        <div class="sc-prob" style="
          background:${s.color}15;border:1px solid ${s.color}35;color:${s.color};
        ">${s.prob}%</div>
      </button>`;
  });
  box.innerHTML = html;
}

// ── Render scenario detail ──
function renderScenarioDetail() {
  const scenarios = getActiveScenarios();
  const s = scenarios[selectedScenario] || scenarios[0];
  if (!s) return;

  const el = document.getElementById('scDetail');
  if (!el) return;
  el.style.background = `linear-gradient(145deg,${s.color}0a,var(--card) 60%)`;
  el.style.border = `1px solid ${s.color}25`;

  let evH = '';
  (s.events || []).forEach((ev, i) => {
    const a = simDay >= ev.d;
    evH += `
      <div class="tl" style="opacity:${a ? 1 : .3}">
        <div class="tl-b" style="background:${a ? s.color : '#1a2744'};color:${a ? '#060e1a' : 'var(--t3)'}">D${ev.d}</div>
        <div class="tl-t" style="color:${a ? 'var(--t1)' : 'var(--t3)'}">${ev.e}</div>
      </div>`;
  });

  el.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <span style="font-size:32px">${s.icon}</span>
      <div>
        <div style="font-size:18px;font-weight:800;color:${s.color}">${s.name}</div>
        <div class="mono" style="font-size:10px;color:var(--t3)">${s.en} · احتمال ${s.prob}%</div>
      </div>
    </div>
    <p style="font-size:13px;color:var(--t2);line-height:1.8;margin-bottom:14px">${s.desc}</p>
    <div class="dm-grid">
      <div class="dm"><div class="dm-l">🛢️ النفط</div><div class="dm-v" style="color:#f59e0b">${s.oil}</div></div>
      <div class="dm"><div class="dm-l">🌊 هرمز</div><div class="dm-v" style="color:#3b82f6">${s.hormuz}</div></div>
      <div class="dm"><div class="dm-l">🏛️ النظام</div><div class="dm-v" style="color:#a855f7">${s.regime}</div></div>
      <div class="dm"><div class="dm-l">☢️ النووي</div><div class="dm-v" style="color:#ef4444">${s.nuke}</div></div>
    </div>
    ${evH ? `<div style="font-size:11px;color:var(--t2);font-weight:700;margin-bottom:8px">📅 الجدول الزمني المتوقع:</div>${evH}` : ''}`;
}

// ── Render analysis card content ──
function renderAnalysis() {
  document.getElementById('aiHeadline').textContent = liveData.headline || '';
  const kd = document.getElementById('aiKeyDev');
  kd.innerHTML = liveData.key_development ? '⚡ ' + liveData.key_development : '';
  document.getElementById('aiMil').textContent = liveData.military || '';
  document.getElementById('aiDip').textContent = liveData.diplomatic || '';
  document.getElementById('aiEco').textContent = liveData.economic || '';
  document.getElementById('lastUpd').textContent = 'آخر تحديث: ' + new Date().toLocaleTimeString('ar-SA');
}

// ── Refresh everything ──
function refreshAllUI() {
  renderStats();
  renderGauges();
  renderScenarioButtons();
  renderScenarioDetail();
  updateSimProjections();
}
