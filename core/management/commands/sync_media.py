import os
import cloudinary
import cloudinary.uploader
from django.core.management.base import BaseCommand
from django.conf import settings
from accounts.models import User
from organizations.models import Organization


class Command(BaseCommand):
    help = 'Sync all local media files to Cloudinary'

    def handle(self, *args, **options):
        self.stdout.write("Scanning and syncing local media files to Cloudinary...")

        synced_count = 0
        error_count = 0

        # Scan User Profile Pictures
        for user in User.objects.exclude(profile_picture='').exclude(profile_picture__isnull=True):
            name = user.profile_picture.name
            clean_name = name.replace('media/', '', 1) if name.startswith('media/') else name
            local_path = os.path.join(settings.MEDIA_ROOT, clean_name)
            alt_local_path = os.path.join(settings.MEDIA_ROOT, name)

            target = local_path if os.path.exists(local_path) else (alt_local_path if os.path.exists(alt_local_path) else None)
            if target:
                pub_id = os.path.splitext(name)[0]
                try:
                    with open(target, 'rb') as f:
                        res = cloudinary.uploader.upload(f, public_id=pub_id, overwrite=True)
                        self.stdout.write(self.style.SUCCESS(f"[Synced User Pic] {user.username} -> {res.get('secure_url')}"))
                        synced_count += 1
                except Exception as ex:
                    self.stdout.write(self.style.ERROR(f"[Error User Pic] {user.username}: {ex}"))
                    error_count += 1

        # Scan Organization Logos
        for org in Organization.objects.exclude(logo='').exclude(logo__isnull=True):
            name = org.logo.name
            clean_name = name.replace('media/', '', 1) if name.startswith('media/') else name
            local_path = os.path.join(settings.MEDIA_ROOT, clean_name)
            alt_local_path = os.path.join(settings.MEDIA_ROOT, name)

            target = local_path if os.path.exists(local_path) else (alt_local_path if os.path.exists(alt_local_path) else None)
            if target:
                pub_id = os.path.splitext(name)[0]
                try:
                    with open(target, 'rb') as f:
                        res = cloudinary.uploader.upload(f, public_id=pub_id, overwrite=True)
                        self.stdout.write(self.style.SUCCESS(f"[Synced Org Logo] {org.name} -> {res.get('secure_url')}"))
                        synced_count += 1
                except Exception as ex:
                    self.stdout.write(self.style.ERROR(f"[Error Org Logo] {org.name}: {ex}"))
                    error_count += 1

        self.stdout.write(self.style.SUCCESS(f"Sync complete. Successfully uploaded: {synced_count}, Errors: {error_count}"))
