import logging
from core.models import ActivityLog

logger = logging.getLogger('csg.audit')


def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    if not request:
        return ''
    return request.META.get('HTTP_USER_AGENT', '')[:255]


def log_activity(request, action, description, resource_type='', resource_id='', status='success'):
    """
    Centralized service function to record structured activity/audit logs.
    """
    user = getattr(request, 'user', None) if request else None
    if user and not user.is_authenticated:
        user = None

    organization = getattr(user, 'organization', None) if user else None

    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    try:
        log_entry = ActivityLog.objects.create(
            user=user,
            organization=organization,
            action=action,
            description=description,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else '',
            ip_address=ip_address,
            user_agent=user_agent,
            status=status
        )
        logger.info(f"AUDIT LOG: [{action}] user={user} org={organization} ip={ip_address} desc='{description}'")
        return log_entry
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}", exc_info=True)
        return None
