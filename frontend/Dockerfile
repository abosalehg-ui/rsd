# ===== رصد Frontend — صورة تطوير (Vite dev server + HMR) =====
# للإنتاج استخدم Dockerfile.prod (بناء ثابت + nginx). راجع docker-compose.prod.yml.
FROM node:20-alpine
WORKDIR /app
# نسخ ملفّي التبعيات أولاً للاستفادة من طبقة الكاش، وnpm ci لبناء قابل للتكرار
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
