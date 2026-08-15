from django.core.management.base import BaseCommand
from tasks.services import TaskService


class Command(BaseCommand):
    help = 'Delete completed tasks older than 7 days. Run this as a scheduled cron job instead of on every page load.'

    def handle(self, *args, **options):
        count = TaskService.cleanup_expired_completed_tasks()
        if count > 0:
            self.stdout.write(self.style.SUCCESS(f'Deleted {count} expired completed task(s).'))
        else:
            self.stdout.write('No expired completed tasks to clean up.')
