"""
إعدادات الاختبار لخدمة الرسائل - منصة نائبك.كوم
"""

from .settings import *

# قاعدة بيانات في الذاكرة للاختبارات السريعة
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# تعطيل Redis للاختبارات
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# تعطيل Celery للاختبارات
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# تسريع كلمات المرور للاختبارات
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# تعطيل التسجيل للاختبارات
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# إعدادات البريد الإلكتروني للاختبارات
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# تعطيل الوسائط للاختبارات
DEFAULT_FILE_STORAGE = 'django.core.files.storage.InMemoryStorage'

# إعدادات أمان مخففة للاختبارات
SECRET_KEY = 'test-secret-key-for-testing-only'
DEBUG = True
ALLOWED_HOSTS = ['*']

# تعطيل CSRF للاختبارات API
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'rest_framework.authentication.SessionAuthentication',
]

# إعدادات الاختبار
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
