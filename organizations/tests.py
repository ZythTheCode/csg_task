from django.test import TestCase
from organizations.forms import OrganizationRegistrationForm
from organizations.models import Organization
from accounts.models import User
from officers.models import Officer, Position

class OrganizationRegistrationFormTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Existing Org", abbreviation="EO", description="Desc")
        self.user = User.objects.create_user(username="existing_user", email="existing@test.com", password="password", organization=self.org)
        self.pos = Position.objects.create(title="President", organization=self.org)
        self.officer = Officer.objects.create(user=self.user, student_id="STU123", position=self.pos)

    def test_duplicate_student_id_validation(self):
        form_data = {
            'name': 'New Unique Org',
            'abbreviation': 'NUO',
            'description': 'Unique Desc',
            'admin_first_name': 'John',
            'admin_last_name': 'Doe',
            'admin_student_id': 'STU123',  # Duplicate!
            'admin_email': 'new@test.com',
            'admin_username': 'newuser',
            'admin_password': 'password123',
        }
        form = OrganizationRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('admin_student_id', form.errors)
        self.assertIn('This Student ID is already registered', form.errors['admin_student_id'][0])

    def test_duplicate_org_name_validation(self):
        form_data = {
            'name': 'Existing Org',  # Duplicate!
            'abbreviation': 'BRANDNEW',
            'description': 'Unique Desc',
            'admin_first_name': 'John',
            'admin_last_name': 'Doe',
            'admin_student_id': 'UNIQUE999',
            'admin_email': 'new@test.com',
            'admin_username': 'newuser',
            'admin_password': 'password123',
        }
        form = OrganizationRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_valid_registration(self):
        form_data = {
            'name': 'Brand New Org',
            'abbreviation': 'BNO',
            'description': 'Brand New Description',
            'admin_first_name': 'John',
            'admin_last_name': 'Doe',
            'admin_student_id': 'UNIQUE999',
            'admin_email': 'unique@test.com',
            'admin_username': 'uniqueuser',
            'admin_password': 'password123',
        }
        form = OrganizationRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        org = form.save()
        self.assertEqual(org.name, 'Brand New Org')
        self.assertEqual(org.status, 'pending')
        admin_user = User.objects.get(username='uniqueuser')
        self.assertEqual(admin_user.organization, org)
        self.assertTrue(Officer.objects.filter(user=admin_user, student_id='UNIQUE999').exists())
