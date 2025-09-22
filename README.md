# خدمة الرسائل - منصة نائبك.كوم

[![Django](https://img.shields.io/badge/Django-4.2.7-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.0-red.svg)](https://redis.io/)

خدمة الرسائل هي جزء من منصة **نائبك.كوم** التي تهدف لربط المواطنين بنوابهم في البرلمان المصري. تتيح هذه الخدمة للمواطنين التواصل المباشر مع النواب من خلال نظام رسائل آمن ومنظم.

## 🎯 الهدف من الخدمة

تسهيل التواصل بين المواطنين والنواب من خلال:
- **نظام رسائل آمن** للتواصل المباشر
- **إدارة المحادثات** بطريقة منظمة ومهنية
- **نظام إشعارات** لضمان وصول الرسائل
- **إحصائيات شاملة** لمتابعة التفاعل
- **نظام إبلاغات** للحفاظ على جودة المحتوى

## 🏗️ البنية التقنية

### التقنيات المستخدمة
- **Backend**: Django 4.2.7 + Django REST Framework
- **قاعدة البيانات**: PostgreSQL 15
- **Cache**: Redis 7.0
- **المهام غير المتزامنة**: Celery
- **المصادقة**: JWT Tokens
- **التوثيق**: Swagger/OpenAPI

### النماذج الأساسية
1. **UserProfile** - ملفات المستخدمين الموسعة
2. **Conversation** - المحادثات بين المواطنين والنواب
3. **Message** - الرسائل داخل المحادثات
4. **MessageReport** - إبلاغات عن الرسائل المسيئة
5. **SystemNotification** - إشعارات النظام
6. **MessageStatistics** - إحصائيات الرسائل

## 🚀 المميزات

### للمواطنين
- ✅ **إنشاء محادثات** مع النواب
- ✅ **إرسال واستقبال الرسائل** بشكل آمن
- ✅ **تقييم المحادثات** بعد الانتهاء
- ✅ **إشعارات فورية** للرسائل الجديدة
- ✅ **إحصائيات شخصية** للتفاعل

### للنواب
- ✅ **إدارة المحادثات** مع المواطنين
- ✅ **الرد على الرسائل** بكفاءة
- ✅ **إغلاق المحادثات** المكتملة
- ✅ **إبلاغ عن المحتوى المسيء**
- ✅ **إحصائيات تفصيلية** للأداء

### للإدارة
- ✅ **مراجعة الإبلاغات**
- ✅ **إدارة المستخدمين**
- ✅ **إحصائيات شاملة** للمنصة
- ✅ **إرسال إشعارات النظام**

## 📡 واجهات برمجة التطبيقات (APIs)

### المستخدمين
```http
POST /api/profiles/create/          # إنشاء ملف مستخدم
GET  /api/profiles/me/              # الحصول على ملف المستخدم الحالي
PUT  /api/profiles/me/              # تحديث ملف المستخدم
```

### المحادثات
```http
GET    /api/conversations/          # قائمة المحادثات
POST   /api/conversations/          # إنشاء محادثة جديدة
GET    /api/conversations/{id}/     # تفاصيل محادثة
POST   /api/conversations/{id}/close/  # إغلاق محادثة
POST   /api/conversations/{id}/rate/   # تقييم محادثة
GET    /api/conversations/my/       # محادثات المستخدم الحالي
GET    /api/conversations/stats/    # إحصائيات المحادثات
```

### الرسائل
```http
GET    /api/messages/               # قائمة الرسائل
POST   /api/messages/               # إرسال رسالة جديدة
GET    /api/messages/{id}/          # تفاصيل رسالة
POST   /api/messages/{id}/read/     # تحديد رسالة كمقروءة
POST   /api/messages/mark-conversation-read/  # تحديد رسائل المحادثة كمقروءة
GET    /api/messages/unread-count/  # عدد الرسائل غير المقروءة
```

### الإبلاغات
```http
GET    /api/reports/                # قائمة الإبلاغات
POST   /api/reports/                # إنشاء إبلاغ جديد
GET    /api/reports/{id}/           # تفاصيل إبلاغ
```

### الإشعارات
```http
GET    /api/notifications/          # قائمة الإشعارات
POST   /api/notifications/{id}/read/  # تحديد إشعار كمقروء
POST   /api/notifications/mark-all-read/  # تحديد جميع الإشعارات كمقروءة
GET    /api/notifications/unread-count/   # عدد الإشعارات غير المقروءة
```

### الإحصائيات
```http
GET    /api/stats/user/             # إحصائيات المستخدم
GET    /api/stats/conversations/    # إحصائيات المحادثات
```

## 🔧 التثبيت والتشغيل

### المتطلبات
- Python 3.11+
- PostgreSQL 15+
- Redis 7.0+

### خطوات التثبيت

1. **استنساخ المستودع**
```bash
git clone https://github.com/alcounsol17/naebak-messaging-service.git
cd naebak-messaging-service
```

2. **إنشاء البيئة الافتراضية**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو
venv\Scripts\activate     # Windows
```

3. **تثبيت المتطلبات**
```bash
pip install -r requirements.txt
```

4. **إعداد قاعدة البيانات**
```bash
# إنشاء قاعدة بيانات PostgreSQL
createdb naebak_messaging

# تطبيق المايجريشن
python manage.py migrate
```

5. **إعداد Redis**
```bash
# تشغيل Redis
redis-server
```

6. **إنشاء مستخدم إداري**
```bash
python manage.py createsuperuser
```

7. **تشغيل الخادم**
```bash
python manage.py runserver
```

### متغيرات البيئة

إنشئ ملف `.env` في المجلد الجذر:

```env
# إعدادات قاعدة البيانات
DATABASE_NAME=naebak_messaging
DATABASE_USER=postgres
DATABASE_PASSWORD=your_password
DATABASE_HOST=localhost
DATABASE_PORT=5432

# إعدادات Redis
REDIS_URL=redis://localhost:6379/0

# إعدادات Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# إعدادات JWT
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=1440

# إعدادات البريد الإلكتروني
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# إعدادات Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## 🧪 الاختبارات

تشغيل جميع الاختبارات:
```bash
python -m pytest
```

تشغيل اختبارات محددة:
```bash
python -m pytest tests/test_models.py
python -m pytest tests/test_apis.py
python -m pytest tests/test_serializers.py
```

تشغيل الاختبارات مع تغطية الكود:
```bash
python -m pytest --cov=messages --cov-report=html
```

## 📊 الإحصائيات والمراقبة

### مؤشرات الأداء الرئيسية (KPIs)
- **عدد المحادثات النشطة**
- **متوسط وقت الاستجابة**
- **معدل رضا المواطنين**
- **عدد الرسائل اليومية**
- **معدل إغلاق المحادثات**

### التسجيل والمراقبة
- **Django Logging** لتسجيل الأحداث
- **Database Logging** لتتبع العمليات
- **Performance Monitoring** لمراقبة الأداء
- **Error Tracking** لتتبع الأخطاء

## 🔒 الأمان

### المصادقة والتفويض
- **JWT Tokens** للمصادقة
- **Role-based Access Control** للصلاحيات
- **Rate Limiting** لمنع الإساءة
- **Input Validation** للتحقق من البيانات

### حماية البيانات
- **تشفير كلمات المرور** باستخدام Django
- **HTTPS Only** في الإنتاج
- **CORS Configuration** للحماية من الطلبات الضارة
- **SQL Injection Protection** من خلال Django ORM

## 🚀 النشر

### Docker
```bash
# بناء الصورة
docker build -t naebak-messaging-service .

# تشغيل الحاوية
docker run -p 8000:8000 naebak-messaging-service
```

### Docker Compose
```bash
docker-compose up -d
```

### GitHub Actions
يتم النشر التلقائي عند الدفع إلى branch `main` من خلال GitHub Actions.

## 📈 خطة التطوير المستقبلية

### المرحلة القادمة
- [ ] **نظام الملفات المرفقة** في الرسائل
- [ ] **الرسائل الصوتية** للتواصل
- [ ] **الترجمة التلقائية** للرسائل
- [ ] **البحث المتقدم** في المحادثات
- [ ] **تصدير المحادثات** بصيغة PDF

### التحسينات التقنية
- [ ] **WebSocket** للرسائل الفورية
- [ ] **Push Notifications** للهواتف المحمولة
- [ ] **GraphQL API** كبديل لـ REST
- [ ] **Elasticsearch** للبحث المتقدم
- [ ] **Machine Learning** لتصنيف الرسائل

## 🤝 المساهمة

نرحب بالمساهمات! يرجى اتباع الخطوات التالية:

1. Fork المستودع
2. إنشاء branch جديد (`git checkout -b feature/amazing-feature`)
3. Commit التغييرات (`git commit -m 'Add amazing feature'`)
4. Push إلى البranch (`git push origin feature/amazing-feature`)
5. فتح Pull Request

### معايير المساهمة
- **كتابة الاختبارات** لجميع الميزات الجديدة
- **اتباع PEP 8** لتنسيق الكود
- **توثيق الكود** باللغة العربية
- **اختبار الكود** قبل الإرسال

## 📝 الترخيص

هذا المشروع مرخص تحت رخصة MIT - راجع ملف [LICENSE](LICENSE) للتفاصيل.

## 📞 التواصل

- **الموقع الرسمي**: [نائبك.كوم](https://naebak.com)
- **البريد الإلكتروني**: info@naebak.com
- **GitHub**: [@alcounsol17](https://github.com/alcounsol17)

## 🙏 شكر وتقدير

شكر خاص للمساهمين في تطوير هذا المشروع:
- فريق تطوير منصة نائبك.كوم
- مجتمع Django العربي
- جميع المختبرين والمراجعين

---

**منصة نائبك.كوم** - *ربط المواطنين بنوابهم*

![نائبك.كوم](https://via.placeholder.com/800x200/4CAF50/FFFFFF?text=نائبك.كوم+-+خدمة+الرسائل)
