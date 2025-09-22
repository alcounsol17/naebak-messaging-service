"""
اختبارات النماذج لخدمة الرسائل - منصة نائبك.كوم
"""

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta

from messages.models import (
    UserProfile, Conversation, Message, MessageReport,
    MessageStatistics, SystemNotification
)


@pytest.mark.django_db
class TestUserProfile:
    """اختبارات نموذج UserProfile"""
    
    def test_create_citizen_profile(self, user):
        """اختبار إنشاء ملف مواطن"""
        profile = UserProfile.objects.create(
            user=user,
            user_type='citizen',
            phone='01234567890',
            governorate='القاهرة',
            district='مصر الجديدة'
        )
        
        assert profile.user == user
        assert profile.user_type == 'citizen'
        assert profile.phone == '01234567890'
        assert profile.governorate == 'القاهرة'
        assert profile.district == 'مصر الجديدة'
        assert profile.email_notifications is True
        assert profile.sms_notifications is True
        assert str(profile) == f"{user.get_full_name() or user.username} - مواطن"
    
    def test_create_representative_profile(self, user):
        """اختبار إنشاء ملف نائب"""
        profile = UserProfile.objects.create(
            user=user,
            user_type='representative',
            representative_id=123,
            phone='01234567890',
            governorate='الجيزة',
            district='الدقي'
        )
        
        assert profile.user_type == 'representative'
        assert profile.representative_id == 123
        assert str(profile) == f"{user.get_full_name() or user.username} - نائب"
    
    def test_unique_user_constraint(self, user):
        """اختبار قيد الفريدة للمستخدم"""
        UserProfile.objects.create(user=user, user_type='citizen')
        
        with pytest.raises(IntegrityError):
            UserProfile.objects.create(user=user, user_type='representative')
    
    def test_phone_validation(self, user):
        """اختبار التحقق من رقم الهاتف"""
        # رقم صحيح
        profile = UserProfile(
            user=user,
            user_type='citizen',
            phone='01234567890'
        )
        profile.clean()  # لا يجب أن يثير خطأ
        
        # رقم خاطئ
        profile.phone = '123'
        with pytest.raises(ValidationError):
            profile.clean()


@pytest.mark.django_db
class TestConversation:
    """اختبارات نموذج Conversation"""
    
    def test_create_conversation(self, citizen_user, representative_user):
        """اختبار إنشاء محادثة"""
        conversation = Conversation.objects.create(
            citizen=citizen_user,
            representative=representative_user,
            subject='استفسار عن الخدمات'
        )
        
        assert conversation.citizen == citizen_user
        assert conversation.representative == representative_user
        assert conversation.subject == 'استفسار عن الخدمات'
        assert conversation.is_closed is False
        assert conversation.total_messages == 0
        assert conversation.citizen_rating is None
        assert str(conversation) == 'استفسار عن الخدمات'
    
    def test_conversation_str_with_long_subject(self, citizen_user, representative_user):
        """اختبار عرض المحادثة مع موضوع طويل"""
        long_subject = 'هذا موضوع طويل جداً يحتوي على أكثر من خمسين حرف لاختبار قطع النص'
        conversation = Conversation.objects.create(
            citizen=citizen_user,
            representative=representative_user,
            subject=long_subject
        )
        
        assert str(conversation) == long_subject[:50] + "..."
    
    def test_close_conversation(self, conversation, citizen_user):
        """اختبار إغلاق المحادثة"""
        conversation.close(closed_by=citizen_user)
        
        assert conversation.is_closed is True
        assert conversation.closed_by == citizen_user
        assert conversation.closed_at is not None
    
    def test_update_last_message(self, conversation, citizen_user):
        """اختبار تحديث آخر رسالة"""
        message = Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='رسالة تجريبية'
        )
        
        conversation.update_last_message(message)
        conversation.refresh_from_db()
        
        assert conversation.last_message_at == message.created_at
        assert conversation.last_message_by == citizen_user
        assert conversation.total_messages == 1


