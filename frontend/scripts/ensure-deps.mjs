#!/usr/bin/env node
/**
 * رصد - التحقق من تطابق node_modules مع package-lock.json قبل التشغيل/البناء.
 *
 * لماذا: start-rasad.bat كان يثبّت الحزم **فقط إن لم يوجد node_modules**، فمن
 * يسحب تحديثاً يرقّي تبعية يبقى على النسخة القديمة بلا أي تنبيه. حين رُقّيت
 * three إلى 0.184 (تتطلبها globe.gl) انهار خادم التطوير برسالة غامضة:
 *   No matching export in "three/build/three.module.js" for import "Timer"
 * لأن three@0.169 القديمة لا تصدّر Timer.
 *
 * الفحص هنا يقارن نسخ الحزم المثبّتة فعلاً (node_modules/.package-lock.json)
 * بالمطلوبة في القفل، ويشغّل npm install تلقائياً عند الاختلاف.
 *
 * يقارن **فروق النسخ للحزم الموجودة في الملفّين فقط**؛ الحزم الغائبة تماماً لا
 * تُعدّ اختلافاً كي لا يُطلق التثبيت في بناء إنتاجي بـ --omit=dev.
 */
import { existsSync, readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');

function readJson(path) {
  try { return JSON.parse(readFileSync(path, 'utf8')); } catch { return null; }
}

/** @returns {string|null} سبب عدم التطابق، أو null إن كان كل شيء متطابقاً */
export function findMismatch(lock, installed, hasNodeModules) {
  if (!hasNodeModules) return 'node_modules غير موجود';
  if (!lock) return null;                       // لا قفل ⇒ لا مرجع للمقارنة
  if (!installed) return 'سجل التثبيت (node_modules/.package-lock.json) مفقود';

  const want = lock.packages || {};
  const have = installed.packages || {};
  for (const [name, spec] of Object.entries(want)) {
    if (!name) continue;                        // المدخل "" هو المشروع نفسه
    const got = have[name];
    if (!got || !spec.version || !got.version) continue;
    if (spec.version !== got.version) {
      return `${name.replace(/^node_modules\//, '')}: المثبّت ${got.version} والمطلوب ${spec.version}`;
    }
  }
  return null;
}

function main() {
  const reason = findMismatch(
    readJson(join(root, 'package-lock.json')),
    readJson(join(root, 'node_modules', '.package-lock.json')),
    existsSync(join(root, 'node_modules'))
  );
  if (!reason) return;

  console.log(`\n[رصد] التبعيات غير محدَّثة (${reason})`);
  console.log('[رصد] تشغيل npm install تلقائياً…\n');

  const res = spawnSync('npm', ['install', '--no-audit', '--no-fund'], {
    cwd: root,
    stdio: 'inherit',
    shell: process.platform === 'win32',   // npm.cmd على ويندوز
  });

  if (res.status !== 0) {
    console.error('\n[رصد] فشل تثبيت التبعيات. شغّل يدوياً داخل مجلد frontend:');
    console.error('      npm install\n');
    process.exit(1);
  }
}

// لا نشغّل التثبيت عند الاستيراد من الاختبارات
if (process.argv[1] && process.argv[1].endsWith('ensure-deps.mjs')) main();
