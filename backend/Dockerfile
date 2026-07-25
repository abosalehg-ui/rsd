FROM python:3.12-slim

# مستخدم غير جذري — لا تحتاج الحاوية صلاحيات root بعد تثبيت الحزم
RUN useradd --create-home --shell /usr/sbin/nologin rasad

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /app/data && chown -R rasad:rasad /app

USER rasad
EXPOSE 8000
# ملاحظة: --host 0.0.0.0 مطلوب داخل الحاوية لتكون قابلة للوصول من الشبكة
# الافتراضية لـ compose؛ التحكّم بالتعرّض يتم عبر ربط المنفذ في compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
