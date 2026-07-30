/**
 * اختبارات فحص تطابق التبعيات.
 *
 * الحالة التي يحرسها: سحب تحديث يرقّي تبعية دون إعادة تثبيت — كان
 * start-rasad.bat يتخطّى npm install كلما وُجد node_modules، فتبقى النسخة
 * القديمة ويسقط خادم التطوير برسالة غامضة عن استيراد "Timer" من three.
 */
import { describe, it, expect } from 'vitest';
import { findMismatch } from '../../scripts/ensure-deps.mjs';

const lock = {
  packages: {
    '': { name: 'rasad-frontend' },
    'node_modules/three': { version: '0.184.0' },
    'node_modules/leaflet': { version: '1.9.4' },
  },
};

describe('findMismatch', () => {
  it('يكتشف نسخة قديمة عالقة بعد ترقية القفل', () => {
    const installed = {
      packages: {
        'node_modules/three': { version: '0.169.0' },
        'node_modules/leaflet': { version: '1.9.4' },
      },
    };
    expect(findMismatch(lock, installed, true)).toMatch(/three.*0\.169\.0.*0\.184\.0/);
  });

  it('يصمت حين تتطابق النسخ', () => {
    const installed = {
      packages: {
        'node_modules/three': { version: '0.184.0' },
        'node_modules/leaflet': { version: '1.9.4' },
      },
    };
    expect(findMismatch(lock, installed, true)).toBeNull();
  });

  it('يبلّغ حين يكون node_modules مفقوداً', () => {
    expect(findMismatch(lock, null, false)).toMatch(/node_modules/);
  });

  it('يبلّغ حين يغيب سجل التثبيت', () => {
    expect(findMismatch(lock, null, true)).toMatch(/سجل التثبيت/);
  });

  it('لا يعدّ الحزم الغائبة اختلافاً (بناء إنتاجي بلا تبعيات التطوير)', () => {
    const installed = { packages: { 'node_modules/three': { version: '0.184.0' } } };
    expect(findMismatch(lock, installed, true)).toBeNull();
  });

  it('يتجاهل مدخل المشروع نفسه ("")', () => {
    const installed = { packages: { '': { name: 'other' }, 'node_modules/three': { version: '0.184.0' } } };
    expect(findMismatch(lock, installed, true)).toBeNull();
  });
});
