"""
اختبارات APIs لخدمة الرسائل - منصة نائبك.كوم
"""

import pytest
from django.urls import reverse
from rest_framework import status
from django.contrib.auth.models import User

from messages.models import UserProfile, Conversation, Message, MessageReport, SystemNotification


@pytest.mark.django_db
class TestUserProfileAPI:
    """اختبارات API ملفات المستخدمين"""
    
    def test_create_profile(self, authenticated_client, citizen_user):
        """اختبار إنشاء ملف مستخدم"""
        url = reverse('userprofile-create-profile')
        data = {
            'user_type': 'citizen',
            'phone': '01234567890',
            'governorate': 'القاهرة',
            'district': 'مصر الجديدة'
        }
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert UserProfile.objects.filter(user=citizen_user).exists()
    
    def test_get_my_profile(self, authenticated_client, citizen_user):
        """اختبار الحصول على ملف المستخدم الحالي"""
        profile = UserProfile.objects.create(
            user=citizen_user,
            user_type='citizen',
            phone='01234567890'
        )
        
        url = reverse('userprofile-me')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['user_type'] == 'citizen'
        assert response.data['phone'] == '01234567890'
    
    def test_get_profile_not_found(self, authenticated_client):
        """اختبار عدم وجود ملف المستخدم"""
        url = reverse('userprofile-me')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_unauthorized_access(self, api_client):
        """اختبار الوصول غير المصرح به"""
        url = reverse('userprofile-me')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestConversationAPI:
    """اختبارات API المحادثات"""
    
    def test_create_conversation(self, authenticated_client, citizen_user, representative_user):
        """اختبار إنشاء محادثة جديدة"""
        url = reverse('conversation-list')
        data = {
            'representative': representative_user.id,
            'subject': 'استفسار عن الخدمات'
        }
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Conversation.objects.filter(
            citizen=citizen_user,
            representative=representative_user,
            subject='استفسار عن الخدمات'
        ).exists()
    
    def test_list_my_conversations(self, authenticated_client, citizen_user, representative_user):
        """اختبار قائمة محادثات المستخدم"""
        conversation = Conversation.objects.create(
            citizen=citizen_user,
            representative=representative_user,
            subject='محادثة تجريبية'
        )
        
        url = reverse('conversation-my-conversations')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['subject'] == 'محادثة تجريبية'
    
    def test_close_conversation(self, authenticated_client, citizen_user, representative_user):
        """اختبار إغلاق محادثة"""
        conversation = Conversation.objects.create(
            citizen=citizen_user,
            representative=representative_user,
            subject='محادثة للإغلاق'
        )
        
        url = reverse('conversation-close', kwargs={'pk': conversation.id})
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        conversation.refresh_from_db()
        assert conversation.is_closed is True
        assert conversation.closed_by == citizen_user
    
    def test_rate_conversation(self, authenticated_client, citizen_user, representative_user):
        """اختبار تقييم محادثة"""
        conversation = Conversation.objects.create(
            citizen=citizen_user,
            representative=representative_user,
            subject='محادثة للتقييم',
            is_closed=True
        )
        
        url = reverse('conversation-rate', kwargs={'pk': conversation.id})
        data = {
            'rating': 5,
            'feedback': 'خدمة ممتازة'
        }
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        conversation.refresh_from_db()
        assert conversation.citizen_rating == 5
        assert conversation.citizen_feedback == 'خدمة ممتازة'
    
    def test_rate_open_conversation_fails(self, authenticated_client, citizen_user, representative_user):
        """اختبار فشل تقييم محادثة مفتوحة"""
        conversation = Conversation.objects.create(
            citizen=citizen_user,
            representative=representative_user,
            subject='محادثة مفتوحة',
            is_closed=False
        )
        
        url = reverse('conversation-rate', kwargs={'pk': conversation.id})
        data = {'rating': 5}
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_conversation_stats(self, authenticated_client, citizen_user, representative_user):
        """اختبار إحصائيات المحادثات"""
        # إنشاء محادثات تجريبية
        Conversation.objects.create(
            citizen=citizen_user,
            representative=representative_user,
            subject='محادثة 1'
        )
        Conversation.objects.create(
            citizen=citizen_user,
            representative=representative_user,
            subject='محادثة 2',
            is_closed=True
        )
        
        url = reverse('conversation-stats')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_conversations'] == 2
        assert response.data['active_conversations'] == 1
        assert response.data['closed_conversations'] == 1


