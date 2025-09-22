"""
Views لخدمة الرسائل - منصة نائبك.كوم
"""

from datetime import datetime, timedelta
from django.db.models import Q, Count, Avg, F
from django.contrib.auth.models import User
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import (
    UserProfile, Conversation, Message, MessageReport, 
    MessageStatistics, SystemNotification
)
from .serializers import (
    UserProfileSerializer, UserProfileCreateSerializer,
    ConversationSerializer, ConversationCreateSerializer, ConversationDetailSerializer,
    MessageSerializer, MessageCreateSerializer,
    MessageReportSerializer, MessageStatisticsSerializer,
    SystemNotificationSerializer, UserStatsSerializer, ConversationStatsSerializer
)
from .filters import ConversationFilter, MessageFilter, MessageReportFilter, SystemNotificationFilter


class UserProfileViewSet(viewsets.ModelViewSet):
    """ViewSet لإدارة ملفات المستخدمين"""
    
    queryset = UserProfile.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['user__first_name', 'user__last_name', 'user__username', 'phone']
    ordering_fields = ['created_at', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']
    filterset_fields = ['user_type', 'governorate', 'district']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserProfileCreateSerializer
        return UserProfileSerializer
    
    def get_queryset(self):
        """فلترة الملفات حسب المستخدم"""
        user = self.request.user
        if user.is_staff:
            return UserProfile.objects.all()
        return UserProfile.objects.filter(user=user)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """الحصول على ملف المستخدم الحالي"""
        try:
            profile = request.user.userprofile
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'ملف المستخدم غير موجود'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def create_profile(self, request):
        """إنشاء ملف للمستخدم الحالي"""
        try:
            # التحقق من عدم وجود ملف مسبقاً
            if hasattr(request.user, 'userprofile'):
                return Response(
                    {'error': 'ملف المستخدم موجود بالفعل'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            data = request.data.copy()
            data['user_id'] = request.user.id
            
            serializer = UserProfileCreateSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConversationViewSet(viewsets.ModelViewSet):
    """ViewSet لإدارة المحادثات"""
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ConversationFilter
    search_fields = ['subject', 'citizen__first_name', 'citizen__last_name', 
                    'representative__first_name', 'representative__last_name']
    ordering_fields = ['created_at', 'last_message_at', 'total_messages', 'citizen_rating']
    ordering = ['-last_message_at', '-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ConversationCreateSerializer
        elif self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationSerializer
    
    def get_queryset(self):
        """فلترة المحادثات حسب المستخدم"""
        user = self.request.user
        if user.is_staff:
            return Conversation.objects.all()
        
        # المستخدم يرى المحادثات التي يشارك فيها فقط
        return Conversation.objects.filter(
            Q(citizen=user) | Q(representative=user)
        ).distinct()
    
    def perform_create(self, serializer):
        """إنشاء محادثة جديدة"""
        # التأكد من أن المستخدم مواطن
        if not hasattr(self.request.user, 'userprofile') or \
           self.request.user.userprofile.user_type != 'citizen':
            raise serializers.ValidationError("فقط المواطنون يمكنهم بدء محادثات جديدة")
        
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """إغلاق المحادثة"""
        conversation = self.get_object()
        
        # التحقق من الصلاحية - المواطن أو النائب يمكنهما إغلاق المحادثة
        if request.user not in [conversation.citizen, conversation.representative]:
            return Response(
                {'error': 'ليس لديك صلاحية لإغلاق هذه المحادثة'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if conversation.is_closed:
            return Response(
                {'error': 'المحادثة مغلقة بالفعل'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conversation.is_closed = True
        conversation.closed_at = timezone.now()
        conversation.closed_by = request.user
        conversation.save()
        
        # إنشاء رسالة نظام
        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=f"تم إغلاق المحادثة بواسطة {request.user.get_full_name() or request.user.username}",
            is_system_message=True
        )
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """تقييم المحادثة من قبل المواطن"""
        conversation = self.get_object()
        
        # التحقق من أن المستخدم هو المواطن
        if request.user != conversation.citizen:
            return Response(
                {'error': 'فقط المواطن يمكنه تقييم المحادثة'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # التحقق من أن المحادثة مغلقة
        if not conversation.is_closed:
            return Response(
                {'error': 'لا يمكن تقييم محادثة مفتوحة'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        rating = request.data.get('rating')
        feedback = request.data.get('feedback', '')
        
        if not rating or not (1 <= int(rating) <= 5):
            return Response(
                {'error': 'التقييم يجب أن يكون بين 1 و 5'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conversation.citizen_rating = int(rating)
        conversation.citizen_feedback = feedback
        conversation.save()
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_conversations(self, request):
        """الحصول على محادثات المستخدم الحالي"""
        user = request.user
        conversations = self.get_queryset().filter(
            Q(citizen=user) | Q(representative=user)
        )
        
        # فلترة حسب النوع إذا تم تحديده
        conversation_type = request.query_params.get('type')
        if conversation_type == 'active':
            conversations = conversations.filter(is_closed=False)
        elif conversation_type == 'closed':
            conversations = conversations.filter(is_closed=True)
        
        page = self.paginate_queryset(conversations)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(conversations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """إحصائيات المحادثات"""
        user = request.user
        queryset = self.get_queryset()
        
        # إحصائيات عامة
        total_conversations = queryset.count()
        active_conversations = queryset.filter(is_closed=False).count()
        closed_conversations = queryset.filter(is_closed=True).count()
        
        # إحصائيات زمنية
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        conversations_today = queryset.filter(created_at__date=today).count()
        conversations_this_week = queryset.filter(created_at__date__gte=week_ago).count()
        conversations_this_month = queryset.filter(created_at__date__gte=month_ago).count()
        
        # متوسط الرسائل لكل محادثة
        avg_messages = queryset.aggregate(avg=Avg('total_messages'))['avg'] or 0
        
        # متوسط مدة المحادثة (بالأيام)
        closed_conversations_qs = queryset.filter(is_closed=True, closed_at__isnull=False)
        avg_duration = 0
        if closed_conversations_qs.exists():
            durations = []
            for conv in closed_conversations_qs:
                duration = (conv.closed_at - conv.created_at).days
                durations.append(duration)
            avg_duration = sum(durations) / len(durations) if durations else 0
        
        stats_data = {
            'total_conversations': total_conversations,
            'active_conversations': active_conversations,
            'closed_conversations': closed_conversations,
            'conversations_today': conversations_today,
            'conversations_this_week': conversations_this_week,
            'conversations_this_month': conversations_this_month,
            'avg_messages_per_conversation': round(avg_messages, 2),
            'avg_conversation_duration': round(avg_duration, 2)
        }
        
        serializer = ConversationStatsSerializer(stats_data)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet لإدارة الرسائل"""
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MessageFilter
    search_fields = ['content']
    ordering_fields = ['created_at', 'read_at']
    ordering = ['created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer
    
    def get_queryset(self):
        """فلترة الرسائل حسب المستخدم"""
        user = self.request.user
        if user.is_staff:
            return Message.objects.all()
        
        # المستخدم يرى الرسائل في المحادثات التي يشارك فيها فقط
        return Message.objects.filter(
            Q(conversation__citizen=user) | Q(conversation__representative=user)
        ).distinct()
    
    def perform_create(self, serializer):
        """إنشاء رسالة جديدة"""
        conversation = serializer.validated_data['conversation']
        
        # التحقق من أن المستخدم مشارك في المحادثة
        if self.request.user not in [conversation.citizen, conversation.representative]:
            raise serializers.ValidationError("ليس لديك صلاحية للكتابة في هذه المحادثة")
        
        # التحقق من أن المحادثة غير مغلقة
        if conversation.is_closed:
            raise serializers.ValidationError("لا يمكن إرسال رسائل في محادثة مغلقة")
        
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """تحديد الرسالة كمقروءة"""
        message = self.get_object()
        
        # التحقق من أن المستخدم ليس المرسل
        if message.sender == request.user:
            return Response(
                {'error': 'لا يمكنك تحديد رسالتك كمقروءة'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message.mark_as_read()
        serializer = self.get_serializer(message)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_conversation_read(self, request):
        """تحديد جميع رسائل المحادثة كمقروءة"""
        conversation_id = request.data.get('conversation_id')
        if not conversation_id:
            return Response(
                {'error': 'معرف المحادثة مطلوب'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            
            # التحقق من أن المستخدم مشارك في المحادثة
            if request.user not in [conversation.citizen, conversation.representative]:
                return Response(
                    {'error': 'ليس لديك صلاحية للوصول لهذه المحادثة'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # تحديد الرسائل غير المقروءة كمقروءة
            unread_messages = conversation.messages.filter(
                is_read=False
            ).exclude(sender=request.user)
            
            updated_count = unread_messages.update(
                is_read=True,
                read_at=timezone.now()
            )
            
            return Response({'messages_marked_read': updated_count})
            
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'المحادثة غير موجودة'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """عدد الرسائل غير المقروءة للمستخدم"""
        user = request.user
        unread_count = Message.objects.filter(
            Q(conversation__citizen=user) | Q(conversation__representative=user),
            is_read=False
        ).exclude(sender=user).count()
        
        return Response({'unread_count': unread_count})


class MessageReportViewSet(viewsets.ModelViewSet):
    """ViewSet لإدارة الإبلاغات"""
    
    queryset = MessageReport.objects.all()
    serializer_class = MessageReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MessageReportFilter
    search_fields = ['description', 'reason']
    ordering_fields = ['created_at', 'reviewed_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """فلترة الإبلاغات حسب المستخدم"""
        user = self.request.user
        if user.is_staff:
            return MessageReport.objects.all()
        return MessageReport.objects.filter(reporter=user)
    
    def perform_create(self, serializer):
        """إنشاء إبلاغ جديد"""
        message = serializer.validated_data['message']
        
        # التحقق من أن المستخدم مشارك في المحادثة
        if self.request.user not in [message.conversation.citizen, message.conversation.representative]:
            raise serializers.ValidationError("ليس لديك صلاحية للإبلاغ عن هذه الرسالة")
        
        # التحقق من عدم الإبلاغ عن رسالة المستخدم نفسه
        if message.sender == self.request.user:
            raise serializers.ValidationError("لا يمكنك الإبلاغ عن رسالتك")
        
        serializer.save()


class SystemNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet لإشعارات النظام"""
    
    serializer_class = SystemNotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SystemNotificationFilter
    search_fields = ['title', 'message']
    ordering_fields = ['created_at', 'read_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """فلترة الإشعارات حسب المستخدم"""
        return SystemNotification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """تحديد الإشعار كمقروء"""
        notification = self.get_object()
        notification.mark_as_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """تحديد جميع الإشعارات كمقروءة"""
        updated_count = self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'notifications_marked_read': updated_count})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """عدد الإشعارات غير المقروءة"""
        unread_count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': unread_count})


class UserStatsViewSet(viewsets.ViewSet):
    """ViewSet لإحصائيات المستخدم"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def my_stats(self, request):
        """إحصائيات المستخدم الحالي"""
        user = request.user
        
        # إحصائيات المحادثات
        conversations = Conversation.objects.filter(
            Q(citizen=user) | Q(representative=user)
        )
        total_conversations = conversations.count()
        active_conversations = conversations.filter(is_closed=False).count()
        
        # إحصائيات الرسائل
        messages_sent = Message.objects.filter(sender=user).count()
        messages_received = Message.objects.filter(
            Q(conversation__citizen=user) | Q(conversation__representative=user)
        ).exclude(sender=user).count()
        
        unread_messages = Message.objects.filter(
            Q(conversation__citizen=user) | Q(conversation__representative=user),
            is_read=False
        ).exclude(sender=user).count()
        
        # إحصائيات شهرية
        month_ago = timezone.now() - timedelta(days=30)
        conversations_this_month = conversations.filter(created_at__gte=month_ago).count()
        messages_this_month = Message.objects.filter(
            sender=user,
            created_at__gte=month_ago
        ).count()
        
        # متوسط وقت الرد (تقدير بسيط)
        avg_response_time = 0  # يمكن تطويره لاحقاً
        
        stats_data = {
            'total_conversations': total_conversations,
            'active_conversations': active_conversations,
            'total_messages_sent': messages_sent,
            'total_messages_received': messages_received,
            'unread_messages': unread_messages,
            'avg_response_time': avg_response_time,
            'conversations_this_month': conversations_this_month,
            'messages_this_month': messages_this_month
        }
        
        serializer = UserStatsSerializer(stats_data)
        return Response(serializer.data)


# Template Views for User Interfaces
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .integrations import integration_manager


@login_required
def citizen_dashboard(request):
    """صفحة إدارة الرسائل للمواطن"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'citizen':
            return render(request, 'messages/error.html', {
                'error': 'هذه الصفحة مخصصة للمواطنين فقط'
            })
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=request.user, user_type='citizen')
        user_profile = request.user.userprofile
    
    # Get user's conversations
    conversations = Conversation.objects.filter(
        citizen=request.user
    ).select_related('representative').order_by('-updated_at')
    
    # Get messaging context from content service
    context = integration_manager.get_messaging_context(request.user.id)
    
    # Add user-specific data
    context.update({
        'user': request.user,
        'user_profile': user_profile,
        'conversations': conversations,
        'unread_count': conversations.filter(
            messages__is_read=False,
            messages__sender__ne=request.user
        ).distinct().count(),
        'total_conversations': conversations.count(),
        'active_conversations': conversations.filter(status='active').count(),
    })
    
    return render(request, 'messages/citizen_dashboard.html', context)


@login_required
def representative_dashboard(request):
    """صفحة إدارة الرسائل للنائب"""
    try:
        user_profile = request.user.userprofile
        if user_profile.user_type != 'representative':
            return render(request, 'messages/error.html', {
                'error': 'هذه الصفحة مخصصة للنواب فقط'
            })
    except UserProfile.DoesNotExist:
        return render(request, 'messages/error.html', {
            'error': 'يجب إنشاء ملف شخصي أولاً'
        })
    
    # Get representative's conversations
    conversations = Conversation.objects.filter(
        representative=request.user
    ).select_related('citizen').order_by('-updated_at')
    
    # Get representative info from content service
    representative_info = integration_manager.content_service.get_representative_contact_info(
        user_profile.representative_id
    ) if hasattr(user_profile, 'representative_id') else None
    
    context = {
        'user': request.user,
        'user_profile': user_profile,
        'representative_info': representative_info,
        'conversations': conversations,
        'unread_count': conversations.filter(
            messages__is_read=False,
            messages__sender__ne=request.user
        ).distinct().count(),
        'total_conversations': conversations.count(),
        'active_conversations': conversations.filter(status='active').count(),
        'pending_conversations': conversations.filter(status='pending').count(),
        'reports_count': MessageReport.objects.filter(
            message__conversation__representative=request.user,
            is_reviewed=False
        ).count(),
    }
    
    return render(request, 'messages/representative_dashboard.html', context)


@login_required
def admin_dashboard(request):
    """صفحة إدارة الرسائل للأدمن"""
    if not request.user.is_staff:
        return render(request, 'messages/error.html', {
            'error': 'هذه الصفحة مخصصة للإدارة فقط'
        })
    
    # Get system statistics
    total_conversations = Conversation.objects.count()
    active_users = User.objects.filter(last_login__gte=timezone.now() - timedelta(days=30)).count()
    pending_reports = MessageReport.objects.filter(is_reviewed=False).count()
    messages_today = Message.objects.filter(created_at__date=timezone.now().date()).count()
    
    # Get recent activity
    recent_activities = []  # This would be populated from an activity log
    
    # Get reports for admin review
    reports = MessageReport.objects.filter(
        is_reviewed=False
    ).select_related('reporter', 'message__sender', 'message__conversation').order_by('-created_at')[:20]
    
    # Get users for management
    users = UserProfile.objects.select_related('user').order_by('-user__date_joined')[:50]
    
    context = {
        'user': request.user,
        'total_conversations': total_conversations,
        'active_users': active_users,
        'pending_reports': pending_reports,
        'messages_today': messages_today,
        'recent_activities': recent_activities,
        'reports': reports,
        'users': users,
        # Chart data
        'active_conversations': Conversation.objects.filter(status='active').count(),
        'closed_conversations': Conversation.objects.filter(status='closed').count(),
        'pending_conversations': Conversation.objects.filter(status='pending').count(),
        'citizens_count': UserProfile.objects.filter(user_type='citizen').count(),
        'representatives_count': UserProfile.objects.filter(user_type='representative').count(),
        'admins_count': User.objects.filter(is_staff=True).count(),
        'messages_chart_labels': [],  # Would be populated with actual data
        'messages_chart_data': [],    # Would be populated with actual data
    }
    
    return render(request, 'messages/admin_dashboard.html', context)


@require_http_methods(["GET"])
@login_required
def get_representatives_list(request):
    """API endpoint to get representatives list for messaging"""
    governorate = request.GET.get('governorate')
    search = request.GET.get('search')
    
    filters = {}
    if governorate:
        filters['governorate'] = governorate
    if search:
        filters['search'] = search
    
    representatives = integration_manager.content_service.search_representatives(filters)
    
    return JsonResponse({
        'representatives': representatives,
        'count': len(representatives)
    })


@require_http_methods(["POST"])
@login_required
def start_conversation_with_representative(request):
    """Start a new conversation with a representative"""
    import json
    
    try:
        data = json.loads(request.body)
        representative_id = data.get('representative_id')
        subject = data.get('subject', '').strip()
        initial_message = data.get('message', '').strip()
        
        if not representative_id or not subject or not initial_message:
            return JsonResponse({
                'error': 'جميع الحقول مطلوبة'
            }, status=400)
        
        # Validate representative exists
        if not integration_manager.content_service.validate_representative_exists(representative_id):
            return JsonResponse({
                'error': 'النائب المحدد غير موجود'
            }, status=404)
        
        # Check if conversation already exists
        existing_conversation = Conversation.objects.filter(
            citizen=request.user,
            representative_id=representative_id,
            status__in=['active', 'pending']
        ).first()
        
        if existing_conversation:
            return JsonResponse({
                'error': 'يوجد محادثة نشطة مع هذا النائب بالفعل',
                'conversation_id': existing_conversation.id
            }, status=400)
        
        # Create new conversation
        conversation = Conversation.objects.create(
            citizen=request.user,
            representative_id=representative_id,
            subject=subject,
            status='pending'
        )
        
        # Create initial message
        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=initial_message
        )
        
        # Increment message count in content service
        integration_manager.content_service.increment_message_count(representative_id)
        
        return JsonResponse({
            'success': True,
            'conversation_id': conversation.id,
            'message': 'تم إنشاء المحادثة بنجاح'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'بيانات غير صحيحة'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': 'حدث خطأ غير متوقع'
        }, status=500)
