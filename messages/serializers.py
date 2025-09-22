"""
Serializers لخدمة الرسائل - منصة نائبك.كوم
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.validators import MaxLengthValidator
from .models import (
    UserProfile, Conversation, Message, MessageReport, 
    MessageStatistics, SystemNotification
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer للمستخدم"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name']
        read_only_fields = ['id', 'username']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer لملف المستخدم"""
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'user_type', 'phone', 'avatar', 'full_name',
            'representative_id', 'district', 'governorate',
            'email_notifications', 'sms_notifications',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserProfileCreateSerializer(serializers.ModelSerializer):
    """Serializer لإنشاء ملف المستخدم"""
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'user_id', 'user_type', 'phone', 'avatar',
            'representative_id', 'district', 'governorate',
            'email_notifications', 'sms_notifications'
        ]
    
    def create(self, validated_data):
        user_id = validated_data.pop('user_id')
        user = User.objects.get(id=user_id)
        validated_data['user'] = user
        return super().create(validated_data)


class MessageSerializer(serializers.ModelSerializer):
    """Serializer للرسائل"""
    sender = UserSerializer(read_only=True)
    sender_profile = serializers.SerializerMethodField()
    is_from_citizen = serializers.ReadOnlyField()
    is_from_representative = serializers.ReadOnlyField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_profile', 'content',
            'is_read', 'read_at', 'is_system_message', 'reply_to',
            'is_from_citizen', 'is_from_representative',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sender', 'is_read', 'read_at', 'created_at', 'updated_at']
    
    def get_sender_profile(self, obj):
        """الحصول على ملف المرسل"""
        try:
            profile = obj.sender.userprofile
            return {
                'user_type': profile.user_type,
                'avatar': profile.avatar.url if profile.avatar else None,
                'district': profile.district,
                'governorate': profile.governorate
            }
        except:
            return None
    
    def validate_content(self, value):
        """التحقق من محتوى الرسالة"""
        if len(value.strip()) == 0:
            raise serializers.ValidationError("محتوى الرسالة لا يمكن أن يكون فارغاً")
        
        if len(value) > 500:
            raise serializers.ValidationError("الحد الأقصى لمحتوى الرسالة 500 حرف")
        
        return value.strip()


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer لإنشاء رسالة جديدة"""
    
    class Meta:
        model = Message
        fields = ['conversation', 'content', 'reply_to']
    
    def validate_content(self, value):
        """التحقق من محتوى الرسالة"""
        if len(value.strip()) == 0:
            raise serializers.ValidationError("محتوى الرسالة لا يمكن أن يكون فارغاً")
        
        if len(value) > 500:
            raise serializers.ValidationError("الحد الأقصى لمحتوى الرسالة 500 حرف")
        
        return value.strip()
    
    def create(self, validated_data):
        """إنشاء رسالة جديدة"""
        request = self.context.get('request')
        if request and request.user:
            validated_data['sender'] = request.user
        return super().create(validated_data)


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer للمحادثات"""
    citizen = UserSerializer(read_only=True)
    representative = UserSerializer(read_only=True)
    citizen_profile = serializers.SerializerMethodField()
    representative_profile = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'citizen', 'representative', 'citizen_profile', 'representative_profile',
            'subject', 'total_messages', 'last_message_at', 'last_message',
            'is_closed', 'closed_at', 'citizen_rating', 'citizen_feedback',
            'unread_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_messages', 'last_message_at', 'is_closed', 
            'closed_at', 'created_at', 'updated_at'
        ]
    
    def get_citizen_profile(self, obj):
        """الحصول على ملف المواطن"""
        try:
            profile = obj.citizen.userprofile
            return {
                'user_type': profile.user_type,
                'avatar': profile.avatar.url if profile.avatar else None,
                'phone': profile.phone
            }
        except:
            return None
    
    def get_representative_profile(self, obj):
        """الحصول على ملف النائب"""
        try:
            profile = obj.representative.userprofile
            return {
                'user_type': profile.user_type,
                'avatar': profile.avatar.url if profile.avatar else None,
                'district': profile.district,
                'governorate': profile.governorate
            }
        except:
            return None
    
    def get_last_message(self, obj):
        """الحصول على آخر رسالة"""
        last_message = obj.messages.last()
        if last_message:
            return {
                'id': str(last_message.id),
                'content': last_message.content[:100] + "..." if len(last_message.content) > 100 else last_message.content,
                'sender': last_message.sender.get_full_name() or last_message.sender.username,
                'created_at': last_message.created_at,
                'is_read': last_message.is_read
            }
        return None
    
    def get_unread_count(self, obj):
        """الحصول على عدد الرسائل غير المقروءة للمستخدم الحالي"""
        request = self.context.get('request')
        if not request or not request.user:
            return 0
        
        user = request.user
        if user == obj.citizen:
            return obj.unread_count_for_citizen
        elif user == obj.representative:
            return obj.unread_count_for_representative
        return 0


