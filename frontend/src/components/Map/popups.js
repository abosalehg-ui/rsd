/**
 * رصد - قوالب نوافذ الخريطة.
 *
 * كانت خمسة قوالب HTML طويلة مكتوبة كسلاسل داخل تأثيرات `RasadMap.jsx`،
 * بألوان hex يدوية مكرّرة في كل واحد، فبلغ الملف 629 سطرًا وتعذّر اختبار
 * القوالب وحدها. هنا دوال نقيّة تأخذ بيانات وتُعيد HTML — قابلة للاختبار
 * مباشرة، وألوانها من `THEME` وحده.
 *
 * قاعدة ثابتة: بيانات الأحداث/الضربات/المنشآت تأتي من مصادر خارجية غير
 * موثوقة، فكل قيمة تمرّ عبر `esc()` وكل رابط عبر `safeUrl()` قبل الحقن.
 */
import {
  CATEGORIES, CONFIDENCE, COUNTRIES, IRAN_EVENT_TYPES, THEME,
  categoryOf, severityOf, timeAgo,
} from '../../utils/constants';
import { esc, safeUrl } from '../../utils/security';

/** غلاف موحّد — الاتجاه يتبع لغة الواجهة لا قيمة ثابتة. */
export function popupShell(inner, dir, minWidth = 220) {
  return `<div style="min-width:${minWidth}px;font-family:Tajawal,sans-serif;direction:${dir}">${inner}</div>`;
}

/** شارة ملوّنة صغيرة (تصنيف/خطورة/ثقة/نوع). */
function badge(label, color, icon = '') {
  const prefix = icon ? `${icon} ` : '';
  return `<span style="font-size:11px;padding:2px 6px;border-radius:4px;background:${color}20;color:${color}">${prefix}${esc(label)}</span>`;
}

/** رابط "المصدر ←" أسفل النافذة، أو سلسلة فارغة إن كان الرابط غير آمن. */
function sourceLink(url, t) {
  const link = safeUrl(url);
  if (!link) return '';
  return `<a href="${esc(link)}" target="_blank" rel="noopener noreferrer" style="display:block;margin-top:6px;font-size:11px;color:${THEME.accent}">${esc(t('map.sourceLink'))}</a>`;
}

/** سطر "المفتاح: القيمة" داخل جسم النافذة. */
function row(label, value, color = THEME.textSecondary) {
  return `<div>${esc(label)}: <span style="color:${color}">${esc(value)}</span></div>`;
}

/** صندوق ملاحظات اختياري. */
function notes(text) {
  if (!text) return '';
  return `<div style="margin-top:6px;padding:6px;background:${THEME.border};border-radius:4px;color:${THEME.textSecondary};font-size:11px">${esc(text)}</div>`;
}

// ===== حدث مفرد =====

export function eventPopup(ev, { t, dir }) {
  const cat = categoryOf(ev.category);
  const sev = severityOf(ev.severity);
  const catLabel = t(`categories.${ev.category}`, { defaultValue: t('categories.general') });
  const sevLabel = t(`severity.${ev.severity}`, { defaultValue: t('severity.low') });
  const flag = COUNTRIES[ev.country_code]?.flag || '🌍';
  const country = t(`countries.${ev.country_code}`, { defaultValue: ev.country || '' });

  return popupShell(`
    <div style="display:flex;gap:4px;margin-bottom:6px">
      <span style="font-size:16px">${cat.icon}</span>
      ${badge(catLabel, cat.color)}
      ${badge(sevLabel, sev.color)}
    </div>
    <h3 style="font-size:13px;font-weight:700;margin-bottom:4px;line-height:1.5">${esc(ev.title)}</h3>
    <p style="font-size:11px;color:${THEME.textSecondary};margin-bottom:6px">${esc((ev.description || '').substring(0, 100))}</p>
    <div style="display:flex;justify-content:space-between;font-size:11px;color:${THEME.textMuted}">
      <span>${flag} ${esc(country)}</span><span>${esc(timeAgo(ev.event_date, t))}</span>
    </div>
    ${sourceLink(ev.url, t)}
  `, dir);
}

