from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsFleetManager
from .models import Message, Notification, SOSAlert
from .serializers import MessageSerializer, NotificationSerializer, SOSAlertSerializer


class MessageViewSet(viewsets.ModelViewSet):
    """
    Supports 1:1 internal native chat between explicitly authenticated users.
    Limits data scopes dynamically based rigorously upon requesting identities securely.
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['trip', 'is_read']
    ordering_fields = ['sent_at']

    def get_queryset(self):
        user = self.request.user
        
        # Accommodates swagger schema parsing smoothly without hitting unauthorized database queries.
        if getattr(self, 'swagger_fake_view', False):
            return Message.objects.none()
            
        qs = Message.objects.filter(Q(sender=user) | Q(receiver=user))
        
        # Allows narrowing natively to a specific active conversational thread.
        peer = self.request.query_params.get('peer')
        if peer:
            qs = qs.filter(Q(sender_id=peer) | Q(receiver_id=peer))
            
        return qs.select_related('sender', 'receiver', 'trip')

    def perform_create(self, serializer):
        """Forces true authorship natively preventing malicious spoofing."""
        serializer.save(sender=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Ensures receipt timestamps apply reliably."""
        message = self.get_object()
        if message.receiver != request.user:
            return Response(
                {'detail': 'Only the receiver can mark a message as read.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        message.is_read = True
        message.read_at = timezone.now()
        message.save()
        return Response(MessageSerializer(message).data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        updated = Message.objects.filter(
            receiver=request.user, is_read=False,
        ).update(is_read=True, read_at=timezone.now())
        return Response({'detail': f'{updated} messages marked as read.'})


class NotificationViewSet(viewsets.ModelViewSet):
    """
    Endpoint parsing global asynchronous Alerts for display layers smoothly.
    Restricts explicit object visibility cleanly to targeted target identities.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['alert_type', 'status', 'reference_type']
    ordering_fields = ['created_at']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.status = 'read'
        notification.read_at = timezone.now()
        notification.save()
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        updated = Notification.objects.filter(
            user=request.user, status='unread',
        ).update(status='read', read_at=timezone.now())
        return Response({'detail': f'{updated} notifications marked as read.'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, status='unread').count()
        return Response({'unread_count': count})


class SOSAlertViewSet(viewsets.ModelViewSet):
    """
    High-priority dispatch hooks handling physical location distress signals natively.
    Exclusively locks standard operational completion behind 'IsFleetManager' resolving securely.
    """
    queryset = SOSAlert.objects.select_related('driver', 'vehicle', 'trip').all()
    serializer_class = SOSAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['driver', 'vehicle', 'resolved']
    ordering_fields = ['triggered_at']

    def perform_create(self, serializer):
        """Overrides explicit sender spoofing."""
        serializer.save(driver=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsFleetManager])
    def resolve(self, request, pk=None):
        """Authoritative completion signal exclusively reserved for Managers securely manually closing."""
        alert = self.get_object()
        if alert.resolved:
            return Response(
                {'detail': 'Alert already resolved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        alert.resolved = True
        alert.resolved_by = request.user
        alert.resolved_at = timezone.now()
        alert.save()
        return Response(SOSAlertSerializer(alert).data)
