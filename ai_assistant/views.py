import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .agent import build_fleet_agent, extract_generated_sql
from .models import AIChatMessage, AIChatSession
from .serializers import (
    AIChatMessageSerializer,
    AIChatSessionSerializer,
    ChatRequestSerializer,
)

logger = logging.getLogger('ai_assistant')


class AIChatThrottle(UserRateThrottle):
    """Limits each authenticated user to 20 AI chat requests per hour."""
    rate = '20/hour'
    scope = 'ai_chat'


# ---------------------------------------------------------------------------
# POST /api/v1/ai/chat/
# ---------------------------------------------------------------------------

class ChatView(APIView):
    """
    Intelligent dispatch ingestion hooking real human language onto LangChain execution agents natively.
    Limits abuse strictly via Throttles enforcing API consumption budgets proactively.

    POST body:
        message    (str, required)  – The user's semantic intention block (max 1000 chars)
        session_id (int, optional)  – Tracks contiguous window context (creates new natively if omitted)

    Returns parsed logical dict outputs representing database resolutions wrapped securely in human text.
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AIChatThrottle]

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_message = serializer.validated_data['message']
        session_id = serializer.validated_data.get('session_id')

        # ── Resolve or create the chat session ──────────────────────────────
        if session_id:
            try:
                session = AIChatSession.objects.get(id=session_id, user=request.user)
            except AIChatSession.DoesNotExist:
                return Response(
                    {'error': 'Session not found.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            session = AIChatSession.objects.create(user=request.user)

        # ── Load recent history (oldest-first) ──────────────────────────────
        recent_messages = list(
            session.messages.order_by('created_at')
        )

        # ── Save the user's message ──────────────────────────────────────────
        AIChatMessage.objects.create(
            session=session,
            role='human',
            content=user_message,
        )

        # ── Auto-title the session on first message ──────────────────────────
        is_first_message = len(recent_messages) == 0
        if is_first_message and session.title == 'New Chat':
            session.title = user_message[:60] + ('...' if len(user_message) > 60 else '')
            session.save(update_fields=['title'])

        # ── Pre-flight config check ──────────────────────────────────────────
        first_name = request.user.first_name or request.user.username
        if not getattr(settings, 'MISTRAL_API_KEY', ''):
            return Response(
                {'error': 'AI assistant is not configured (missing MISTRAL_API_KEY).'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not getattr(settings, 'AI_ASSISTANT_DB_URL', ''):
            return Response(
                {'error': 'AI assistant is not configured (missing AI_ASSISTANT_DB_URL).'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # ── Run the AI chain ─────────────────────────────────────────────────
        ai_response = ''
        generated_sql = ''

        try:
            chain = build_fleet_agent(request.user, recent_messages)

            result = chain.invoke({'input': user_message})

            ai_response = result.get('output', '').strip()
            generated_sql = extract_generated_sql(result)

            if not ai_response:
                ai_response = (
                    f"I'm sorry {first_name}, "
                    "I couldn't generate a response. Please try rephrasing your question."
                )

        except PermissionDenied:
            ai_response = (
                f"Sorry {first_name}, "
                "I can only read data from the fleet database — "
                "I'm not able to make any changes."
            )

        except Exception as e:
            logger.error(
                "AI chain error for user %s: %s", request.user.id, e, exc_info=True
            )
            ai_response = (
                f"I encountered an error processing your request, {first_name}. "
                "Please try rephrasing your question."
            )

        # ── Save the AI response ─────────────────────────────────────────────
        ai_msg = AIChatMessage.objects.create(
            session=session,
            role='ai',
            content=ai_response,
            generated_sql=generated_sql,
        )

        session.save(update_fields=['updated_at'])

        # ── Build response ───────────────────────────────────────────────────
        response_data = {
            'session_id': session.id,
            'session_title': session.title,
            'message': AIChatMessageSerializer(ai_msg).data,
        }

        # Include suggested starter questions on the very first exchange
        if is_first_message:
            response_data['suggested_questions'] = _get_suggested_questions(request.user)

        return Response(response_data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# GET /api/v1/ai/chat/history/
# ---------------------------------------------------------------------------

class ChatHistoryView(APIView):
    """
    Retrieve messages in a specific session.

    Query params:
        session_id (int, required) – The session to retrieve
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response(
                {'error': 'session_id query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = AIChatSession.objects.get(
                id=session_id, user=request.user
            )
        except AIChatSession.DoesNotExist:
            return Response(
                {'error': 'Session not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        messages = session.messages.order_by('created_at')
        return Response({
            'session_id': session.id,
            'session_title': session.title,
            'messages': AIChatMessageSerializer(messages, many=True).data,
        })


# ---------------------------------------------------------------------------
# GET /api/v1/ai/chat/sessions/
# ---------------------------------------------------------------------------

class ChatSessionListView(APIView):
    """List the 20 most recent chat sessions for the authenticated user."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sessions = (
            AIChatSession.objects
            .filter(user=request.user)
            .order_by('-updated_at')[:20]
        )
        return Response({
            'sessions': AIChatSessionSerializer(sessions, many=True).data,
        })


# ---------------------------------------------------------------------------
# DELETE /api/v1/ai/chat/sessions/<session_id>/clear/
# ---------------------------------------------------------------------------

class ClearSessionView(APIView):
    """Delete all messages in a session (keeps the session itself)."""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, session_id):
        try:
            session = AIChatSession.objects.get(id=session_id, user=request.user)
        except AIChatSession.DoesNotExist:
            return Response(
                {'error': 'Session not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        deleted_count, _ = session.messages.all().delete()
        session.title = 'New Chat'
        session.save(update_fields=['title', 'updated_at'])

        return Response({'deleted_messages': deleted_count}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_suggested_questions(user) -> list:
    """Return role-specific starter questions to guide first-time users."""
    profile = getattr(user, 'profile', None)
    role = profile.role if profile else ''

    if role == 'driver':
        return [
            "What is the status of my current trip?",
            "How many trips have I completed this month?",
            "Show me my recent fuel logs.",
            "Do I have any pending leave requests?",
        ]
    elif role == 'fleet_manager':
        return [
            "How many vehicles are currently available?",
            "Show me all trips in progress right now.",
            "Which vehicles are due for maintenance soon?",
            "Are there any unresolved SOS alerts?",
            "How many orders are pending assignment?",
        ]
    else:  # maintenance_staff
        return [
            "Which vehicles have open issues?",
            "Show me all scheduled maintenance this week.",
            "Which maintenance records are currently in progress?",
            "List all critical vehicle issues.",
        ]
