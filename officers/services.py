from django.db import transaction
from officers.models import Officer, Position
from core.services.audit import log_activity


class OfficerService:
    @staticmethod
    @transaction.atomic
    def create_position(title, initials, description='', organization=None, request=None):
        pos = Position.objects.create(
            title=title,
            initials=initials,
            description=description,
            organization=organization
        )
        log_activity(request, 'POSITION_CREATE', f"Created position '{title}' ({pos.get_initials()})", resource_type='Position', resource_id=pos.id)
        return pos

    @staticmethod
    @transaction.atomic
    def update_position(position, title, initials, description='', request=None):
        position.title = title
        position.initials = initials
        position.description = description
        position.save()
        log_activity(request, 'POSITION_UPDATE', f"Updated position '{title}' ({position.get_initials()})", resource_type='Position', resource_id=position.id)
        return position
