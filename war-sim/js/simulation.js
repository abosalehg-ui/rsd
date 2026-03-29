// ═══════════════════════════════════════
// simulation.js — Sim Controls & Projections
// ═══════════════════════════════════════

function getOilProj(d) {
  const scenarios = getActiveScenarios();
  const sc = scenarios[selectedScenario] || scenarios[0];
  if (!sc) return liveData.oil;
  // Higher prob = more moderate, lower = more extreme
  const direction = sc.prob > 20 ? -0.4 : 0.6;
  const volatility = sc.color === '#EF4444' ? 1.5 : sc.color === '#10B981' ? -0.8 : direction;
  return Math.max(55, Math.min(250, Math.round(liveData.oil + (d - WAR_DAY) * volatility)));
}

function getMisProj(d) {
  const scenarios = getActiveScenarios();
  const sc = scenarios[selectedScenario] || scenarios[0];
  const rate = sc && sc.prob > 30 ? 1.0 : 0.5;
  return Math.max(0, Math.round(liveData.missiles - Math.max(0, d - WAR_DAY) * rate));
}

function getRiskProj(d) {
  const scenarios = getActiveScenarios();
  const sc = scenarios[selectedScenario] || scenarios[0];
  const direction = sc && sc.color === '#EF4444' ? 0.03 : sc && sc.color === '#10B981' ? -0.06 : -0.03;
  return Math.max(1, Math.min(10, +(liveData.risk + (d - WAR_DAY) * direction).toFixed(1)));
}

function updateSimProjections() {
  const simNumEl = document.getElementById('simNum');
  if (simNumEl) simNumEl.textContent = simDay;

  const gDayEl = document.getElementById('gDay');
  if (gDayEl) gDayEl.textContent = 'SIM:D' + simDay;

  const pOil = document.getElementById('pOil');
  if (pOil) pOil.textContent = '$' + getOilProj(simDay);

  const pMis = document.getElementById('pMis');
  if (pMis) pMis.textContent = getMisProj(simDay);

  const pRisk = document.getElementById('pRisk');
  if (pRisk) pRisk.textContent = getRiskProj(simDay);

  renderGauges();
  renderScenarioDetail();
}

function updatePlayBtn(isPlaying) {
  const btn = document.getElementById('playBtn');
  if (!btn) return;
  const scenarios = getActiveScenarios();
  const sc = scenarios[selectedScenario] || { color: '#F59E0B' };
  if (isPlaying) {
    btn.innerHTML = '⏸ إيقاف المحاكاة';
    btn.classList.add('playing');
    btn.style.background = sc.color;
    btn.style.color = '#020408';
    btn.style.borderColor = sc.color;
  } else {
    btn.innerHTML = '▶ تشغيل المحاكاة';
    btn.classList.remove('playing');
    btn.style.background = 'rgba(' + hexToRgb(sc.color) + ', 0.1)';
    btn.style.color = sc.color;
    btn.style.borderColor = sc.color;
  }
}

function hexToRgb(hex) {
  try {
    if (!hex || typeof hex !== 'string' || !hex.startsWith('#')) return '245,158,11';
    const r = parseInt(hex.slice(1,3),16);
    const g = parseInt(hex.slice(3,5),16);
    const b = parseInt(hex.slice(5,7),16);
    if (isNaN(r) || isNaN(g) || isNaN(b)) return '245,158,11';
    return r+','+g+','+b;
  } catch { return '245,158,11'; }
}

function selectScenario(i) {
  selectedScenario = i;
  simDay = WAR_DAY;
  playing = false;
  clearInterval(playInt);
  const slider = document.getElementById('simSlider');
  if (slider) slider.value = WAR_DAY;
  updatePlayBtn(false);
  renderScenarioButtons();
  renderScenarioDetail();
  renderGauges();
  updateSimProjections();
}

function togglePlay() {
  try {
    if (playing) {
      playing = false;
      clearInterval(playInt);
      updatePlayBtn(false);
    } else {
      playing = true;
      updatePlayBtn(true);
      playInt = setInterval(() => {
        simDay++;
        if (simDay > 200) {
          simDay = 200;
          playing = false;
          clearInterval(playInt);
          updatePlayBtn(false);
        }
        const slider = document.getElementById('simSlider');
        if (slider) slider.value = simDay;
        updateSimProjections();
      }, 150);
    }
  } catch(e) { console.error('togglePlay error:', e); }
}

function resetSim() {
  playing = false;
  clearInterval(playInt);
  simDay = WAR_DAY;
  const slider = document.getElementById('simSlider');
  if (slider) slider.value = WAR_DAY;
  updatePlayBtn(false);
  updateSimProjections();
}
