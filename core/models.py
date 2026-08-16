from django.db import models
from django.conf import settings


class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    organization = models.ForeignKey('organizations.Organization', on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    action = models.CharField(max_length=100, db_index=True)
    description = models.TextField()
    resource_type = models.CharField(max_length=50, blank=True, db_index=True)
    resource_id = models.CharField(max_length=50, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, default='success', db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            # Covers: Global activity log display ordered by most recent
            models.Index(fields=['-timestamp']),
            # Covers: Org-scoped audit log — filtered by organization, ordered by timestamp desc
            models.Index(fields=['organization', '-timestamp']),
            # Covers: Action-type filtering in audit log (e.g. "all login events")
            models.Index(fields=['action', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.user} - {self.action} ({self.status}) at {self.timestamp}"
