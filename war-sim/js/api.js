// ═══════════════════════════════════════
// api.js — Claude AI Integration
// ═══════════════════════════════════════

function getApiKey() {
  return localStorage.getItem(STORAGE_KEY) || '';
}

function saveApiKey(key) {
  localStorage.setItem(STORAGE_KEY, key);
}

function clearApiKey() {
  localStorage.removeItem(STORAGE_KEY);
}

function hasApiKey() {
  const k = getApiKey();
  return k && k.startsWith('sk-');
}

// ── Build the analysis prompt ──
function buildAnalysisPrompt() {
  const dateStr = TODAY.toISOString().split('T')[0];
  return `أنت محلل عسكري واستراتيجي خبير متخصص في شؤون الشرق الأوسط. ابحث عن آخر تطورات حرب إيران وأمريكا وإسرائيل 2026 اليوم (${dateStr}، اليوم ${WAR_DAY} من الحرب).

بناءً على ما تجده من أخبار ومعطيات حقيقية، قم بـ:
1. تحليل الوضع الحالي
2. توليد سيناريوهات نهاية الحرب المتوقعة بناءً على المعطيات الفعلية (ليست ثابتة — تتغير حسب الأحداث)

أجب بصيغة JSON فقط بدون backticks أو نص إضافي:
{
  "date": "${dateStr}",
  "war_day": ${WAR_DAY},
  "headline": "عنوان رئيسي لأهم حدث اليوم",
  "military": "تحليل عسكري مفصل في 3-4 جمل",
  "diplomatic": "تحليل دبلوماسي في 3-4 جمل",
  "economic": "تحليل اقتصادي في 2-3 جمل",
  "key_development": "أهم تطور جديد في جملتين",
  "missiles_remaining_est": رقم,
  "launchers_remaining_est": رقم,
  "nuclear_capability_pct": رقم من 0 لـ 100,
  "air_defense_pct": رقم من 0 لـ 100,
  "navy_pct": رقم من 0 لـ 100,
  "oil_price_est": رقم,
  "casualties_iran": رقم,
  "casualties_israel": رقم,
  "hormuz_status": "مفتوح" أو "مغلق جزئياً" أو "مغلق",
  "risk_level": رقم من 1 لـ 10,
  "scenarios": [
    {
      "name": "اسم السيناريو بالعربي",
      "name_en": "English Name",
      "probability": رقم نسبة الاحتمال (مجموع كل السيناريوهات = 100),
      "icon": "ايموجي واحد مناسب",
      "color": "لون hex مثل #F59E0B",
      "description": "وصف السيناريو في 2-3 جمل",
      "oil_forecast": "توقع سعر النفط",
      "hormuz_forecast": "توقع وضع مضيق هرمز",
      "regime_forecast": "توقع مصير النظام الإيراني",
      "nuclear_forecast": "توقع البرنامج النووي",
      "timeline": [
        {"day": رقم يوم الحرب, "event": "وصف الحدث المتوقع"},
        {"day": رقم, "event": "حدث آخر"},
        {"day": رقم, "event": "حدث آخر"},
        {"day": رقم, "event": "حدث آخر"},
        {"day": رقم, "event": "حدث آخر"}
      ]
    }
  ]
}

ملاحظات مهمة:
- ولّد 4-6 سيناريوهات بناءً على المعطيات الحقيقية اليوم
- السيناريوهات يجب أن تعكس الوضع الفعلي وليست ثابتة
- إذا كانت هناك مفاوضات جارية، أعطِ سيناريو التفاوض احتمالاً أعلى
- إذا كان هناك تصعيد، أعطِ سيناريو التصعيد احتمالاً أعلى
- أيام الجدول الزمني يجب أن تبدأ من ${WAR_DAY} وتمتد للمستقبل
- مجموع الاحتمالات = 100`;
}

// ── Call Claude API ──
async function callClaudeAPI() {
  const key = getApiKey();
  if (!key) throw new Error('لا يوجد مفتاح API');

  const resp = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': key,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true'
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 4000,
      tools: [{ type: 'web_search_20250305', name: 'web_search', max_uses: 5 }],
      messages: [{ role: 'user', content: buildAnalysisPrompt() }]
    })
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    if (resp.status === 401) {
      clearApiKey();
      throw new Error('مفتاح API غير صالح — تم حذفه. أعد إدخال مفتاح صحيح.');
    }
    throw new Error(err.error?.message || `خطأ HTTP ${resp.status}`);
  }

  const data = await resp.json();
  let fullText = '';
  if (data.content) {
    data.content.forEach(block => {
      if (block.type === 'text') fullText += block.text;
    });
  }

  const cleaned = fullText.replace(/```json|```/g, '').trim();
  let parsed;
  try {
    parsed = JSON.parse(cleaned);
  } catch {
    const match = cleaned.match(/\{[\s\S]*\}/);
    if (match) parsed = JSON.parse(match[0]);
    else throw new Error('لم يتم الحصول على بيانات JSON صالحة من Claude');
  }

  return parsed;
}

// ── Parse API response into app state ──
function parseAPIResponse(raw) {
  // Update live data
  const data = { ...liveData };

  data.missiles = raw.missiles_remaining_est ?? data.missiles;
  data.launchers = raw.launchers_remaining_est ?? data.launchers;
  data.nuclear_pct = raw.nuclear_capability_pct ?? data.nuclear_pct;
  data.airdef_pct = raw.air_defense_pct ?? data.airdef_pct;
  data.navy_pct = raw.navy_pct ?? data.navy_pct;
  data.oil = raw.oil_price_est ?? data.oil;
  data.dead_iran = raw.casualties_iran ?? data.dead_iran;
  data.dead_israel = raw.casualties_israel ?? data.dead_israel;
  data.risk = raw.risk_level ?? data.risk;
  data.hormuz = raw.hormuz_status ?? data.hormuz;
  data.headline = raw.headline ?? '';
  data.military = raw.military ?? '';
  data.diplomatic = raw.diplomatic ?? '';
  data.economic = raw.economic ?? '';
  data.key_development = raw.key_development ?? '';

  // Parse dynamic scenarios
  if (raw.scenarios && Array.isArray(raw.scenarios) && raw.scenarios.length > 0) {
    data.scenarios = raw.scenarios.map((s, i) => ({
      id: i + 1,
      name: s.name || `سيناريو ${i+1}`,
      en: s.name_en || `Scenario ${i+1}`,
      prob: s.probability || 0,
      color: s.color || ['#F59E0B','#10B981','#A855F7','#EF4444','#3B82F6','#06B6D4'][i % 6],
      icon: s.icon || '📌',
      desc: s.description || '',
      oil: s.oil_forecast || '--',
      hormuz: s.hormuz_forecast || '--',
      regime: s.regime_forecast || '--',
      nuke: s.nuclear_forecast || '--',
      events: (s.timeline || []).map(t => ({ d: t.day, e: t.event })),
    }));
    // Set likely scenario
    const sorted = [...data.scenarios].sort((a,b) => b.prob - a.prob);
    data.likely = sorted[0]?.name || data.likely;
  }

  return data;
}
