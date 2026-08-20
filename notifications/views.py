from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, View
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import EmptyPage, PageNotAnInteger
from core.mixins import FragmentResponseMixin
from .models import Notification


class NotificationListView(FragmentResponseMixin, LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related('related_task')

    def paginate_queryset(self, queryset, page_size):
        """Override to return last available page if requested page exceeds total."""
        paginator = self.get_paginator(
            queryset, page_size, orphans=self.get_paginate_orphans(),
            allow_empty_first_page=self.get_allow_empty()
        )
        page_kwarg = self.page_kwarg
        page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
        try:
            page_number = paginator.validate_number(page)
        except PageNotAnInteger:
            page_number = 1
        except EmptyPage:
            # Return last available page if requested page exceeds total
            page_number = paginator.num_pages
        page = paginator.page(page_number)
        return (paginator, page, page.object_list, page.has_other_pages())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Notifications'
        ctx['unread_count'] = Notification.objects.filter(recipient=self.request.user, is_read=False).count()
        return ctx


class MarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        cache.delete(f'notif_unread_{request.user.pk}')
        
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return redirect(referer)
        return redirect('notifications:list')


class MarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        cache.delete(f'notif_unread_{request.user.pk}')
        messages.success(request, 'All notifications marked as read.')
        return redirect('notifications:list')


class DeleteNotificationView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notif.delete()
        cache.delete(f'notif_unread_{request.user.pk}')
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

        cache.delete(f'notif_unread_{request.user.pk}')
        return redirect('notifications:list')

