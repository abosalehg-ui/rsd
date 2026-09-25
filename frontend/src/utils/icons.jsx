/**
 * رصد - مجموعة أيقونات واحدة.
 *
 * كانت الواجهة تخلط الرموز التعبيرية (☣️ 💥 🤝) بأيقونات lucide: يختلف حجم
 * الإيموجي ولونه بين ويندوز وماك وأندرويد، ولا يُلوَّن بلون التصنيف. هنا
 * أسماء ثابتة → مكوّنات lucide، ومعها `iconSvg()` لقوالب HTML الخام (نوافذ
 * Leaflet وعلاماتها) التي لا تستطيع استعمال JSX.
 */
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import {
  Atom, Radiation, Swords, Handshake, HeartPulse, TrendingUp, Newspaper,
  Flame, Rocket, Shield, Plane, Anchor, Crosshair, Factory, Droplets, FlaskConical,
  Fuel, MapPin,
} from 'lucide-react';

export const ICONS = {
  atom: Atom,
  radiation: Radiation,
  swords: Swords,
  handshake: Handshake,
  heart: HeartPulse,
  trend: TrendingUp,
  news: Newspaper,
  flame: Flame,
  rocket: Rocket,
  shield: Shield,
  plane: Plane,
  anchor: Anchor,
  crosshair: Crosshair,
  factory: Factory,
  droplets: Droplets,
  flask: FlaskConical,
  fuel: Fuel,
  pin: MapPin,
};

/** أيقونة باسمها — تقع على «خبر» للأسماء غير المعروفة. */
export function Icon({ name, className = 'w-4 h-4', ...props }) {
  const Cmp = ICONS[name] || Newspaper;
  return <Cmp className={className} aria-hidden="true" {...props} />;
}

const svgCache = new Map();

/** SVG نصّي لقوالب HTML الخام. مخزَّن مؤقتًا لأن العلامات تُبنى بالمئات. */
export function iconSvg(name, { size = 14, color = 'currentColor', strokeWidth = 2 } = {}) {
  const key = `${name}|${size}|${color}|${strokeWidth}`;
  if (!svgCache.has(key)) {
    const Cmp = ICONS[name] || Newspaper;
    svgCache.set(key, renderToStaticMarkup(
      <Cmp width={size} height={size} color={color} strokeWidth={strokeWidth} aria-hidden="true" />,
    ));
  }
  return svgCache.get(key);
}
