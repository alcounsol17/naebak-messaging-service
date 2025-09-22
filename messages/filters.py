"""
Filters لخدمة الرسائل - منصة نائبك.كوم
"""

import django_filters
from django.db.models import Q
from django.contrib.auth.models import User
from .models import Conversation, Message, MessageReport, SystemNotification


class ConversationFilter(django_filters.FilterSet):
    """فلاتر المحادثات"""
    
    # فلترة حسب الحالة
    is_closed = django_filters.BooleanFilter()
    
    # فلترة حسب التاريخ
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    last_message_after = django_filters.DateTimeFilter(field_name='last_message_at', lookup_expr='gte')
    last_message_before = django_filters.DateTimeFilter(field_name='last_message_at', lookup_expr='lte')
    
    # فلترة حسب التقييم
    rating = django_filters.NumberFilter(field_name='citizen_rating')
    rating_min = django_filters.NumberFilter(field_name='citizen_rating', lookup_expr='gte')
    rating_max = django_filters.NumberFilter(field_name='citizen_rating', lookup_expr='lte')
    
    # فلترة حسب عدد الرسائل
    messages_count_min = django_filters.NumberFilter(field_name='total_messages', lookup_expr='gte')
    messages_count_max = django_filters.NumberFilter(field_name='total_messages', lookup_expr='lte')
    
    # فلترة حسب المحافظة (للنواب)
    governorate = django_filters.CharFilter(
        field_name='representative__userprofile__governorate',
        lookup_expr='icontains'
    )
    
    # فلترة حسب الدائرة الانتخابية
    district = django_filters.CharFilter(
        field_name='representative__userprofile__district',
        lookup_expr='icontains'
    )
    
    # بحث في موضوع المحادثة
    search = django_filters.CharFilter(method='filter_search')
    
    # فلترة المحادثات التي تحتوي على رسائل غير مقروءة
    has_unread = django_filters.BooleanFilter(method='filter_has_unread')
    
    class Meta:
        model = Conversation
        fields = [
            'is_closed', 'citizen_rating', 'created_after', 'created_before',
            'last_message_after', 'last_message_before', 'rating', 'rating_min', 'rating_max',
            'messages_count_min', 'messages_count_max', 'governorate', 'district',
            'search', 'has_unread'
        ]
    
    def filter_search(self, queryset, name, value):
        """البحث في موضوع المحادثة وأسماء المشاركين"""
        return queryset.filter(
            Q(subject__icontains=value) |
            Q(citizen__first_name__icontains=value) |
            Q(citizen__last_name__icontains=value) |
            Q(representative__first_name__icontains=value) |
            Q(representative__last_name__icontains=value)
        )
    
    def filter_has_unread(self, queryset, name, value):
        """فلترة المحادثات التي تحتوي على رسائل غير مقروءة"""
        user = self.request.user
        if value:
            if hasattr(user, 'userprofile') and user.userprofile.user_type == 'citizen':
                return queryset.filter(
                    messages__sender=F('representative'),
                    messages__is_read=False
                ).distinct()
            elif hasattr(user, 'userprofile') and user.userprofile.user_type == 'representative':
                return queryset.filter(
                    messages__sender=F('citizen'),
                    messages__is_read=False
                ).distinct()
        return queryset


class MessageFilter(django_filters.FilterSet):
    """فلاتر الرسائل"""
    
    # فلترة حسب المحادثة
    conversation = django_filters.UUIDFilter()
    
    # فلترة حسب المرسل
    sender = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    
    # فلترة حسب حالة القراءة
    is_read = django_filters.BooleanFilter()
    
    # فلترة حسب نوع الرسالة
    is_system_message = django_filters.BooleanFilter()
    
    # فلترة حسب التاريخ
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    read_after = django_filters.DateTimeFilter(field_name='read_at', lookup_expr='gte')
    read_before = django_filters.DateTimeFilter(field_name='read_at', lookup_expr='lte')
    
    # بحث في محتوى الرسالة
    search = django_filters.CharFilter(field_name='content', lookup_expr='icontains')
    
    # فلترة الرسائل من المواطنين أو النواب
    from_citizens = django_filters.BooleanFilter(method='filter_from_citizens')
    from_representatives = django_filters.BooleanFilter(method='filter_from_representatives')
    
    class Meta:
        model = Message
        fields = [
            'conversation', 'sender', 'is_read', 'is_system_message',
            'created_after', 'created_before', 'read_after', 'read_before',
            'search', 'from_citizens', 'from_representatives'
        ]
    
    def filter_from_citizens(self, queryset, name, value):
        """فلترة الرسائل من المواطنين"""
        if value:
            return queryset.filter(sender__userprofile__user_type='citizen')
        return queryset
    
    def filter_from_representatives(self, queryset, name, value):
        """فلترة الرسائل من النواب"""
        if value:
            return queryset.filter(sender__userprofile__user_type='representative')
        return queryset


class MessageReportFilter(django_filters.FilterSet):
    """فلاتر الإبلاغات"""
    
    # فلترة حسب سبب الإبلاغ
    reason = django_filters.ChoiceFilter(choices=MessageReport.REPORT_REASONS)
    
    # فلترة حسب حالة المراجعة
    is_reviewed = django_filters.BooleanFilter()
    
    # فلترة حسب المبلغ
    reporter = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    
    # فلترة حسب التاريخ
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    reviewed_after = django_filters.DateTimeFilter(field_name='reviewed_at', lookup_expr='gte')
    reviewed_before = django_filters.DateTimeFilter(field_name='reviewed_at', lookup_expr='lte')
    
    # بحث في وصف الإبلاغ
    search = django_filters.CharFilter(field_name='description', lookup_expr='icontains')
    
    class Meta:
        model = MessageReport
        fields = [
            'reason', 'is_reviewed', 'reporter', 'created_after', 'created_before',
            'reviewed_after', 'reviewed_before', 'search'
        ]


class SystemNotificationFilter(django_filters.FilterSet):
    """فلاتر إشعارات النظام"""
    
    # فلترة حسب نوع الإشعار
    notification_type = django_filters.ChoiceFilter(choices=SystemNotification.NOTIFICATION_TYPES)
    
    # فلترة حسب حالة القراءة
    is_read = django_filters.BooleanFilter()
    
    # فلترة حسب التاريخ
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    read_after = django_filters.DateTimeFilter(field_name='read_at', lookup_expr='gte')
    read_before = django_filters.DateTimeFilter(field_name='read_at', lookup_expr='lte')
    
    # بحث في العنوان والمحتوى
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = SystemNotification
        fields = [
            'notification_type', 'is_read', 'created_after', 'created_before',
            'read_after', 'read_before', 'search'
        ]
    
    def filter_search(self, queryset, name, value):
        """البحث في عنوان ومحتوى الإشعار"""
        return queryset.filter(
            Q(title__icontains=value) |
            Q(message__icontains=value)
        )
