// ═══════════════════════════════════════
// app.js — Main Application
// ═══════════════════════════════════════

// Global state
let liveData = { ...DEFAULT_DATA };
let selectedScenario = 0;
let simDay = WAR_DAY;
let playing = false;
let playInt = null;

// ── Initialize ──
function init() {
  document.getElementById('dayLabel').textContent = 'DAY ' + WAR_DAY;
  document.getElementById('todayDate').textContent = TODAY.toLocaleDateString('ar-SA');

  // Slider setup
  const slider = document.getElementById('simSlider');
  slider.min = WAR_DAY;
  slider.max = 200;
  slider.value = WAR_DAY;
  slider.addEventListener('input', function () {
    simDay = parseInt(this.value);
    playing = false;
    clearInterval(playInt);
    updatePlayBtn(false);
    updateSimProjections();
  });

  // Check saved API key
  if (hasApiKey()) {
    document.getElementById('keySection').style.display = 'none';
    document.getElementById('analysisCard').style.display = 'block';
    document.getElementById('apiIndicator').innerHTML = '<span class="api-on">Claude</span>';
    document.getElementById('discBtn').style.display = 'inline-block';
    fetchAnalysis();
  }

  // Initial render with defaults
  refreshAllUI();
}

// ── Connect API ──
function connectAPI() {
  const input = document.getElementById('apiKeyInput');
  const key = input.value.trim();
  if (!key || !key.startsWith('sk-')) {
    input.style.borderColor = '#ef4444';
    input.style.animation = 'shake .3s';
    setTimeout(() => {
      input.style.borderColor = '';
      input.style.animation = '';
    }, 1500);
    return;
  }
  saveApiKey(key);
  document.getElementById('keySection').style.display = 'none';
  document.getElementById('analysisCard').style.display = 'block';
  document.getElementById('apiIndicator').innerHTML = '<span class="api-on">Claude</span>';
  document.getElementById('discBtn').style.display = 'inline-block';
  fetchAnalysis();
}

function skipAPI() {
  document.getElementById('keySection').style.display = 'none';
}

function disconnectAPI() {
  clearApiKey();
  document.getElementById('apiIndicator').innerHTML = '';
  document.getElementById('discBtn').style.display = 'none';
  document.getElementById('analysisCard').style.display = 'none';
  document.getElementById('keySection').style.display = 'block';
  liveData.scenarios = null;
  refreshAllUI();
}

// ── Fetch Analysis ──
async function fetchAnalysis() {
  const ld = document.getElementById('analysisLoading');
  const ct = document.getElementById('analysisContent');
  const er = document.getElementById('analysisError');
  const rb = document.getElementById('refreshBtn');

  ld.style.display = 'block';
  ct.style.display = 'none';
  er.style.display = 'none';
  rb.disabled = true;

  try {
    const raw = await callClaudeAPI();
    liveData = parseAPIResponse(raw);

    renderAnalysis();
    ld.style.display = 'none';
    ct.style.display = 'block';

    // Reset scenario selection if new scenarios came
    selectedScenario = 0;
    simDay = WAR_DAY;
    const slider = document.getElementById('simSlider');
    if (slider) slider.value = WAR_DAY;

    refreshAllUI();

  } catch (e) {
    er.style.display = 'block';
    er.innerHTML = '❌ ' + (e.message || 'خطأ في الاتصال');
    ld.style.display = 'none';

    // If we had no previous data, show content area anyway
    if (liveData.headline) {
      ct.style.display = 'block';
    }
  }
  rb.disabled = false;
}

// ── Toggle expand analysis ──
function toggleExpand() {
  const el = document.getElementById('expBox');
  const open = el.style.display !== 'none';
  el.style.display = open ? 'none' : 'block';
  document.getElementById('expArr').style.transform = open ? '' : 'rotate(180deg)';
  document.getElementById('expLbl').textContent = open ? 'عرض التحليل التفصيلي' : 'إخفاء';
}

// ── Start ──
document.addEventListener('DOMContentLoaded', init);
