from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Notifications'
        ctx['unread_count'] = Notification.objects.filter(recipient=self.request.user, is_read=False).count()
        return ctx


class MarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notif.is_read = True
        notif.save()
        if notif.related_task:
            return redirect('tasks:detail', pk=notif.related_task.pk)
        return redirect('notifications:list')


class MarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        messages.success(request, 'All notifications marked as read.')
        return redirect('notifications:list')


class DeleteNotificationView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notif.delete()
        messages.success(request, 'Notification permanently deleted.')
        return redirect('notifications:list')


class BulkDeleteNotificationView(LoginRequiredMixin, View):
    def post(self, request):
        action_type = request.POST.get('action_type', 'selected')
        if action_type == 'all':
            deleted_count, _ = Notification.objects.filter(recipient=request.user).delete()
            if deleted_count > 0:
                messages.success(request, f'All {deleted_count} notifications permanently deleted.')
            else:
                messages.info(request, 'No notifications to delete.')
        else:
            selected_ids = request.POST.getlist('notification_ids')
            if selected_ids:
                deleted_count, _ = Notification.objects.filter(recipient=request.user, pk__in=selected_ids).delete()
                messages.success(request, f'Successfully deleted {deleted_count} notification(s) permanently.')
            else:
                messages.warning(request, 'No notifications were selected for deletion.')

        return redirect('notifications:list')

