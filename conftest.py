"""
إعدادات pytest لخدمة الرسائل - منصة نائبك.كوم
"""

import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
import factory
from factory.django import DjangoModelFactory
from messages.models import UserProfile, Conversation, Message


class UserFactory(DjangoModelFactory):
    """Factory لإنشاء مستخدمين للاختبار"""
    
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True


class UserProfileFactory(DjangoModelFactory):
    """Factory لإنشاء ملفات المستخدمين للاختبار"""
    
    class Meta:
        model = UserProfile
    
    user = factory.SubFactory(UserFactory)
    user_type = 'citizen'
    phone = factory.Faker('phone_number')
    governorate = factory.Faker('city')
    district = factory.Faker('city')
    email_notifications = True
    sms_notifications = True


class RepresentativeProfileFactory(UserProfileFactory):
    """Factory لإنشاء ملفات النواب للاختبار"""
    
    user_type = 'representative'
    representative_id = factory.Sequence(lambda n: n + 1)


class ConversationFactory(DjangoModelFactory):
    """Factory لإنشاء محادثات للاختبار"""
    
    class Meta:
        model = Conversation
    
    citizen = factory.SubFactory(UserFactory)
    representative = factory.SubFactory(UserFactory)
    subject = factory.Faker('sentence', nb_words=4)


class MessageFactory(DjangoModelFactory):
    """Factory لإنشاء رسائل للاختبار"""
    
    class Meta:
        model = Message
    
    conversation = factory.SubFactory(ConversationFactory)
    sender = factory.SubFactory(UserFactory)
    content = factory.Faker('text', max_nb_chars=200)
    is_read = False
    is_system_message = False


@pytest.fixture
def api_client():
    """عميل API للاختبارات"""
    return APIClient()


@pytest.fixture
def client():
    """عميل Django للاختبارات"""
    return Client()


@pytest.fixture
def user():
    """مستخدم عادي للاختبار"""
    return UserFactory()


@pytest.fixture
def citizen_user():
    """مواطن للاختبار"""
    user = UserFactory()
    UserProfileFactory(user=user, user_type='citizen')
    return user


@pytest.fixture
def representative_user():
    """نائب للاختبار"""
    user = UserFactory()
    RepresentativeProfileFactory(user=user, user_type='representative')
    return user


@pytest.fixture
def authenticated_client(api_client, citizen_user):
    """عميل API مع مصادقة"""
    refresh = RefreshToken.for_user(citizen_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def representative_client(api_client, representative_user):
    """عميل API للنائب مع مصادقة"""
    refresh = RefreshToken.for_user(representative_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def conversation(citizen_user, representative_user):
    """محادثة للاختبار"""
    return ConversationFactory(
        citizen=citizen_user,
        representative=representative_user
    )


@pytest.fixture
def message(conversation, citizen_user):
    """رسالة للاختبار"""
    return MessageFactory(
        conversation=conversation,
        sender=citizen_user
    )
