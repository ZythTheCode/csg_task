from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
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
    orgs = Organization.objects.filter(status='pending')
    return render(request, 'organizations/pending_list.html', {'orgs': orgs})

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
