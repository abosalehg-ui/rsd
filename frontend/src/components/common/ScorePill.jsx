/**
 * رصد - شارة نسبة/درجة ملوّنة: درجة الخطر، ودرجة الأثر على المملكة، وثقة
 * الرابط السببي. النمط واحد (نص بلون الدرجة على خلفيته الشفافة وإطار داخلي)
 * فيُعدَّل من هنا وحده.
 *
 * `label`: وصف لقارئ الشاشة يحلّ محل الرقم المجرد (`role="img"` كي لا يُتجاهل
 * `aria-label` على `<span>`).
 */
import React from 'react';

export default function ScorePill({ color, children, title, label, size = 'text-xs', className = '' }) {
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 font-mono ${size} font-semibold tabular-nums ${className}`}
      style={{ color, background: `${color}1f`, boxShadow: `inset 0 0 0 1px ${color}55` }}
      title={title}
      {...(label ? { role: 'img', 'aria-label': label } : {})}
    >
      {children}
    </span>
  );
}
