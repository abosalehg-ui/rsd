import { describe, it, expect } from 'vitest';
import { esc, safeUrl } from './security';

describe('esc', () => {
  it('escapes HTML metacharacters', () => {
    expect(esc('<script>alert(1)</script>')).toBe('&lt;script&gt;alert(1)&lt;/script&gt;');
    expect(esc('a & b "c" \'d\'')).toBe('a &amp; b &quot;c&quot; &#39;d&#39;');
  });

  it('handles null/undefined safely', () => {
    expect(esc(null)).toBe('');
    expect(esc(undefined)).toBe('');
    expect(esc(42)).toBe('42');
  });
});

describe('safeUrl', () => {
  it('allows http/https URLs', () => {
    expect(safeUrl('https://example.com/x')).toBe('https://example.com/x');
    expect(safeUrl('http://example.com')).toBe('http://example.com');
  });

  it('blocks javascript: and other dangerous schemes', () => {
    expect(safeUrl('javascript:alert(1)')).toBe('');
    expect(safeUrl('data:text/html,<script>alert(1)</script>')).toBe('');
    expect(safeUrl('  javascript:void(0)  ')).toBe('');
    expect(safeUrl('file:///etc/passwd')).toBe('');
  });

  it('blocks null/undefined/relative', () => {
    expect(safeUrl(null)).toBe('');
    expect(safeUrl('/relative/path')).toBe('');
  });
});
