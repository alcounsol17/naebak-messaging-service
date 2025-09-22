"""
نماذج قاعدة البيانات لخدمة الرسائل - منصة نائبك.كوم
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxLengthValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone


class BaseModel(models.Model):
    """نموذج أساسي يحتوي على الحقول المشتركة"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        abstract = True


class UserProfile(BaseModel):
    """نموذج ملف المستخدم الموسع"""
    
    USER_TYPES = [
        ('citizen', 'مواطن'),
        ('representative', 'نائب'),
        ('admin', 'مدير'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="المستخدم")
    user_type = models.CharField(max_length=20, choices=USER_TYPES, verbose_name="نوع المستخدم")
    phone = models.CharField(
        max_length=15, 
        blank=True, 
        verbose_name="رقم الهاتف",
        validators=[RegexValidator(
            regex=r'^\d{10,15}$',
            message='رقم الهاتف يجب أن يكون بين 10 و 15 رقم'
        )]
    )
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="الصورة الشخصية")
    
    # معلومات إضافية للنواب
    representative_id = models.UUIDField(blank=True, null=True, verbose_name="معرف النائب في خدمة المحتوى")
    district = models.CharField(max_length=100, blank=True, verbose_name="الدائرة الانتخابية")
    governorate = models.CharField(max_length=50, blank=True, verbose_name="المحافظة")
    
    # إعدادات الإشعارات
    email_notifications = models.BooleanField(default=True, verbose_name="إشعارات البريد الإلكتروني")
    sms_notifications = models.BooleanField(default=False, verbose_name="إشعارات الرسائل النصية")
    
    class Meta:
        verbose_name = "ملف المستخدم"
        verbose_name_plural = "ملفات المستخدمين"
        indexes = [
            models.Index(fields=['user_type']),
            models.Index(fields=['representative_id']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_user_type_display()}"

    @property
    def full_name(self):
        """إرجاع الاسم الكامل"""
        return self.user.get_full_name() or self.user.username


class Conversation(BaseModel):
    """نموذج المحادثة بين المواطن والنائب"""
    
    citizen = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='citizen_conversations',
        verbose_name="المواطن"
    )
    representative = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='representative_conversations',
        verbose_name="النائب"
    )
    
    subject = models.CharField(max_length=200, verbose_name="موضوع المحادثة")
    
    # إحصائيات المحادثة
    total_messages = models.PositiveIntegerField(default=0, verbose_name="إجمالي الرسائل")
    last_message_at = models.DateTimeField(null=True, blank=True, verbose_name="آخر رسالة")
    last_message_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='last_messages',
        verbose_name="آخر مرسل"
    )
    
    # حالة المحادثة
    is_closed = models.BooleanField(default=False, verbose_name="مغلقة")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإغلاق")
    closed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='closed_conversations',
        verbose_name="أغلقها"
    )
    
    # تقييم المحادثة
    citizen_rating = models.PositiveSmallIntegerField(
        null=True, 
        blank=True, 
        choices=[(i, i) for i in range(1, 6)],
        verbose_name="تقييم المواطن"
    )
    citizen_feedback = models.TextField(blank=True, verbose_name="تعليق المواطن")
    
    class Meta:
        verbose_name = "محادثة"
        verbose_name_plural = "المحادثات"
        indexes = [
            models.Index(fields=['citizen', 'representative']),
            models.Index(fields=['is_closed', 'last_message_at']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-last_message_at', '-created_at']

    def __str__(self):
        if len(self.subject) > 30:
            return f"{self.subject[:30]}..."
        return self.subject

    def save(self, *args, **kwargs):
        # تحديث آخر رسالة عند إنشاء المحادثة
        if not self.last_message_at:
            self.last_message_at = timezone.now()
        super().save(*args, **kwargs)
    
    def close(self, closed_by_user):
        """إغلاق المحادثة"""
        self.is_closed = True
        self.closed_at = timezone.now()
        self.closed_by = closed_by_user
        self.save()
    
    def update_last_message(self, message):
        """تحديث آخر رسالة"""
        self.last_message_at = message.created_at
        self.last_message_by = message.sender
        self.total_messages = self.messages.count()
        self.save()

    @property
    def unread_count_for_citizen(self):
        """عدد الرسائل غير المقروءة للمواطن"""
        return self.messages.filter(
            sender=self.representative,
            is_read=False
        ).count()

    @property
    def unread_count_for_representative(self):
        """عدد الرسائل غير المقروءة للنائب"""
        return self.messages.filter(
            sender=self.citizen,
            is_read=False
        ).count()


class Message(BaseModel):
    """نموذج الرسالة"""
    
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages',
        verbose_name="المحادثة"
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages',
        verbose_name="المرسل"
    )
    
    # محتوى الرسالة (حد أقصى 500 حرف كما هو مطلوب في البرومبت)
    content = models.TextField(
        validators=[MaxLengthValidator(500)],
        verbose_name="محتوى الرسالة",
        help_text="الحد الأقصى 500 حرف"
    )
    
    # حالة الرسالة
    is_read = models.BooleanField(default=False, verbose_name="مقروءة")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ القراءة")
    
    # معلومات إضافية
    is_system_message = models.BooleanField(default=False, verbose_name="رسالة نظام")
    reply_to = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="رد على"
    )
    
    class Meta:
        verbose_name = "رسالة"
        verbose_name_plural = "الرسائل"
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'is_read']),
            models.Index(fields=['is_system_message']),
        ]
        ordering = ['created_at']

    def __str__(self):
        if self.is_system_message:
            return "رسالة نظام"
        content_preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        sender_name = self.sender.get_full_name() or self.sender.username
        return f"رسالة من {sender_name}: {content_preview}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # تحديث إحصائيات المحادثة
            self.conversation.total_messages = self.conversation.messages.count()
            self.conversation.last_message_at = self.created_at
            self.conversation.last_message_by = self.sender
            self.conversation.save(update_fields=['total_messages', 'last_message_at', 'last_message_by'])

    def mark_as_read(self, user=None):
        """تحديد الرسالة كمقروءة"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @property
    def is_from_citizen(self):
        """هل الرسالة من المواطن"""
        try:
            return self.sender.userprofile.user_type == 'citizen'
        except:
            return False

    @property
    def is_from_representative(self):
        """هل الرسالة من النائب"""
        try:
            return self.sender.userprofile.user_type == 'representative'
        except:
            return False


class MessageReport(BaseModel):
    """نموذج الإبلاغ عن الرسائل"""
    
    REPORT_REASONS = [
        ('spam', 'رسائل مزعجة'),
        ('inappropriate', 'محتوى غير مناسب'),
        ('harassment', 'تحرش أو إساءة'),
        ('fake', 'معلومات مضللة'),
        ('other', 'أخرى'),
    ]
    
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='reports',
        verbose_name="الرسالة"
    )
    reporter = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='message_reports',
        verbose_name="المبلغ"
    )
    
    reason = models.CharField(max_length=20, choices=REPORT_REASONS, verbose_name="سبب الإبلاغ")
    description = models.TextField(blank=True, verbose_name="وصف الإبلاغ")
    
    # حالة الإبلاغ
    is_reviewed = models.BooleanField(default=False, verbose_name="تمت المراجعة")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ المراجعة")
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_reports',
        verbose_name="راجعها"
    )
    
    action_taken = models.TextField(blank=True, verbose_name="الإجراء المتخذ")
    
    class Meta:
        verbose_name = "إبلاغ عن رسالة"
        verbose_name_plural = "الإبلاغات عن الرسائل"
        unique_together = ['message', 'reporter']
        indexes = [
            models.Index(fields=['is_reviewed', 'created_at']),
            models.Index(fields=['reason']),
        ]

    def __str__(self):
        reporter_name = self.reporter.get_full_name() or self.reporter.username
        return f"إبلاغ عن رسالة - {reporter_name} - {self.get_reason_display()}"
    
    def mark_as_reviewed(self, reviewed_by_user, action_taken=""):
        """تمييز الإبلاغ كمراجع"""
        self.is_reviewed = True
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewed_by_user
        self.action_taken = action_taken
        self.save()


class MessageStatistics(BaseModel):
    """نموذج إحصائيات الرسائل"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="المستخدم")
    date = models.DateField(verbose_name="التاريخ")
    
    # إحصائيات يومية
    messages_sent = models.PositiveIntegerField(default=0, verbose_name="الرسائل المرسلة")
    messages_received = models.PositiveIntegerField(default=0, verbose_name="الرسائل المستلمة")
    conversations_started = models.PositiveIntegerField(default=0, verbose_name="المحادثات المبدوءة")
    conversations_closed = models.PositiveIntegerField(default=0, verbose_name="المحادثات المغلقة")
    
    # متوسط وقت الرد (بالدقائق)
    avg_response_time = models.PositiveIntegerField(null=True, blank=True, verbose_name="متوسط وقت الرد")
    
    class Meta:
        verbose_name = "إحصائيات الرسائل"
        verbose_name_plural = "إحصائيات الرسائل"
        unique_together = ['user', 'date']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"إحصائيات {self.user.get_full_name()} - {self.date}"


class SystemNotification(BaseModel):
    """نموذج إشعارات النظام"""
    
    NOTIFICATION_TYPES = [
        ('new_message', 'رسالة جديدة'),
        ('conversation_closed', 'إغلاق محادثة'),
        ('system_update', 'تحديث النظام'),
        ('maintenance', 'صيانة'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        verbose_name="المستخدم"
    )
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name="نوع الإشعار")
    title = models.CharField(max_length=200, verbose_name="عنوان الإشعار")
    message = models.TextField(verbose_name="محتوى الإشعار")
    
    # معلومات إضافية
    related_object_id = models.UUIDField(null=True, blank=True, verbose_name="معرف الكائن المرتبط")
    action_url = models.URLField(blank=True, verbose_name="رابط الإجراء")
    
    # حالة الإشعار
    is_read = models.BooleanField(default=False, verbose_name="مقروء")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ القراءة")
    
    class Meta:
        verbose_name = "إشعار النظام"
        verbose_name_plural = "إشعارات النظام"
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def mark_as_read(self):
        """تحديد الإشعار كمقروء"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
