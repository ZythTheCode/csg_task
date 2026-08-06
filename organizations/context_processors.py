from organizations.models import Organization

def organization_processor(request):
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {}
    
    user = request.user
    context = {}
    
    if user.is_super_admin:
        all_orgs = Organization.objects.filter(status='approved').order_by('name')
        context['all_approved_organizations'] = all_orgs
        
        active_org_id = request.session.get('active_org_id')
        if active_org_id:
            curr_org = Organization.objects.filter(id=active_org_id).first()
            context['current_organization'] = curr_org if curr_org else user.organization
        else:
            context['current_organization'] = user.organization
    else:
        context['current_organization'] = user.organization
        
    return context
