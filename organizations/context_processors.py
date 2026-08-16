from organizations.models import Organization
from core.cache_utils import safe_cache_get


def organization_processor(request):
    # Unauthenticated users: return immediately with empty defaults (zero queries)
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {
            'current_organization': None,
            'all_approved_organizations': [],
        }

    user = request.user

    # Non-super-admin: return organization from already-loaded User FK (zero additional queries)
    if not user.is_super_admin:
        return {
            'current_organization': user.organization,
            'all_approved_organizations': [],
        }

    # Super-admin: cache approved organizations list with 60s TTL
    all_orgs = safe_cache_get(
        'approved_orgs_list',
        lambda: list(
            Organization.objects.filter(status='approved')
            .only('id', 'name', 'abbreviation')
            .order_by('name')
        ),
        timeout=60,
    )

    # Determine current organization from session or user FK
    active_org_id = request.session.get('active_org_id')
    if active_org_id:
        # Try to find the active org in the already-cached list to avoid a query
        curr_org = next(
            (org for org in all_orgs if org.pk == active_org_id),
            None,
        )
        if curr_org is None:
            curr_org = user.organization
    else:
        curr_org = user.organization

    return {
        'current_organization': curr_org,
        'all_approved_organizations': all_orgs,
    }
