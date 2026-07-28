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