// ===== مجموعة أحداث =====

export const CLUSTER_LIST_LIMIT = 8;

export function clusterPopup(cluster, { t, dir }) {
  const count = cluster.events.length;
  const listHtml = cluster.events.slice(0, CLUSTER_LIST_LIMIT).map(ev => {
    const cat = categoryOf(ev.category);
    return `<div class="rasad-cluster-item" data-id="${esc(ev.id)}" tabindex="0" role="button" style="padding:4px 0;border-bottom:1px solid ${THEME.border};font-size:11px;line-height:1.5;cursor:pointer;color:${THEME.textSecondary}">${cat.icon} ${esc((ev.title || '').substring(0, 60))}</div>`;
  }).join('');

  const moreText = count > CLUSTER_LIST_LIMIT
    ? `<div style="font-size:11px;color:${THEME.textMuted};padding-top:4px">${esc(t('map.clusterMore', { count: count - CLUSTER_LIST_LIMIT }))}</div>`
    : '';

  return popupShell(`
    <div style="max-height:250px;overflow-y:auto">
      <div style="font-size:12px;font-weight:700;margin-bottom:6px;color:${THEME.accent}">${esc(t('map.clusterTitle', { count }))}</div>
      ${listHtml}
      ${moreText}
    </div>
  `, dir, 240);
}

// ===== رحلة =====

export function flightPopup(f, { t, dir }) {
  const isMil = f.is_military;
  const altitude = f.altitude
    ? `${esc(Math.round(f.altitude))} ${esc(t('map.metersShort'))}`
    : '—';
  const speed = f.velocity
    ? `${esc(Math.round(f.velocity * 3.6))} ${esc(t('map.kmhShort'))}`
    : '—';

  return popupShell(`
    <div style="font-weight:700;font-family:monospace">${esc(f.callsign || f.icao24)}</div>
    ${isMil ? `<span style="font-size:11px;color:${THEME.violetSoft}">⚔️ ${esc(t('map.military'))}</span>` : ''}
    <div style="font-size:11px;color:${THEME.textSecondary};margin-top:4px">
      ${esc(f.origin_country || '')}<br/>
      ${esc(t('map.altitude'))}: ${altitude}<br/>
      ${esc(t('map.speed'))}: ${speed}
    </div>
  `, dir, 160);
}

// ===== ضربة إيران OSINT =====

export function iranPopup(strike, { t, dir }) {
  const conf = CONFIDENCE[strike.confidence] || CONFIDENCE.LOW;
  const evType = IRAN_EVENT_TYPES[strike.event_type] || IRAN_EVENT_TYPES.strike;
  const confLabel = t(`confidence.${strike.confidence}`, { defaultValue: t('confidence.LOW') });
  const typeLabel = t(`iranEventTypes.${strike.event_type}`, { defaultValue: t('iranEventTypes.strike') });
  const videoLink = safeUrl(strike.video_url);

  const videoBadge = videoLink
    ? `<a href="${esc(videoLink)}" target="_blank" rel="noopener noreferrer" style="font-size:11px;padding:2px 6px;border-radius:4px;background:#7c3aed20;color:${THEME.violetSoft}">${esc(t('map.osintVideo'))}</a>`
    : '';

  return popupShell(`
    <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap">
      <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:${conf.color}20;color:${conf.color};border:1px solid ${conf.color}40">
        ${conf.icon} ${esc(confLabel)}
      </span>
      ${badge(typeLabel, evType.color, evType.icon)}
      ${videoBadge}
    </div>
    <h3 style="font-size:13px;font-weight:700;margin-bottom:4px;line-height:1.5">${esc(strike.title)}</h3>
    <p style="font-size:11px;color:${THEME.textSecondary};margin-bottom:6px">${esc((strike.description || '').substring(0, 120))}</p>
    <div style="font-size:11px;color:${THEME.textMuted};display:flex;justify-content:space-between;gap:8px">
      <span>📍 ${esc(strike.location_name || strike.country || '')}</span>
      <span>${esc(strike.feed_name || '')}</span>
    </div>
    ${sourceLink(strike.url, t)}
  `, dir, 240);
}

