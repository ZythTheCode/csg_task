import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'csg_project.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")
print(f"EMAIL_HOST_USER: '{settings.EMAIL_HOST_USER}'")
print(f"EMAIL_HOST_PASSWORD set: {bool(settings.EMAIL_HOST_PASSWORD)}")
print(f"DEFAULT_FROM_EMAIL: '{settings.DEFAULT_FROM_EMAIL}'")

try:
    print("Attempting to send test email...")
    sent = send_mail(
        subject="Test CSG Nudge Email",
        message="This is a test nudge email from CSG Task Management System.",
        from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
        recipient_list=["csgtasks2026@gmail.com"],
        fail_silently=False
    )
    print(f"Result: {sent} email(s) sent successfully!")
except Exception as e:
    print(f"Email send error: {e}")
