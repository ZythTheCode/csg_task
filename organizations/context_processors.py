from django.core.cache import cache
from organizations.models import Organization


def organization_processor(request):
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {}

    user = request.user
    context = {}

    if user.is_super_admin:
        # Cached approved orgs list (TTL 60s)
        cache_key = 'approved_orgs_list'
        all_orgs = cache.get(cache_key)
        if all_orgs is None:
            all_orgs = list(Organization.objects.filter(status='approved').only('id', 'name', 'abbreviation').order_by('name'))
            cache.set(cache_key, all_orgs, 60)
        context['all_approved_organizations'] = all_orgs

        active_org_id = request.session.get('active_org_id')
        if active_org_id:
            # Find from cached list to avoid extra DB query on cache hit
            curr_org = next((o for o in all_orgs if o.id == active_org_id), None)
            if curr_org is None:
                curr_org = user.organization
            context['current_organization'] = curr_org
        else:
            context['current_organization'] = user.organization
    else:
        context['current_organization'] = user.organization

    return context
