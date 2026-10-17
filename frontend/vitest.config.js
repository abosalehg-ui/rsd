import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.js'],
    css: false,
    include: ['src/**/*.{test,spec}.{js,jsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['node_modules/', 'src/test/', '**/*.config.js', 'dist/'],
      // حدّ أدنى يُفشل CI إن انخفضت التغطية (نظير --cov-fail-under=75 في الخلفية)
      thresholds: { lines: 75, statements: 70, functions: 65, branches: 60 },
    },
  },
});