class ConversationCreateSerializer(serializers.ModelSerializer):
    """Serializer لإنشاء محادثة جديدة"""
    representative_id = serializers.IntegerField(write_only=True)
    first_message = serializers.CharField(
        write_only=True, 
        validators=[MaxLengthValidator(500)],
        help_text="الرسالة الأولى في المحادثة"
    )
    
    class Meta:
        model = Conversation
        fields = ['representative_id', 'subject', 'first_message']
    
    def validate_representative_id(self, value):
        """التحقق من وجود النائب"""
        try:
            user = User.objects.get(id=value)
            profile = user.userprofile
            if profile.user_type != 'representative':
                raise serializers.ValidationError("المستخدم المحدد ليس نائباً")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("النائب غير موجود")
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError("ملف النائب غير موجود")
    
    def validate(self, data):
        """التحقق من صحة البيانات العامة"""
        request = self.context.get('request')
        if request and request.user:
            citizen = request.user
            representative_id = data.get('representative_id')
            
            # التحقق من عدم إنشاء محادثة مع نفس المستخدم
            if citizen.id == representative_id:
                raise serializers.ValidationError({
                    'non_field_errors': ['لا يمكن إنشاء محادثة مع نفسك']
                })
        
        return data
    
    def validate_first_message(self, value):
        """التحقق من الرسالة الأولى"""
        if len(value.strip()) == 0:
            raise serializers.ValidationError("الرسالة الأولى لا يمكن أن تكون فارغة")
        return value.strip()
    
    def create(self, validated_data):
        """إنشاء محادثة جديدة مع الرسالة الأولى"""
        representative_id = validated_data.pop('representative_id')
        first_message_content = validated_data.pop('first_message')
        
        representative = User.objects.get(id=representative_id)
        request = self.context.get('request')
        citizen = request.user if request else None
        
        # إنشاء المحادثة
        conversation = Conversation.objects.create(
            citizen=citizen,
            representative=representative,
            **validated_data
        )
        
        # إنشاء الرسالة الأولى
        Message.objects.create(
            conversation=conversation,
            sender=citizen,
            content=first_message_content
        )
        
        return conversation


class MessageReportSerializer(serializers.ModelSerializer):
    """Serializer للإبلاغ عن الرسائل"""
    reporter = UserSerializer(read_only=True)
    message_content = serializers.CharField(source='message.content', read_only=True)
    
    class Meta:
        model = MessageReport
        fields = [
            'id', 'message', 'reporter', 'message_content', 'reason', 
            'description', 'is_reviewed', 'reviewed_at', 'action_taken',
            'created_at'
        ]
        read_only_fields = ['id', 'reporter', 'is_reviewed', 'reviewed_at', 'created_at']
    
    def create(self, validated_data):
        """إنشاء إبلاغ جديد"""
        request = self.context.get('request')
        if request and request.user:
            validated_data['reporter'] = request.user
        return super().create(validated_data)


class MessageStatisticsSerializer(serializers.ModelSerializer):
    """Serializer لإحصائيات الرسائل"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = MessageStatistics
        fields = [
            'id', 'user', 'date', 'messages_sent', 'messages_received',
            'conversations_started', 'conversations_closed', 'avg_response_time'
        ]
        read_only_fields = ['id', 'user']


class SystemNotificationSerializer(serializers.ModelSerializer):
    """Serializer لإشعارات النظام"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = SystemNotification
        fields = [
            'id', 'user', 'notification_type', 'title', 'message', 'related_object_id',
            'action_url', 'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'is_read', 'read_at', 'created_at']


class ConversationDetailSerializer(ConversationSerializer):
    """Serializer تفصيلي للمحادثة مع الرسائل"""
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ['messages']


class UserStatsSerializer(serializers.Serializer):
    """Serializer لإحصائيات المستخدم"""
    total_conversations = serializers.IntegerField()
    active_conversations = serializers.IntegerField()
    total_messages_sent = serializers.IntegerField()
    total_messages_received = serializers.IntegerField()
    unread_messages = serializers.IntegerField()
    avg_response_time = serializers.FloatField()
    conversations_this_month = serializers.IntegerField()
    messages_this_month = serializers.IntegerField()


class ConversationStatsSerializer(serializers.Serializer):
    """Serializer لإحصائيات المحادثات"""
    total_conversations = serializers.IntegerField()
    active_conversations = serializers.IntegerField()
    closed_conversations = serializers.IntegerField()
    conversations_today = serializers.IntegerField()
    conversations_this_week = serializers.IntegerField()
    conversations_this_month = serializers.IntegerField()
    avg_messages_per_conversation = serializers.FloatField()
    avg_conversation_duration = serializers.FloatField()
