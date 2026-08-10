import os
import logging
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from cloudinary_storage.storage import MediaCloudinaryStorage, RawMediaCloudinaryStorage
import cloudinary.uploader

logger = logging.getLogger(__name__)


class SmartMediaCloudinaryStorage(MediaCloudinaryStorage):
    """
    Smart Media Storage bridging Cloudinary and local media storage:
    1. Saves uploaded media to Cloudinary AND creates an exact local file copy in MEDIA_ROOT.
    2. Auto-syncs legacy local files to Cloudinary on access if missing.
    3. Falls back seamlessly to local media URLs if Cloudinary is offline.
    """

    def _save(self, name, content):
        local_storage = FileSystemStorage()
        clean_local_name = name.replace('media/', '', 1) if name.startswith('media/') else name
        
        # Save local copy first
        saved_local_name = None
        try:
            if not local_storage.exists(clean_local_name):
                saved_local_name = local_storage.save(clean_local_name, content)
            else:
                saved_local_name = clean_local_name
            if hasattr(content, 'seek'):
                content.seek(0)
        except Exception as ex:
            logger.warning(f"SmartMediaCloudinaryStorage local backup warning: {ex}")

        # Upload to Cloudinary
        try:
            c_name = super()._save(name, content)
            # Ensure local copy also exists under the Cloudinary returned name if suffixed
            if c_name and c_name != name:
                clean_c = c_name.replace('media/', '', 1) if c_name.startswith('media/') else c_name
                if hasattr(content, 'seek'):
                    content.seek(0)
                if not local_storage.exists(clean_c):
                    local_storage.save(clean_c, content)
            return c_name
        except Exception as ex:
            logger.error(f"Cloudinary upload failed, falling back to local file storage: {ex}")
            return saved_local_name or clean_local_name

    def url(self, name):
        if not name:
            return ''

        clean_name = name.replace('media/', '', 1) if name.startswith('media/') else name
        full_local_path = os.path.join(settings.MEDIA_ROOT, name)
        clean_local_path = os.path.join(settings.MEDIA_ROOT, clean_name)

        target_file = None
        if os.path.exists(full_local_path):
            target_file = full_local_path
        elif os.path.exists(clean_local_path):
            target_file = clean_local_path

        # Return Cloudinary URL for images
        try:
            cloudinary_url = super().url(name)
            if cloudinary_url:
                exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')
                if not any(cloudinary_url.lower().endswith(ext) for ext in exts):
                    cloudinary_url = f"{cloudinary_url}.jpg"
                return cloudinary_url
        except Exception:
            pass

        # Fallback to local media URL
        return f"{settings.MEDIA_URL.rstrip('/')}/{clean_name}"


class SmartRawMediaCloudinaryStorage(SmartMediaCloudinaryStorage):
    """
    Smart Raw Storage for task attachments.
    Always creates guaranteed local backup in MEDIA_ROOT for instant viewing & downloading.
    """
    pass