@pytest.mark.django_db
class TestMessageAPI:
    """اختبارات API الرسائل"""
    
    def test_create_message(self, authenticated_client, conversation, citizen_user):
        """اختبار إنشاء رسالة جديدة"""
        url = reverse('message-list')
        data = {
            'conversation': conversation.id,
            'content': 'مرحباً، أريد استفسار'
        }
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Message.objects.filter(
            conversation=conversation,
            sender=citizen_user,
            content='مرحباً، أريد استفسار'
        ).exists()
    
    def test_create_message_in_closed_conversation_fails(self, authenticated_client, conversation, citizen_user):
        """اختبار فشل إنشاء رسالة في محادثة مغلقة"""
        conversation.is_closed = True
        conversation.save()
        
        url = reverse('message-list')
        data = {
            'conversation': conversation.id,
            'content': 'رسالة في محادثة مغلقة'
        }
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_mark_message_as_read(self, representative_client, conversation, citizen_user, representative_user):
        """اختبار تحديد رسالة كمقروءة"""
        message = Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='رسالة للقراءة'
        )
        
        url = reverse('message-mark-read', kwargs={'pk': message.id})
        response = representative_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        message.refresh_from_db()
        assert message.is_read is True
        assert message.read_at is not None
    
    def test_mark_own_message_as_read_fails(self, authenticated_client, conversation, citizen_user):
        """اختبار فشل تحديد رسالة المستخدم نفسه كمقروءة"""
        message = Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='رسالة المستخدم'
        )
        
        url = reverse('message-mark-read', kwargs={'pk': message.id})
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_mark_conversation_messages_as_read(self, representative_client, conversation, citizen_user, representative_user):
        """اختبار تحديد جميع رسائل المحادثة كمقروءة"""
        # إنشاء رسائل غير مقروءة
        Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='رسالة 1'
        )
        Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='رسالة 2'
        )
        
        url = reverse('message-mark-conversation-read')
        data = {'conversation_id': conversation.id}
        
        response = representative_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['messages_marked_read'] == 2
        
        # التحقق من أن الرسائل أصبحت مقروءة
        unread_count = Message.objects.filter(
            conversation=conversation,
            is_read=False
        ).exclude(sender=representative_user).count()
        assert unread_count == 0
    
    def test_get_unread_count(self, representative_client, conversation, citizen_user, representative_user):
        """اختبار الحصول على عدد الرسائل غير المقروءة"""
        # إنشاء رسائل غير مقروءة
        Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='رسالة غير مقروءة 1'
        )
        Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='رسالة غير مقروءة 2'
        )
        
        url = reverse('message-unread-count')
        response = representative_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['unread_count'] == 2


