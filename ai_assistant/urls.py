from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.ChatView.as_view(), name='ai-chat'),
    path('chat/history/', views.ChatHistoryView.as_view(), name='ai-chat-history'),
    path('chat/sessions/', views.ChatSessionListView.as_view(), name='ai-chat-sessions'),
    path('chat/sessions/<int:session_id>/clear/', views.ClearSessionView.as_view(), name='ai-chat-clear'),
]
