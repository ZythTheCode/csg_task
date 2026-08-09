from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from datetime import timedelta
from .models import Organization
from .forms import OrganizationRegistrationForm
from accounts.models import User

def register_organization(request):
    if request.method == 'POST':
        form = OrganizationRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your organization has been registered and is pending approval from the Super Admin.')
            return redirect('login')
    else:
        form = OrganizationRegistrationForm()
    
    return render(request, 'organizations/register.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_super_admin)
def pending_organizations(request):
    # Lazy cleanup: permanently delete orgs marked for deletion > 24 hours ago
    cutoff_time = timezone.now() - timedelta(days=1)
    Organization.objects.filter(status='marked_for_deletion', marked_for_deletion_at__lt=cutoff_time).delete()

    pending_orgs = Organization.objects.filter(status='pending').order_by('-created_at')
    approved_orgs = Organization.objects.filter(status='approved').order_by('-created_at')
    deleting_orgs = Organization.objects.filter(status='marked_for_deletion').order_by('-marked_for_deletion_at')

    return render(request, 'organizations/pending_list.html', {
        'pending_orgs': pending_orgs,
        'approved_orgs': approved_orgs,
        'deleting_orgs': deleting_orgs,
    })

@login_required
@login_required
@user_passes_test(lambda u: u.is_super_admin)
def delete_organization(request, org_id):
    if request.method == 'POST':
        confirm_text = request.POST.get('confirm_text', '').strip()
        org = Organization.objects.filter(id=org_id).first()
        if not org:
            messages.warning(request, 'This organization no longer exists or has already been deleted.')
            return redirect('pending_organizations')

        if confirm_text != 'DELETE':
            messages.error(request, 'You must type DELETE to confirm.')
            return redirect('pending_organizations')

        org_name = org.name
        org.status = 'marked_for_deletion'
        org.marked_for_deletion_at = timezone.now()
        org.save()
        messages.warning(request, f'Organization "{org_name}" marked for deletion. It will be permanently removed in 24 hours.')
    return redirect('pending_organizations')

@login_required
@user_passes_test(lambda u: u.is_super_admin)
def restore_organization(request, org_id):
    if request.method == 'POST':
        org = Organization.objects.filter(id=org_id, status='marked_for_deletion').first()
        if not org:
            messages.warning(request, 'This organization was not found in deletion queue.')
            return redirect('pending_organizations')
        org.status = 'approved'
        org.marked_for_deletion_at = None
        org.save()
        messages.success(request, f'Organization "{org.name}" has been restored.')
    return redirect('pending_organizations')

@login_required
@user_passes_test(lambda u: u.is_super_admin)
def force_delete_organization(request, org_id):
    if request.method == 'POST':
        confirm_text = request.POST.get('confirm_text', '').strip()
        org = Organization.objects.filter(id=org_id, status='marked_for_deletion').first()
        if not org:
            messages.warning(request, 'This organization was not found in deletion queue.')
            return redirect('pending_organizations')

        if confirm_text != 'DELETE':
            messages.error(request, 'You must type DELETE to confirm immediate deletion.')
            return redirect('pending_organizations')

        org_name = org.name
        org.delete()
        messages.success(request, f'Organization "{org_name}" has been permanently force deleted.')
    return redirect('pending_organizations')

@login_required
@user_passes_test(lambda u: u.is_super_admin)
def approve_organization(request, org_id):
    org = Organization.objects.filter(id=org_id).first()
    if not org:
        messages.warning(request, 'This organization no longer exists or has already been deleted.')
        return redirect('pending_organizations')
    org.status = 'approved'
    org.save()
    
    # Activate the admin user
    admin_user = org.users.filter(role='org_admin').first()
    if admin_user:
        admin_user.is_active = True
        admin_user.save()
        
    messages.success(request, f'Organization {org.name} has been approved.')
    return redirect('pending_organizations')

@login_required
@user_passes_test(lambda u: u.is_super_admin)
def reject_organization(request, org_id):
    org = Organization.objects.filter(id=org_id).first()
    if not org:
        messages.warning(request, 'This organization no longer exists or has already been deleted.')
        return redirect('pending_organizations')
    org.status = 'rejected'
    org.save()
    messages.info(request, f'Organization {org.name} has been rejected.')
    return redirect('pending_organizations')

@login_required
@user_passes_test(lambda u: u.is_super_admin)
def organization_detail_json(request, org_id):
    from django.http import JsonResponse
    from tasks.models import Task
    from officers.models import Position
    
    org = Organization.objects.filter(id=org_id).first()
    if not org:
        return JsonResponse({'error': 'Organization not found.'}, status=404)

    users = org.users.filter(is_active=True).exclude(role__in=['super_admin', 'super_super_admin']).order_by('role', 'first_name')
    current_admin = org.users.filter(role='org_admin', is_active=True).first()
    current_admin_name = (current_admin.get_full_name() or current_admin.username) if current_admin else 'None (Unassigned)'
    
    officers = []
    for u in users:
        officers.append({
            'id': u.id,
            'name': u.get_full_name() or u.username,
            'username': u.username,
            'email': u.email or 'N/A',
            'role': u.get_role_display(),
            'position': u.position_title,
            'is_current_admin': (current_admin and u.id == current_admin.id),
        })

    tasks_count = Task.objects.filter(organization=org).count()
    completed_tasks = Task.objects.filter(organization=org, status='completed').count()
    positions = list(Position.objects.filter(organization=org).values_list('title', flat=True))

    return JsonResponse({
        'id': org.id,
        'name': org.name,
        'abbreviation': org.abbreviation or '',
        'display_name': org.display_name,
        'description': org.description or 'No description provided.',
        'status': org.get_status_display(),
        'created_at': org.created_at.strftime('%b %d, %Y'),
        'admin_name': current_admin_name,
        'current_admin': {
            'id': current_admin.id,
            'name': current_admin.get_full_name() or current_admin.username,
            'username': current_admin.username,
            'position': current_admin.position_title
        } if current_admin else None,
        'officers_count': users.count(),
        'tasks_count': tasks_count,
        'completed_tasks': completed_tasks,
        'positions': positions,
        'officers': officers,
    })

@login_required
def switch_organization(request, org_id):
    if request.user.is_super_admin:
        org = Organization.objects.filter(id=org_id, status='approved').first()
        if org:
            request.session['active_org_id'] = org.id
            messages.success(request, f"Switched active workspace dashboard to: {org.name}")
        else:
            messages.warning(request, "Organization not found.")
    return redirect(request.META.get('HTTP_REFERER', 'core:dashboard'))


@login_required
def reassign_org_admin(request, org_id):
    if request.method == 'POST':
        org = Organization.objects.filter(id=org_id).first()
        if not org:
            messages.warning(request, 'This organization no longer exists or has already been deleted.')
            return redirect('pending_organizations')

        if not (request.user.is_super_admin or (request.user.role == 'org_admin' and request.user.organization == org)):
            messages.error(request, 'Permission denied.')
            return redirect('core:dashboard')

        new_admin_id = request.POST.get('new_admin_id')
        if not new_admin_id:
            messages.error(request, 'Please select an officer to assign as Org Admin.')
            return redirect(request.META.get('HTTP_REFERER', 'pending_organizations'))

        new_admin = get_object_or_404(User, id=new_admin_id, organization=org)
        
        if not request.user.is_super_admin:
            password = request.POST.get('password', '')
            if not request.user.check_password(password):
                messages.error(request, 'Invalid password. Handover failed.')
                return redirect(request.META.get('HTTP_REFERER', 'core:settings'))

        # Demote existing org_admin in this org to executive
        existing_admins = User.objects.filter(organization=org, role='org_admin').exclude(id=new_admin.id)
        for prev in existing_admins:
            prev.role = 'executive'
            prev.save(update_fields=['role'])

        # Promote new admin
        new_admin.role = 'org_admin'
        new_admin.is_active = True
        new_admin.save(update_fields=['role', 'is_active'])

        from core.services.audit import log_activity
        log_activity(request, 'ORG_ADMIN_TRANSFER', f"Transferred Org Admin role for '{org.name}' to '{new_admin.get_full_name() or new_admin.username}'", resource_type='Organization', resource_id=org.id)

        messages.success(request, f"Org Admin role for '{org.name}' has been successfully assigned to {new_admin.get_full_name() or new_admin.username}.")
    return redirect(request.META.get('HTTP_REFERER', 'pending_organizations'))


