/**
 * رصد - مخطط خطّي مصغّر للسلاسل الزمنية (المؤشر عبر الفترة).
 *
 * الزمن يجري من اليسار لليمين في اللغتين (عُرف المخططات الزمنية حتى في
 * الواجهات العربية)، فالحاوية `dir="ltr"` صراحةً.
 */
import React from 'react';

export default function Sparkline({ points = [], max = 100, color = 'currentColor', height = 36, label }) {
  if (!points.length) return null;
  const w = 100;
  const step = points.length > 1 ? w / (points.length - 1) : w;
  const y = (v) => height - 2 - (Math.min(v, max) / max) * (height - 4);
  const coords = points.map((v, i) => `${(i * step).toFixed(2)},${y(v).toFixed(2)}`);
  const area = `0,${height} ${coords.join(' ')} ${w},${height}`;

  return (
    <svg
      dir="ltr"
      viewBox={`0 0 ${w} ${height}`}
      preserveAspectRatio="none"
      className="w-full block"
      style={{ height }}
      role="img"
      aria-label={label}
    >
      <polygon points={area} fill={color} opacity="0.12" />
      <polyline points={coords.join(' ')} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
