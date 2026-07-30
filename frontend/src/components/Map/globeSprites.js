/**
 * رصد - علامات الكرة ثلاثية الأبعاد (Sprites).
 *
 * طبقة النقاط المدمجة في globe.gl ترسم **أسطوانة** تمتد من سطح الكرة إلى
 * الارتفاع المطلوب، وحجمها بالدرجات الجغرافية. النتيجة كانت أسطوانات قطرها
 * ~111 كم وارتفاعها ~96 كم تغطي جيرانها وتخرج الطائرات كأعمدة من الأرض.
 *
 * البديل هنا: Sprite (لوح يواجه الكاميرا دائماً) مع sizeAttenuation=false،
 * فيبقى حجمه **بالبكسل ثابتاً** مهما اقترب المستخدم أو ابتعد — كنقاط الخرائط
 * الحديثة. النسيج أبيض ويُلوَّن عبر material.color (الضرب اللوني)، فيكفي نسيج
 * واحد مشترك لكل العلامات.
 */
import { Sprite, SpriteMaterial, CanvasTexture, SRGBColorSpace, Color } from 'three';

const TEX_SIZE = 128;

function makeCanvas(size = TEX_SIZE) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  return c;
}

function toTexture(canvas) {
  const t = new CanvasTexture(canvas);
  t.colorSpace = SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

// ===== نسيج النقطة: نواة صلبة + هالة متلاشية =====
let dotTex = null;
export function dotTexture() {
  if (dotTex) return dotTex;
  const c = makeCanvas();
  const ctx = c.getContext('2d');
  const r = TEX_SIZE / 2;
  const g = ctx.createRadialGradient(r, r, 0, r, r, r);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.40, 'rgba(255,255,255,1)');
  g.addColorStop(0.52, 'rgba(255,255,255,0.45)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, TEX_SIZE, TEX_SIZE);
  dotTex = toTexture(c);
  return dotTex;
}

// ===== نسيج المنشأة/القاعدة: حلقة مفرّغة تميّزها عن نقاط الأحداث =====
let ringTex = null;
export function ringTexture() {
  if (ringTex) return ringTex;
  const c = makeCanvas();
  const ctx = c.getContext('2d');
  const r = TEX_SIZE / 2;
  ctx.strokeStyle = 'rgba(255,255,255,1)';
  ctx.lineWidth = TEX_SIZE * 0.13;
  ctx.beginPath();
  ctx.arc(r, r, r * 0.62, 0, Math.PI * 2);
  ctx.stroke();
  ctx.fillStyle = 'rgba(255,255,255,0.35)';
  ctx.beginPath();
  ctx.arc(r, r, r * 0.5, 0, Math.PI * 2);
  ctx.fill();
  ringTex = toTexture(c);
  return ringTex;
}

// ===== نسيج الطائرة: مسقط علوي متّجه نحو الشمال =====
// حدّ داكن حول جسم أبيض: الضرب اللوني يُبقي الحدّ داكناً ويلوّن الجسم، فتظل
// الطائرة مقروءة فوق مناطق مضيئة من نسيج الأرض الليلي.
let planeTex = null;
export function planeTexture() {
  if (planeTex) return planeTex;
  const c = makeCanvas();
  const ctx = c.getContext('2d');
  ctx.beginPath();
  ctx.moveTo(64, 10);    // الأنف
  ctx.lineTo(73, 46);
  ctx.lineTo(120, 76);   // طرف الجناح الأيمن
  ctx.lineTo(120, 89);
  ctx.lineTo(73, 74);
  ctx.lineTo(73, 101);
  ctx.lineTo(92, 115);   // المثبّت الأفقي الأيمن
  ctx.lineTo(92, 123);
  ctx.lineTo(64, 113);   // الذيل
  ctx.lineTo(36, 123);
  ctx.lineTo(36, 115);
  ctx.lineTo(55, 101);
  ctx.lineTo(55, 74);
  ctx.lineTo(8, 89);     // طرف الجناح الأيسر
  ctx.lineTo(8, 76);
  ctx.lineTo(55, 46);
  ctx.closePath();
  ctx.strokeStyle = 'rgba(0,0,0,0.85)';
  ctx.lineWidth = 7;
  ctx.lineJoin = 'round';
  ctx.stroke();
  ctx.fillStyle = '#ffffff';
  ctx.fill();
  planeTex = toTexture(c);
  return planeTex;
}

// ===== نسيج مجموعة الأحداث: قرص ملوّن يحمل العدد =====
// ملوّن مسبقاً (بلا ضرب لوني) كي يبقى الرقم أبيض فوق خلفية اللون.
const countCache = new Map();
const COUNT_CACHE_MAX = 60;

export function countTexture(count, color) {
  const key = `${count}|${color}`;
  const hit = countCache.get(key);
  if (hit) return hit;

  const c = makeCanvas();
  const ctx = c.getContext('2d');
  const r = TEX_SIZE / 2;
  const glow = ctx.createRadialGradient(r, r, r * 0.6, r, r, r);
  glow.addColorStop(0, `${color}66`);
  glow.addColorStop(1, `${color}00`);
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, TEX_SIZE, TEX_SIZE);

  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(r, r, r * 0.62, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,0.9)';
  ctx.lineWidth = 6;
  ctx.stroke();

  const label = count > 99 ? '99+' : String(count);
  ctx.fillStyle = '#0a0e17';
  ctx.font = `bold ${label.length > 2 ? 40 : 52}px monospace`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(label, r, r + 2);

  const tex = toTexture(c);
  if (countCache.size >= COUNT_CACHE_MAX) {
    const oldest = countCache.keys().next().value;
    countCache.get(oldest)?.dispose?.();
    countCache.delete(oldest);
  }
  countCache.set(key, tex);
  return tex;
}

/**
 * إنشاء علامة.
 * @param {object} o
 * @param {Texture} o.texture النسيج المشترك
 * @param {string} [o.color] لون الضرب — يُترك فارغاً للأنسجة الملوّنة مسبقاً
 * @param {number} o.scale الحجم كنسبة من ارتفاع نافذة العرض (0.03 ≈ 29px عند 900px)
 * @param {number} [o.rotation] دوران بالراديان في مستوى الشاشة (لاتجاه الطائرة)
 * @param {number} [o.opacity]
 */
export function makeSprite({ texture, color, scale, rotation = 0, opacity = 1 }) {
  const material = new SpriteMaterial({
    map: texture,
    transparent: true,
    opacity,
    depthWrite: false,      // لا تحجب العلامات المتجاورة بعضها
    sizeAttenuation: false, // حجم بكسلي ثابت مهما تغيّر التقريب
    rotation,
  });
  if (color) material.color = new Color(color);
  const sprite = new Sprite(material);
  sprite.scale.set(scale, scale, 1);
  return sprite;
}
