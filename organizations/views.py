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
@user_passes_test(lambda u: u.is_super_admin)
def delete_organization(request, org_id):
    if request.method == 'POST':
        confirm_text = request.POST.get('confirm_text', '').strip()
        org = get_object_or_404(Organization, id=org_id)

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
        org = get_object_or_404(Organization, id=org_id, status='marked_for_deletion')
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
        org = get_object_or_404(Organization, id=org_id, status='marked_for_deletion')

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
    org = get_object_or_404(Organization, id=org_id)
    org.status = 'approved'
    org.save()
    
    # Activate the admin user
    admin_user = org.users.filter(role='org_admin').first()
    if admin_user:
        admin_user.is_active = True
        admin_user.save()
        # Optionally send an email here
        
    messages.success(request, f'Organization {org.name} has been approved.')
    return redirect('pending_organizations')

@login_required
@user_passes_test(lambda u: u.is_super_admin)
def reject_organization(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
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
    
    org = get_object_or_404(Organization, id=org_id)
    users = org.users.filter(is_active=True).order_by('role', 'first_name')
    admin_users = users.filter(role__in=['super_admin', 'org_admin', 'president'])
    admin_name = ", ".join([u.get_full_name() or u.username for u in admin_users]) if admin_users.exists() else 'None Assigned'
    
    officers = []
    for u in users:
        officers.append({
            'id': u.id,
            'name': u.get_full_name() or u.username,
            'username': u.username,
            'email': u.email or 'N/A',
            'role': u.get_role_display(),
            'position': u.position_title,
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
        'admin_name': admin_user.get_full_name() or admin_user.username if admin_user else 'None Assigned',
        'admin_email': admin_user.email if admin_user and admin_user.email else 'N/A',
        'officers_count': users.count(),
        'tasks_count': tasks_count,
        'completed_tasks': completed_tasks,
        'positions': positions,
        'officers': officers,
    })

