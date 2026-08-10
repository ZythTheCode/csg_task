import os
import logging
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from cloudinary_storage.storage import MediaCloudinaryStorage, RawMediaCloudinaryStorage
import cloudinary.uploader

logger = logging.getLogger(__name__)


class SmartMediaCloudinaryStorage(MediaCloudinaryStorage):
    """
    Smart Media Storage that bridges Cloudinary and local media storage:
    1. Saves uploaded media to Cloudinary AND creates a local copy in MEDIA_ROOT.
    2. Auto-syncs legacy local files to Cloudinary on access if missing in Cloudinary.
    3. Seamlessly falls back to local media URLs if Cloudinary is offline.
    """

    def _save(self, name, content):
        # 1. Save local backup to MEDIA_ROOT
        try:
            local_storage = FileSystemStorage()
            clean_local_name = name.replace('media/', '', 1) if name.startswith('media/') else name
            if not local_storage.exists(clean_local_name):
                local_storage.save(clean_local_name, content)
                if hasattr(content, 'seek'):
                    content.seek(0)
        except Exception as ex:
            logger.warning(f"SmartMediaCloudinaryStorage local backup warning: {ex}")

        # 2. Upload to Cloudinary
        try:
            return super()._save(name, content)
        except Exception as ex:
            logger.error(f"Cloudinary upload failed, falling back to local file storage: {ex}")
            local_storage = FileSystemStorage()
            clean_local_name = name.replace('media/', '', 1) if name.startswith('media/') else name
            return local_storage.save(clean_local_name, content)

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

        # Auto-sync existing local media file to Cloudinary if marker missing
        if target_file:
            marker_file = target_file + '.cloudinary_synced'
            if not os.path.exists(marker_file):
                try:
                    pub_id_no_ext = os.path.splitext(name)[0]
                    with open(target_file, 'rb') as f:
                        res = cloudinary.uploader.upload(f, public_id=pub_id_no_ext, overwrite=True)
                        with open(marker_file, 'w') as mf:
                            mf.write(res.get('secure_url', ''))
                        logger.info(f"Auto-synced local media file to Cloudinary: {name}")
                except Exception as sync_ex:
                    logger.warning(f"Auto-sync to Cloudinary failed for {name}: {sync_ex}")

        # Return Cloudinary URL
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


class SmartRawMediaCloudinaryStorage(RawMediaCloudinaryStorage):
    """
    Smart Raw Storage for non-image task attachments (PDF, DOCX, XLSX, ZIP).
    """

    def _save(self, name, content):
        try:
            local_storage = FileSystemStorage()
            clean_local_name = name.replace('media/', '', 1) if name.startswith('media/') else name
            if not local_storage.exists(clean_local_name):
                local_storage.save(clean_local_name, content)
                if hasattr(content, 'seek'):
                    content.seek(0)
        except Exception as ex:
            logger.warning(f"SmartRawMediaCloudinaryStorage local backup warning: {ex}")

        try:
            return super()._save(name, content)
        except Exception as ex:
            logger.error(f"Cloudinary raw upload failed, falling back to local: {ex}")
            local_storage = FileSystemStorage()
            clean_local_name = name.replace('media/', '', 1) if name.startswith('media/') else name
            return local_storage.save(clean_local_name, content)

    def url(self, name):
        if not name:
            return ''
        clean_name = name.replace('media/', '', 1) if name.startswith('media/') else name
        try:
            url_str = super().url(name)
            if url_str:
                return url_str
        except Exception:
            pass
        return f"{settings.MEDIA_URL.rstrip('/')}/{clean_name}"

