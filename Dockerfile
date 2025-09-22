# خدمة الرسائل - منصة نائبك.كوم
# Dockerfile للإنتاج

FROM python:3.11-slim

# تعيين متغيرات البيئة
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# تعيين مجلد العمل
WORKDIR /app

# تثبيت متطلبات النظام
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# إنشاء مستخدم غير جذر
RUN groupadd -r naebak && useradd -r -g naebak naebak

# نسخ ملفات المتطلبات
COPY requirements.txt requirements-test.txt ./

# تثبيت متطلبات Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn

# نسخ الكود
COPY . .

# إنشاء المجلدات المطلوبة
RUN mkdir -p /app/static /app/media /app/logs && \
    chown -R naebak:naebak /app

# التبديل للمستخدم غير الجذر
USER naebak

# جمع الملفات الثابتة
RUN python manage.py collectstatic --noinput

# فتح المنفذ
EXPOSE 8000

# إعدادات الصحة
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python manage.py check --deploy || exit 1

# الأمر الافتراضي
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "messaging_service.wsgi:application"]
