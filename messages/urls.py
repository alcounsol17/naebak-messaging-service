"""
URLs لخدمة الرسائل - منصة نائبك.كوم
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserProfileViewSet, ConversationViewSet, MessageViewSet,
    MessageReportViewSet, SystemNotificationViewSet, UserStatsViewSet
)

# إنشاء router للـ ViewSets
router = DefaultRouter()
router.register(r'profiles', UserProfileViewSet, basename='userprofile')
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'reports', MessageReportViewSet, basename='messagereport')
router.register(r'notifications', SystemNotificationViewSet, basename='systemnotification')
router.register(r'stats', UserStatsViewSet, basename='userstats')

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # مسارات إضافية مخصصة
    path('api/conversations/<uuid:pk>/messages/', 
         MessageViewSet.as_view({'get': 'list'}), 
         name='conversation-messages'),
]
