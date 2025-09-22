"""
اختبارات Serializers لخدمة الرسائل - منصة نائبك.كوم
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError

from messages.models import UserProfile, Conversation, Message, MessageReport, SystemNotification
from messages.serializers import (
    UserProfileSerializer, UserProfileCreateSerializer,
    ConversationSerializer, ConversationCreateSerializer, ConversationDetailSerializer,
    MessageSerializer, MessageCreateSerializer,
    MessageReportSerializer, SystemNotificationSerializer,
    UserStatsSerializer, ConversationStatsSerializer
)


@pytest.mark.django_db
class TestUserProfileSerializer:
    """اختبارات UserProfile Serializer"""
    
    def test_serialize_user_profile(self, citizen_user):
        """اختبار تسلسل ملف المستخدم"""
        profile = UserProfile.objects.create(
            user=citizen_user,
            user_type='citizen',
            phone='01234567890',
            governorate='القاهرة',
            district='مصر الجديدة'
        )
        
        serializer = UserProfileSerializer(profile)
        data = serializer.data
        
        assert data['user_type'] == 'citizen'
        assert data['phone'] == '01234567890'
        assert data['governorate'] == 'القاهرة'
        assert data['district'] == 'مصر الجديدة'
        assert data['email_notifications'] is True
        assert data['sms_notifications'] is True
        assert 'user' in data
        assert 'created_at' in data
    
    def test_create_user_profile(self, user):
        """اختبار إنشاء ملف مستخدم"""
        data = {
            'user_id': user.id,
            'user_type': 'citizen',
            'phone': '01234567890',
            'governorate': 'الجيزة',
            'district': 'الدقي',
            'email_notifications': False
        }
        
        serializer = UserProfileCreateSerializer(data=data)
        assert serializer.is_valid()
        
        profile = serializer.save()
        assert profile.user == user
        assert profile.user_type == 'citizen'
        assert profile.phone == '01234567890'
        assert profile.email_notifications is False
    
    def test_invalid_user_type(self, user):
        """اختبار نوع مستخدم غير صحيح"""
        data = {
            'user_id': user.id,
            'user_type': 'invalid_type',
            'phone': '01234567890'
        }
        
        serializer = UserProfileCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'user_type' in serializer.errors
    
    def test_invalid_phone_format(self, user):
        """اختبار تنسيق هاتف غير صحيح"""
        data = {
            'user_id': user.id,
            'user_type': 'citizen',
            'phone': '123'  # رقم قصير جداً
        }
        
        serializer = UserProfileCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'phone' in serializer.errors


@pytest.mark.django_db
class TestConversationSerializer:
    """اختبارات Conversation Serializer"""
    
    def test_serialize_conversation(self, conversation):
        """اختبار تسلسل المحادثة"""
        serializer = ConversationSerializer(conversation)
        data = serializer.data
        
        assert data['subject'] == conversation.subject
        assert data['is_closed'] == conversation.is_closed
        assert data['total_messages'] == conversation.total_messages
        assert 'citizen' in data
        assert 'representative' in data
        assert 'created_at' in data
    
    def test_serialize_conversation_detail(self, conversation, citizen_user):
        """اختبار تسلسل تفاصيل المحادثة"""
        # إضافة رسائل للمحادثة
        Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='رسالة تجريبية'
        )
        
        serializer = ConversationDetailSerializer(conversation)
        data = serializer.data
        
        assert 'messages' in data
        assert len(data['messages']) == 1
        assert data['messages'][0]['content'] == 'رسالة تجريبية'
    
    def test_create_conversation(self, citizen_user, representative_user):
        """اختبار إنشاء محادثة"""
        data = {
            'citizen': citizen_user.id,
            'representative': representative_user.id,
            'subject': 'محادثة جديدة'
        }
        
        serializer = ConversationCreateSerializer(data=data)
        assert serializer.is_valid()
        
        conversation = serializer.save()
        assert conversation.citizen == citizen_user
        assert conversation.representative == representative_user
        assert conversation.subject == 'محادثة جديدة'
        assert conversation.is_closed is False
    
    def test_create_conversation_missing_subject(self, citizen_user, representative_user):
        """اختبار إنشاء محادثة بدون موضوع"""
        data = {
            'citizen': citizen_user.id,
            'representative': representative_user.id
        }
        
        serializer = ConversationCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'subject' in serializer.errors
    
    def test_create_conversation_same_users(self, citizen_user):
        """اختبار إنشاء محادثة بين نفس المستخدم"""
        data = {
            'citizen': citizen_user.id,
            'representative': citizen_user.id,
            'subject': 'محادثة خاطئة'
        }
        
        serializer = ConversationCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors


@pytest.mark.django_db
class TestMessageSerializer:
    """اختبارات Message Serializer"""
    
    def test_serialize_message(self, message):
        """اختبار تسلسل الرسالة"""
        serializer = MessageSerializer(message)
        data = serializer.data
        
        assert data['content'] == message.content
        assert data['is_read'] == message.is_read
        assert data['is_system_message'] == message.is_system_message
        assert 'sender' in data
        assert 'conversation' in data
        assert 'created_at' in data
    
    def test_create_message(self, conversation, citizen_user):
        """اختبار إنشاء رسالة"""
        data = {
            'conversation': conversation.id,
            'sender': citizen_user.id,
            'content': 'رسالة جديدة'
        }
        
        serializer = MessageCreateSerializer(data=data)
        assert serializer.is_valid()
        
        message = serializer.save()
        assert message.conversation == conversation
        assert message.sender == citizen_user
        assert message.content == 'رسالة جديدة'
        assert message.is_read is False
    
    def test_create_empty_message(self, conversation, citizen_user):
        """اختبار إنشاء رسالة فارغة"""
        data = {
            'conversation': conversation.id,
            'sender': citizen_user.id,
            'content': ''
        }
        
        serializer = MessageCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'content' in serializer.errors
    
    def test_create_message_with_reply(self, conversation, citizen_user, representative_user):
        """اختبار إنشاء رسالة رد"""
        original_message = Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='رسالة أصلية'
        )
        
        data = {
            'conversation': conversation.id,
            'sender': representative_user.id,
            'content': 'رد على الرسالة',
            'reply_to': original_message.id
        }
        
        serializer = MessageCreateSerializer(data=data)
        assert serializer.is_valid()
        
        message = serializer.save()
        assert message.reply_to == original_message
        assert message.content == 'رد على الرسالة'


@pytest.mark.django_db
class TestMessageReportSerializer:
    """اختبارات MessageReport Serializer"""
    
    def test_serialize_message_report(self, message, representative_user):
        """اختبار تسلسل الإبلاغ"""
        report = MessageReport.objects.create(
            message=message,
            reporter=representative_user,
            reason='spam',
            description='رسالة مزعجة'
        )
        
        serializer = MessageReportSerializer(report)
        data = serializer.data
        
        assert data['reason'] == 'spam'
        assert data['description'] == 'رسالة مزعجة'
        assert data['is_reviewed'] is False
        assert 'message' in data
        assert 'reporter' in data
        assert 'created_at' in data
    
    def test_create_message_report(self, message, representative_user):
        """اختبار إنشاء إبلاغ"""
        data = {
            'message': message.id,
            'reporter': representative_user.id,
            'reason': 'inappropriate',
            'description': 'محتوى غير مناسب'
        }
        
        serializer = MessageReportSerializer(data=data)
        assert serializer.is_valid()
        
        report = serializer.save()
        assert report.message == message
        assert report.reporter == representative_user
        assert report.reason == 'inappropriate'
        assert report.description == 'محتوى غير مناسب'
    
    def test_create_report_missing_reason(self, message, representative_user):
        """اختبار إنشاء إبلاغ بدون سبب"""
        data = {
            'message': message.id,
            'reporter': representative_user.id,
            'description': 'وصف بدون سبب'
        }
        
        serializer = MessageReportSerializer(data=data)
        assert not serializer.is_valid()
        assert 'reason' in serializer.errors


@pytest.mark.django_db
class TestSystemNotificationSerializer:
    """اختبارات SystemNotification Serializer"""
    
    def test_serialize_notification(self, citizen_user):
        """اختبار تسلسل الإشعار"""
        notification = SystemNotification.objects.create(
            user=citizen_user,
            notification_type='message',
            title='رسالة جديدة',
            message='لديك رسالة جديدة من النائب',
            action_url='/conversations/123/'
        )
        
        serializer = SystemNotificationSerializer(notification)
        data = serializer.data
        
        assert data['notification_type'] == 'message'
        assert data['title'] == 'رسالة جديدة'
        assert data['message'] == 'لديك رسالة جديدة من النائب'
        assert data['action_url'] == '/conversations/123/'
        assert data['is_read'] is False
        assert 'user' in data
        assert 'created_at' in data


@pytest.mark.django_db
class TestStatsSerializers:
    """اختبارات Stats Serializers"""
    
    def test_user_stats_serializer(self):
        """اختبار UserStats Serializer"""
        stats_data = {
            'total_conversations': 10,
            'active_conversations': 5,
            'total_messages_sent': 50,
            'total_messages_received': 45,
            'unread_messages': 3,
            'avg_response_time': 120.5,
            'conversations_this_month': 8,
            'messages_this_month': 35
        }
        
        serializer = UserStatsSerializer(stats_data)
        data = serializer.data
        
        assert data['total_conversations'] == 10
        assert data['active_conversations'] == 5
        assert data['total_messages_sent'] == 50
        assert data['total_messages_received'] == 45
        assert data['unread_messages'] == 3
        assert data['avg_response_time'] == 120.5
        assert data['conversations_this_month'] == 8
        assert data['messages_this_month'] == 35
    
    def test_conversation_stats_serializer(self):
        """اختبار ConversationStats Serializer"""
        stats_data = {
            'total_conversations': 25,
            'active_conversations': 12,
            'closed_conversations': 13,
            'conversations_today': 2,
            'conversations_this_week': 8,
            'conversations_this_month': 15,
            'avg_messages_per_conversation': 4.2,
            'avg_conversation_duration': 2.5
        }
        
        serializer = ConversationStatsSerializer(stats_data)
        data = serializer.data
        
        assert data['total_conversations'] == 25
        assert data['active_conversations'] == 12
        assert data['closed_conversations'] == 13
        assert data['conversations_today'] == 2
        assert data['conversations_this_week'] == 8
        assert data['conversations_this_month'] == 15
        assert data['avg_messages_per_conversation'] == 4.2
        assert data['avg_conversation_duration'] == 2.5


@pytest.mark.django_db
class TestSerializerValidation:
    """اختبارات التحقق من صحة البيانات"""
    
    def test_phone_number_validation(self, user):
        """اختبار التحقق من رقم الهاتف"""
        # رقم صحيح
        data = {
            'user_id': user.id,
            'user_type': 'citizen',
            'phone': '01234567890'
        }
        serializer = UserProfileCreateSerializer(data=data)
        assert serializer.is_valid()
        
        # رقم قصير
        data['phone'] = '123'
        serializer = UserProfileCreateSerializer(data=data)
        assert not serializer.is_valid()
        
        # رقم طويل جداً
        data['phone'] = '012345678901234567890'
        serializer = UserProfileCreateSerializer(data=data)
        assert not serializer.is_valid()
    
    def test_message_content_validation(self, conversation, citizen_user):
        """اختبار التحقق من محتوى الرسالة"""
        # محتوى صحيح
        data = {
            'conversation': conversation.id,
            'sender': citizen_user.id,
            'content': 'رسالة صحيحة'
        }
        serializer = MessageCreateSerializer(data=data)
        assert serializer.is_valid()
        
        # محتوى فارغ
        data['content'] = ''
        serializer = MessageCreateSerializer(data=data)
        assert not serializer.is_valid()
        
        # محتوى مسافات فقط
        data['content'] = '   '
        serializer = MessageCreateSerializer(data=data)
        assert not serializer.is_valid()
    
    def test_conversation_subject_validation(self, citizen_user, representative_user):
        """اختبار التحقق من موضوع المحادثة"""
        # موضوع صحيح
        data = {
            'representative_id': representative_user.id,
            'subject': 'موضوع صحيح',
            'first_message': 'رسالة أولى'
        }
        serializer = ConversationCreateSerializer(data=data)
        assert serializer.is_valid()
        
        # موضوع فارغ
        data['subject'] = ''
        data['first_message'] = 'رسالة أولى'
        serializer = ConversationCreateSerializer(data=data)
        assert not serializer.is_valid()
        
        # موضوع طويل جداً
        data['subject'] = 'موضوع طويل جداً ' * 50
        data['first_message'] = 'رسالة أولى'
        serializer = ConversationCreateSerializer(data=data)
        assert not serializer.is_valid()
