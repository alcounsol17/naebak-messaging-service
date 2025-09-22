"""
إعدادات لوحة الإدارة لخدمة الرسائل - منصة نائبك.كوم
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    UserProfile, Conversation, Message, MessageReport,
    MessageStatistics, SystemNotification
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """إدارة ملفات المستخدمين"""
    
    list_display = [
        'user', 'user_type', 'phone', 'governorate', 'district',
        'email_notifications', 'sms_notifications', 'created_at'
    ]
    list_filter = [
        'user_type', 'governorate', 'email_notifications', 
        'sms_notifications', 'created_at'
    ]
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name',
        'user__email', 'phone', 'district', 'governorate'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('معلومات المستخدم', {
            'fields': ('user', 'user_type', 'phone')
        }),
        ('معلومات النائب', {
            'fields': ('representative_id', 'district', 'governorate'),
            'classes': ('collapse',)
        }),
        ('إعدادات الإشعارات', {
            'fields': ('email_notifications', 'sms_notifications')
        }),
        ('الصورة الشخصية', {
            'fields': ('avatar',)
        }),
        ('معلومات النظام', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


class MessageInline(admin.TabularInline):
    """عرض الرسائل داخل المحادثة"""
    model = Message
    extra = 0
    readonly_fields = ['sender', 'created_at', 'is_read', 'read_at']
    fields = ['sender', 'content', 'is_read', 'is_system_message', 'created_at']
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """إدارة المحادثات"""
    
    list_display = [
        'subject', 'citizen', 'representative', 'total_messages',
        'is_closed', 'citizen_rating', 'last_message_at', 'created_at'
    ]
    list_filter = [
        'is_closed', 'citizen_rating', 'created_at', 'last_message_at',
        'representative__userprofile__governorate'
    ]
    search_fields = [
        'subject', 'citizen__first_name', 'citizen__last_name',
        'representative__first_name', 'representative__last_name'
    ]
    readonly_fields = [
        'id', 'total_messages', 'last_message_at', 'last_message_by',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('معلومات المحادثة', {
            'fields': ('citizen', 'representative', 'subject')
        }),
        ('إحصائيات', {
            'fields': ('total_messages', 'last_message_at', 'last_message_by')
        }),
        ('حالة المحادثة', {
            'fields': ('is_closed', 'closed_at', 'closed_by')
        }),
        ('التقييم', {
            'fields': ('citizen_rating', 'citizen_feedback')
        }),
        ('معلومات النظام', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [MessageInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'citizen', 'representative', 'last_message_by'
        )
    
    actions = ['close_conversations', 'open_conversations']
    
    def close_conversations(self, request, queryset):
        """إغلاق المحادثات المحددة"""
        updated = queryset.filter(is_closed=False).update(
            is_closed=True,
            closed_by=request.user
        )
        self.message_user(request, f'تم إغلاق {updated} محادثة')
    close_conversations.short_description = 'إغلاق المحادثات المحددة'
    
    def open_conversations(self, request, queryset):
        """فتح المحادثات المحددة"""
        updated = queryset.filter(is_closed=True).update(
            is_closed=False,
            closed_at=None,
            closed_by=None
        )
        self.message_user(request, f'تم فتح {updated} محادثة')
    open_conversations.short_description = 'فتح المحادثات المحددة'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """إدارة الرسائل"""
    
    list_display = [
        'conversation_link', 'sender', 'content_preview', 
        'is_read', 'is_system_message', 'created_at'
    ]
    list_filter = [
        'is_read', 'is_system_message', 'created_at',
        'sender__userprofile__user_type'
    ]
    search_fields = [
        'content', 'sender__first_name', 'sender__last_name',
        'conversation__subject'
    ]
    readonly_fields = [
        'id', 'conversation', 'sender', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('معلومات الرسالة', {
            'fields': ('conversation', 'sender', 'content')
        }),
        ('حالة الرسالة', {
            'fields': ('is_read', 'read_at', 'is_system_message')
        }),
        ('الرد', {
            'fields': ('reply_to',)
        }),
        ('معلومات النظام', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def conversation_link(self, obj):
        """رابط للمحادثة"""
        url = reverse('admin:naebak_messages_conversation_change', args=[obj.conversation.id])
        return format_html('<a href="{}">{}</a>', url, obj.conversation.subject)
    conversation_link.short_description = 'المحادثة'
    
    def content_preview(self, obj):
        """معاينة محتوى الرسالة"""
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'المحتوى'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'conversation', 'sender', 'reply_to'
        )
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        """تحديد الرسائل كمقروءة"""
        updated = queryset.filter(is_read=False).update(is_read=True)
        self.message_user(request, f'تم تحديد {updated} رسالة كمقروءة')
    mark_as_read.short_description = 'تحديد كمقروءة'
    
    def mark_as_unread(self, request, queryset):
        """تحديد الرسائل كغير مقروءة"""
        updated = queryset.filter(is_read=True).update(is_read=False, read_at=None)
        self.message_user(request, f'تم تحديد {updated} رسالة كغير مقروءة')
    mark_as_unread.short_description = 'تحديد كغير مقروءة'


@admin.register(MessageReport)
class MessageReportAdmin(admin.ModelAdmin):
    """إدارة الإبلاغات"""
    
    list_display = [
        'message_link', 'reporter', 'reason', 'is_reviewed',
        'reviewed_by', 'created_at'
    ]
    list_filter = [
        'reason', 'is_reviewed', 'created_at', 'reviewed_at'
    ]
    search_fields = [
        'description', 'reporter__first_name', 'reporter__last_name',
        'message__content'
    ]
    readonly_fields = [
        'id', 'message', 'reporter', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('معلومات الإبلاغ', {
            'fields': ('message', 'reporter', 'reason', 'description')
        }),
        ('المراجعة', {
            'fields': ('is_reviewed', 'reviewed_at', 'reviewed_by', 'action_taken')
        }),
        ('معلومات النظام', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def message_link(self, obj):
        """رابط للرسالة المبلغ عنها"""
        url = reverse('admin:naebak_messages_message_change', args=[obj.message.id])
        content_preview = obj.message.content[:30] + "..." if len(obj.message.content) > 30 else obj.message.content
        return format_html('<a href="{}">{}</a>', url, content_preview)
    message_link.short_description = 'الرسالة'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'message', 'reporter', 'reviewed_by'
        )
    
    actions = ['mark_as_reviewed']
    
    def mark_as_reviewed(self, request, queryset):
        """تحديد الإبلاغات كمراجعة"""
        from django.utils import timezone
        updated = queryset.filter(is_reviewed=False).update(
            is_reviewed=True,
            reviewed_at=timezone.now(),
            reviewed_by=request.user
        )
        self.message_user(request, f'تم مراجعة {updated} إبلاغ')
    mark_as_reviewed.short_description = 'تحديد كمراجع'


@admin.register(MessageStatistics)
class MessageStatisticsAdmin(admin.ModelAdmin):
    """إدارة إحصائيات الرسائل"""
    
    list_display = [
        'user', 'date', 'messages_sent', 'messages_received',
        'conversations_started', 'conversations_closed', 'avg_response_time'
    ]
    list_filter = ['date', 'user__userprofile__user_type']
    search_fields = ['user__first_name', 'user__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    """إدارة إشعارات النظام"""
    
    list_display = [
        'title', 'user', 'notification_type', 'is_read', 'created_at'
    ]
    list_filter = [
        'notification_type', 'is_read', 'created_at'
    ]
    search_fields = [
        'title', 'message', 'user__first_name', 'user__last_name'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('معلومات الإشعار', {
            'fields': ('user', 'notification_type', 'title', 'message')
        }),
        ('معلومات إضافية', {
            'fields': ('related_object_id', 'action_url')
        }),
        ('حالة القراءة', {
            'fields': ('is_read', 'read_at')
        }),
        ('معلومات النظام', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        """تحديد الإشعارات كمقروءة"""
        from django.utils import timezone
        updated = queryset.filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        self.message_user(request, f'تم تحديد {updated} إشعار كمقروء')
    mark_as_read.short_description = 'تحديد كمقروء'
    
    def mark_as_unread(self, request, queryset):
        """تحديد الإشعارات كغير مقروءة"""
        updated = queryset.filter(is_read=True).update(is_read=False, read_at=None)
        self.message_user(request, f'تم تحديد {updated} إشعار كغير مقروء')
    mark_as_unread.short_description = 'تحديد كغير مقروء'


# تخصيص لوحة الإدارة
admin.site.site_header = "إدارة خدمة الرسائل - منصة نائبك.كوم"
admin.site.site_title = "خدمة الرسائل"
admin.site.index_title = "مرحباً بك في لوحة إدارة خدمة الرسائل"