@pytest.mark.django_db
class TestMessageReportAPI:
    """اختبارات API الإبلاغات"""
    
    def test_create_report(self, representative_client, conversation, citizen_user, representative_user):
        """اختبار إنشاء إبلاغ"""
        message = Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='رسالة مسيئة'
        )
        
        url = reverse('messagereport-list')
        data = {
            'message': message.id,
            'reason': 'inappropriate',
            'description': 'محتوى غير مناسب'
        }
        
        response = representative_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert MessageReport.objects.filter(
            message=message,
            reporter=representative_user,
            reason='inappropriate'
        ).exists()
    
    def test_report_own_message_fails(self, authenticated_client, conversation, citizen_user):
        """اختبار فشل الإبلاغ عن رسالة المستخدم نفسه"""
        message = Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='رسالة المستخدم'
        )
        
        url = reverse('messagereport-list')
        data = {
            'message': message.id,
            'reason': 'spam'
        }
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_list_user_reports(self, authenticated_client, conversation, citizen_user, representative_user):
        """اختبار قائمة إبلاغات المستخدم"""
        message = Message.objects.create(
            conversation=conversation,
            sender=representative_user,
            content='رسالة للإبلاغ عنها'
        )
        
        report = MessageReport.objects.create(
            message=message,
            reporter=citizen_user,
            reason='spam',
            description='رسالة مزعجة'
        )
        
        url = reverse('messagereport-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['reason'] == 'spam'


@pytest.mark.django_db
class TestSystemNotificationAPI:
    """اختبارات API إشعارات النظام"""
    
    def test_list_user_notifications(self, authenticated_client, citizen_user):
        """اختبار قائمة إشعارات المستخدم"""
        notification = SystemNotification.objects.create(
            user=citizen_user,
            notification_type='message',
            title='رسالة جديدة',
            message='لديك رسالة جديدة'
        )
        
        url = reverse('systemnotification-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['title'] == 'رسالة جديدة'
    
    def test_mark_notification_as_read(self, authenticated_client, citizen_user):
        """اختبار تحديد إشعار كمقروء"""
        notification = SystemNotification.objects.create(
            user=citizen_user,
            notification_type='system',
            title='إشعار النظام'
        )
        
        url = reverse('systemnotification-mark-read', kwargs={'pk': notification.id})
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        notification.refresh_from_db()
        assert notification.is_read is True
        assert notification.read_at is not None
    
    def test_mark_all_notifications_as_read(self, authenticated_client, citizen_user):
        """اختبار تحديد جميع الإشعارات كمقروءة"""
        # إنشاء إشعارات غير مقروءة
        SystemNotification.objects.create(
            user=citizen_user,
            notification_type='message',
            title='إشعار 1'
        )
        SystemNotification.objects.create(
            user=citizen_user,
            notification_type='system',
            title='إشعار 2'
        )
        
        url = reverse('systemnotification-mark-all-read')
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['notifications_marked_read'] == 2
        
        # التحقق من أن جميع الإشعارات أصبحت مقروءة
        unread_count = SystemNotification.objects.filter(
            user=citizen_user,
            is_read=False
        ).count()
        assert unread_count == 0
    
    def test_get_unread_notifications_count(self, authenticated_client, citizen_user):
        """اختبار الحصول على عدد الإشعارات غير المقروءة"""
        # إنشاء إشعارات غير مقروءة
        SystemNotification.objects.create(
            user=citizen_user,
            notification_type='message',
            title='إشعار غير مقروء 1'
        )
        SystemNotification.objects.create(
            user=citizen_user,
            notification_type='system',
            title='إشعار غير مقروء 2'
        )
        # إنشاء إشعار مقروء
        SystemNotification.objects.create(
            user=citizen_user,
            notification_type='message',
            title='إشعار مقروء',
            is_read=True
        )
        
        url = reverse('systemnotification-unread-count')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['unread_count'] == 2


@pytest.mark.django_db
class TestUserStatsAPI:
    """اختبارات API إحصائيات المستخدم"""
    
    def test_get_user_stats(self, authenticated_client, citizen_user, representative_user):
        """اختبار الحصول على إحصائيات المستخدم"""
        # إنشاء بيانات تجريبية
        conversation = Conversation.objects.create(
            citizen=citizen_user,
            representative=representative_user,
            subject='محادثة إحصائيات'
        )
        
        Message.objects.create(
            conversation=conversation,
            sender=citizen_user,
            content='رسالة مرسلة'
        )
        Message.objects.create(
            conversation=conversation,
            sender=representative_user,
            content='رسالة مستلمة'
        )
        
        url = reverse('userstats-my-stats')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_conversations'] == 1
        assert response.data['active_conversations'] == 1
        assert response.data['total_messages_sent'] == 1
        assert response.data['total_messages_received'] == 1