@pytest.mark.django_db
class TestMessage:
    """اختبارات نموذج Message"""
    
    def test_create_message(self, conversation, citizen_user):
        """اختبار إنشاء رسالة"""
        message = Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='مرحباً، أريد استفسار'
        )
        
        assert message.conversation == conversation
        assert message.sender == citizen_user
        assert message.content == 'مرحباً، أريد استفسار'
        assert message.is_read is False
        assert message.is_system_message is False
        assert message.read_at is None
        assert str(message) == f"رسالة من {citizen_user.get_full_name() or citizen_user.username}"
    
    def test_mark_as_read(self, message):
        """اختبار تحديد الرسالة كمقروءة"""
        message.mark_as_read()
        
        assert message.is_read is True
        assert message.read_at is not None
    
    def test_system_message(self, conversation, citizen_user):
        """اختبار رسالة النظام"""
        message = Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='تم إغلاق المحادثة',
            is_system_message=True
        )
        
        assert message.is_system_message is True
        assert str(message) == "رسالة نظام"
    
    def test_reply_to_message(self, conversation, citizen_user, representative_user):
        """اختبار الرد على رسالة"""
        original_message = Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='سؤال'
        )
        
        reply = Message.objects.create(
            conversation=conversation,
            sender=representative_user,
            content='جواب',
            reply_to=original_message
        )
        
        assert reply.reply_to == original_message
        assert reply.conversation == conversation


@pytest.mark.django_db
class TestMessageReport:
    """اختبارات نموذج MessageReport"""
    
    def test_create_report(self, message, representative_user):
        """اختبار إنشاء إبلاغ"""
        report = MessageReport.objects.create(
            message=message,
            reporter=representative_user,
            reason='spam',
            description='رسالة مزعجة'
        )
        
        assert report.message == message
        assert report.reporter == representative_user
        assert report.reason == 'spam'
        assert report.description == 'رسالة مزعجة'
        assert report.is_reviewed is False
        assert str(report) == f"إبلاغ عن رسالة من {message.sender.get_full_name() or message.sender.username}"
    
    def test_mark_as_reviewed(self, message, representative_user, user):
        """اختبار تحديد الإبلاغ كمراجع"""
        report = MessageReport.objects.create(
            message=message,
            reporter=representative_user,
            reason='inappropriate'
        )
        
        report.mark_as_reviewed(reviewed_by=user, action_taken='تم حذف الرسالة')
        
        assert report.is_reviewed is True
        assert report.reviewed_by == user
        assert report.reviewed_at is not None
        assert report.action_taken == 'تم حذف الرسالة'


@pytest.mark.django_db
class TestMessageStatistics:
    """اختبارات نموذج MessageStatistics"""
    
    def test_create_statistics(self, user):
        """اختبار إنشاء إحصائيات"""
        today = timezone.now().date()
        stats = MessageStatistics.objects.create(
            user=user,
            date=today,
            messages_sent=5,
            messages_received=3,
            conversations_started=2,
            conversations_closed=1,
            avg_response_time=30.5
        )
        
        assert stats.user == user
        assert stats.date == today
        assert stats.messages_sent == 5
        assert stats.messages_received == 3
        assert stats.conversations_started == 2
        assert stats.conversations_closed == 1
        assert stats.avg_response_time == 30.5
        assert str(stats) == f"إحصائيات {user.get_full_name() or user.username} - {today}"
    
    def test_unique_user_date_constraint(self, user):
        """اختبار قيد الفريدة للمستخدم والتاريخ"""
        today = timezone.now().date()
        MessageStatistics.objects.create(user=user, date=today)
        
        with pytest.raises(IntegrityError):
            MessageStatistics.objects.create(user=user, date=today)


@pytest.mark.django_db
class TestSystemNotification:
    """اختبارات نموذج SystemNotification"""
    
    def test_create_notification(self, user):
        """اختبار إنشاء إشعار"""
        notification = SystemNotification.objects.create(
            user=user,
            notification_type='message',
            title='رسالة جديدة',
            message='لديك رسالة جديدة من النائب'
        )
        
        assert notification.user == user
        assert notification.notification_type == 'message'
        assert notification.title == 'رسالة جديدة'
        assert notification.message == 'لديك رسالة جديدة من النائب'
        assert notification.is_read is False
        assert str(notification) == 'رسالة جديدة'
    
    def test_mark_as_read(self, user):
        """اختبار تحديد الإشعار كمقروء"""
        notification = SystemNotification.objects.create(
            user=user,
            notification_type='system',
            title='إشعار النظام'
        )
        
        notification.mark_as_read()
        
        assert notification.is_read is True
        assert notification.read_at is not None
    
    def test_notification_with_action_url(self, user):
        """اختبار إشعار مع رابط إجراء"""
        notification = SystemNotification.objects.create(
            user=user,
            notification_type='conversation',
            title='محادثة جديدة',
            action_url='/conversations/123/'
        )
        
        assert notification.action_url == '/conversations/123/'