// ===== منشأة نووية =====

export function nuclearPopup(fac, { t, dir, typeColor, statusColor }) {
  const typeLabel = t(`nuclearTypes.${fac.type}`, { defaultValue: fac.type || '-' });
  const statusLabel = t(`nuclearStatus.${fac.status}`, { defaultValue: fac.status || '-' });
  const name = fac.name_ar || fac.name_en || '';

  const capacity = fac.capacity_mw
    ? row(t('map.capacity'), `${fac.capacity_mw} MW`, THEME.highlight) : '';
  const firstGrid = fac.first_grid ? row(t('map.firstGrid'), fac.first_grid) : '';
  const operator = fac.operator ? row(t('map.operator'), fac.operator) : '';

  return popupShell(`
    <div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap">
      <span style="font-size:11px;padding:2px 6px;border-radius:4px;background:${typeColor}20;color:${typeColor};border:1px solid ${typeColor}40">
        ☢️ ${esc(typeLabel)}
      </span>
      ${badge(statusLabel, statusColor)}
    </div>
    <h3 style="font-size:13px;font-weight:700;margin-bottom:6px;line-height:1.5;color:${THEME.highlight}">${esc(name)}</h3>
    <div style="font-size:11px;color:${THEME.textSecondary};margin-bottom:6px">${esc(fac.name_en || '')}</div>
    <div style="font-size:12px;color:${THEME.text};line-height:1.8">
      ${row(t('map.country'), fac.country || '-', THEME.accent)}
      ${row(t('map.type'), fac.reactor_type || '-')}
      ${capacity}
      ${firstGrid}
      ${operator}
    </div>
    ${notes(fac.notes)}
    <div style="font-size:11px;color:${THEME.textMuted};margin-top:6px;font-family:monospace">
      ${fac.latitude.toFixed(3)}, ${fac.longitude.toFixed(3)}
    </div>
  `, dir, 240);
}

// ===== قاعدة عسكرية =====

export function basePopup(b, { t, dir }) {
  return popupShell(`
    <div style="font-size:13px;font-weight:700;color:${THEME.violetSoft};margin-bottom:4px">${esc(b.name_ar || b.name_en || '')}</div>
    <div style="font-size:11px;color:${THEME.textSecondary};margin-bottom:6px">${esc(b.name_en || '')}</div>
    <div style="font-size:12px;color:${THEME.text};line-height:1.7">
      ${row(t('map.country'), b.country || '-', THEME.accent)}
      ${row(t('map.operator'), b.operator || '-', THEME.highlight)}
      ${row(t('map.type'), b.type || '-')}
    </div>
    ${notes(b.notes)}
  `, dir);
}

// ===== خط أنابيب =====

export function pipelinePopup(p, { t, dir, color }) {
  const capacity = p.capacity_mbpd
    ? `${p.capacity_mbpd} ${t('map.mbpd')}`
    : p.capacity_bcm ? `${p.capacity_bcm} ${t('map.bcm')}` : '-';

  return popupShell(`
    <div style="font-size:13px;font-weight:700;color:${color};margin-bottom:4px">${p.type === 'oil' ? '🛢️' : '🔥'} ${esc(p.name_ar || p.name_en || '')}</div>
    <div style="font-size:11px;color:${THEME.textSecondary};margin-bottom:6px">${esc(p.name_en || '')}</div>
    <div style="font-size:12px;color:${THEME.text};line-height:1.7">
      ${row(t('map.length'), `${p.length_km || '-'} ${t('map.kmShort')}`, THEME.accent)}
      ${row(t('map.capacity'), capacity, THEME.highlight)}
      ${row(t('map.operator'), p.operator || '-')}
      ${row(t('map.status'), p.status || '-')}
    </div>
  `, dir);
}
