from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from organizations.models import Organization
from officers.models import Position, Officer
from tasks.models import Task, TaskAssignment, TaskComment
from notifications.models import Notification
import datetime

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds the database with current local CSG organizations, positions, users, officers, and tasks'

    def handle(self, *args, **kwargs):
        self.stdout.write('[*] Seeding CSG Task Management System with local snapshot data...')

        # ── ORGANIZATIONS ─────────────────────────
        orgs_data = [
            {'name': 'Central Student Government', 'abbreviation': 'CSG', 'description': 'Central Student Government Main Organization', 'status': 'approved'},
            {'name': 'CO:DE', 'abbreviation': 'CO:DE', 'description': 'Computer Developers and Engineers Society', 'status': 'approved'},
            {'name': 'ACES', 'abbreviation': 'ACES', 'description': 'Association of Civil Engineering Students', 'status': 'approved'},
        ]
        org_map = {}
        for o_info in orgs_data:
            org = Organization.objects.filter(id=2).first() if o_info['abbreviation'] == 'CSG' else None
            if not org:
                org = Organization.objects.filter(abbreviation=o_info['abbreviation']).first() or \
                      Organization.objects.filter(name__iexact=o_info['name']).first()
            if not org:
                org = Organization.objects.create(
                    name=o_info['name'],
                    abbreviation=o_info['abbreviation'],
                    description=o_info['description'],
                    status=o_info['status']
                )
            else:
                if not org.abbreviation:
                    org.abbreviation = o_info['abbreviation']
                org.status = o_info['status']
                org.save()
            org_map[o_info['abbreviation']] = org
            org_map[o_info['name']] = org
            self.stdout.write(f'  [+] Organization: {org.name} ({org.abbreviation}) [{org.status}]')

        csg_org = org_map.get('CSG')
        code_org = org_map.get('CO:DE')
        aces_org = org_map.get('ACES')

        # ── POSITIONS ────────────────────────────
        positions_data = [
            {'title': 'President', 'initials': 'PRES', 'org': csg_org},
            {'title': 'Vice President', 'initials': 'VP', 'org': csg_org},
            {'title': 'Secretary', 'initials': 'SEC', 'org': csg_org},
            {'title': 'Treasurer', 'initials': 'TREAS', 'org': csg_org},
            {'title': 'Auditor', 'initials': 'AUD', 'org': csg_org},
            {'title': 'P.R.O.', 'initials': 'PRO', 'org': csg_org},
            {'title': 'Business Manager', 'initials': 'BM', 'org': csg_org},
            {'title': 'Executive Assistant', 'initials': 'EA', 'org': csg_org},
            {'title': 'Assistant Secretary', 'initials': 'ASEC', 'org': csg_org},
            {'title': 'Assistant Treasurer', 'initials': 'ATREAS', 'org': csg_org},
            {'title': 'Events Manager', 'initials': 'EM', 'org': csg_org},
            {'title': 'Graphics and Media', 'initials': 'GM', 'org': csg_org},
            {'title': 'P.V.', 'initials': 'PV', 'org': csg_org},
            {'title': 'Elected Officer', 'initials': 'EO', 'org': csg_org},
            {'title': 'Chief Technology Officer', 'initials': 'CTO', 'org': code_org},
            {'title': 'Vice President', 'initials': 'VP', 'org': code_org},
            {'title': 'President', 'initials': 'PRES', 'org': aces_org},
        ]

        pos_map = {}
        for p_info in positions_data:
            key = (p_info['title'], p_info['org'].name if p_info['org'] else None)
            pos, _ = Position.objects.get_or_create(
                title=p_info['title'],
                organization=p_info['org'],
                defaults={'initials': p_info['initials']}
            )
            if p_info['initials'] and pos.initials != p_info['initials']:
                pos.initials = p_info['initials']
                pos.save()
            pos_map[key] = pos
            self.stdout.write(f'  [+] Position: {pos.title} [{pos.organization.name if pos.organization else "Global"}]')

        # ── USERS ─────────────────────────────────
        users_data = [
            {'username': 'admin', 'first_name': 'Admin', 'last_name': 'CSG', 'email': 'admin@csg.edu.ph', 'role': 'super_admin', 'org': csg_org},
            {'username': 'president', 'first_name': 'Zyron Asty', 'last_name': 'Bustamante', 'email': 'president@csg.edu.ph', 'role': 'president', 'org': csg_org},
            {'username': 'vp_juan', 'first_name': 'Boris', 'last_name': 'Alano', 'email': 'juan@csg.edu.ph', 'role': 'executive', 'org': csg_org},
            {'username': 'sec_anna', 'first_name': 'Jazel', 'last_name': 'Moradas', 'email': 'anna@csg.edu.ph', 'role': 'executive', 'org': csg_org},
            {'username': 'treas_ben', 'first_name': 'Benjamin', 'last_name': 'Torres', 'email': 'ben@csg.edu.ph', 'role': 'executive', 'org': csg_org},
            {'username': 'auditor_lea', 'first_name': 'Lea', 'last_name': 'Garcia', 'email': 'lea@csg.edu.ph', 'role': 'executive', 'org': csg_org},
            {'username': 'pro_chris', 'first_name': 'Christopher', 'last_name': 'Lim', 'email': 'chris@csg.edu.ph', 'role': 'executive', 'org': csg_org},
            {'username': 'bm_rose', 'first_name': 'Roselyn', 'last_name': 'Cruz', 'email': 'rose@csg.edu.ph', 'role': 'executive', 'org': csg_org},
            {'username': 'ea_mark', 'first_name': 'Mark', 'last_name': 'Villanueva', 'email': 'mark@csg.edu.ph', 'role': 'executive', 'org': csg_org},
            {'username': 'ext_mark', 'first_name': 'Mark', 'last_name': 'Villanueva', 'email': 'mark@csg.edu.ph', 'role': 'executive', 'org': csg_org},
            {'username': 'asec_jen', 'first_name': 'Jennifer', 'last_name': 'Bautista', 'email': 'jen@csg.edu.ph', 'role': 'committee_head', 'org': csg_org},
            {'username': 'atreas_mike', 'first_name': 'Michael', 'last_name': 'Ramos', 'email': 'mike@csg.edu.ph', 'role': 'committee_head', 'org': csg_org},
            {'username': 'codeadmin', 'first_name': 'Bian Avan', 'last_name': 'Toledo', 'email': 'rc.maurice.montano@cvsu.edu.ph', 'role': 'org_admin', 'org': code_org},
            {'username': 'em_david', 'first_name': 'David', 'last_name': 'Flores', 'email': 'david@csg.edu.ph', 'role': 'committee_head', 'org': code_org},
            {'username': 'gm_sophia', 'first_name': 'Sophia', 'last_name': 'Mendoza', 'email': 'sophia@csg.edu.ph', 'role': 'committee_head', 'org': code_org},
            {'username': 'pv_alex', 'first_name': 'Alex', 'last_name': 'Navarro', 'email': 'alex@csg.edu.ph', 'role': 'executive', 'org': code_org},
            {'username': 'acesadmin', 'first_name': 'John', 'last_name': 'Doe', 'email': 'mmauricemontano16@gmail.com', 'role': 'org_admin', 'org': aces_org},
        ]

        user_map = {}
        for u_info in users_data:
            is_su = True if u_info['role'] == 'super_admin' else False
            user, created = User.objects.get_or_create(
                username=u_info['username'],
                defaults={
                    'first_name': u_info['first_name'],
                    'last_name': u_info['last_name'],
                    'email': u_info['email'],
                    'role': u_info['role'],
                    'organization': u_info['org'],
                    'is_superuser': is_su,
                    'is_staff': is_su,
                    'is_active': True
                }
            )
            if created:
                user.set_password('csg2025')
                user.save()
            else:
                user.first_name = u_info['first_name']
                user.last_name = u_info['last_name']
                user.role = u_info['role']
                user.organization = u_info['org']
                if is_su:
                    user.is_superuser = True
                    user.is_staff = True
                user.save(update_fields=['first_name', 'last_name', 'role', 'organization', 'is_superuser', 'is_staff'])
            user_map[u_info['username']] = user
            self.stdout.write(f'  [+] User: {user.username} ({user.get_role_display()}) - Org: {user.organization.name if user.organization else "None"}')

        # ── OFFICERS ─────────────────────────────
        officers_data = [
            {'username': 'admin', 'student_id': 'SA-2026-0001', 'pos_title': None, 'org': csg_org},
            {'username': 'president', 'student_id': '2024-0001', 'pos_title': 'President', 'org': csg_org},
            {'username': 'vp_juan', 'student_id': '2024-0002', 'pos_title': 'Vice President', 'org': csg_org},
            {'username': 'sec_anna', 'student_id': '2024-0003', 'pos_title': 'Secretary', 'org': csg_org},
            {'username': 'treas_ben', 'student_id': '2024-0004', 'pos_title': 'Treasurer', 'org': csg_org},
            {'username': 'auditor_lea', 'student_id': '2024-0005', 'pos_title': 'Auditor', 'org': csg_org},
            {'username': 'pro_chris', 'student_id': '2024-0006', 'pos_title': 'P.R.O.', 'org': csg_org},
            {'username': 'bm_rose', 'student_id': '2024-0007', 'pos_title': 'Business Manager', 'org': csg_org},
            {'username': 'ea_mark', 'student_id': '2024-0008', 'pos_title': 'Executive Assistant', 'org': csg_org},
            {'username': 'asec_jen', 'student_id': '2024-0009', 'pos_title': 'Assistant Secretary', 'org': csg_org},
            {'username': 'atreas_mike', 'student_id': '2024-0010', 'pos_title': 'Assistant Treasurer', 'org': csg_org},
            {'username': 'em_david', 'student_id': '2024-0011', 'pos_title': 'Events Manager', 'org': code_org},
            {'username': 'gm_sophia', 'student_id': '2024-0012', 'pos_title': 'Graphics and Media', 'org': code_org},
            {'username': 'pv_alex', 'student_id': '2024-0013', 'pos_title': 'P.V.', 'org': code_org},
            {'username': 'codeadmin', 'student_id': '2024102365', 'pos_title': 'Chief Technology Officer', 'org': code_org},
            {'username': 'acesadmin', 'student_id': '202210267', 'pos_title': 'President', 'org': aces_org},
        ]

        for off_info in officers_data:
            user = user_map.get(off_info['username'])
            if user:
                pos = pos_map.get((off_info['pos_title'], off_info['org'].name if off_info['org'] else None))
                if pos:
                    existing_officer_with_pos = Officer.objects.filter(position=pos).exclude(user=user).first()
                    if existing_officer_with_pos:
                        existing_officer_with_pos.position = None
                        existing_officer_with_pos.save(update_fields=['position'])

                officer, _ = Officer.objects.get_or_create(
                    user=user,
                    defaults={'student_id': off_info['student_id'], 'position': pos}
                )
                officer.student_id = off_info['student_id']
                officer.position = pos
                officer.save()

        # ── TASKS ────────────────────────────────
        admin_user = user_map['admin']
        tasks_data = [
            {'task_number': '2026-0002', 'title': 'Website Portal Infrastructure Upgrade', 'desc': 'Deploy Vite and Django backend updates for student portal.', 'priority': 'urgent', 'status': 'not_started', 'progress': 0, 'due_date': None, 'org': code_org, 'created_by': 'codeadmin', 'assignees': ['em_david']},
            {'task_number': '2026-0001', 'title': 'CO:DE Hackathon 2026 Preparation', 'desc': 'Organize sponsorship and challenge tracks for the upcoming hackathon.', 'priority': 'high', 'status': 'not_started', 'progress': 45, 'due_date': None, 'org': code_org, 'created_by': 'codeadmin', 'assignees': ['em_david', 'codeadmin']},
            {'task_number': '2026-0027', 'title': 'from vp', 'desc': 'fdsfae', 'priority': 'medium', 'status': 'to_advisers', 'progress': 18, 'due_date': '2026-07-31', 'org': csg_org, 'created_by': 'vp_juan', 'assignees': ['atreas_mike', 'asec_jen', 'vp_juan']},
            {'task_number': '2026-0026', 'title': 'Mid-Year Constitutional Review Assembly', 'desc': 'Conduct mid-year review of council resolutions and bylaws.', 'priority': 'urgent', 'status': 'processing', 'progress': 100, 'due_date': '2026-07-24', 'org': csg_org, 'created_by': 'admin', 'assignees': ['em_david', 'treas_ben']},
            {'task_number': '2026-0025', 'title': 'Annual Campus Clean-up Drive Logistics', 'desc': 'Coordinate volunteer registration and equipment distribution for campus cleanup.', 'priority': 'medium', 'status': 'completed', 'progress': 100, 'due_date': '2026-08-15', 'org': csg_org, 'created_by': 'admin', 'assignees': ['ea_mark']},
            {'task_number': '2026-0024', 'title': 'Student Grievance Hotline Setup', 'desc': 'Establish an online feedback form and ticketing system for student complaints.', 'priority': 'high', 'status': 'not_started', 'progress': 47, 'due_date': '2026-08-05', 'org': csg_org, 'created_by': 'admin', 'assignees': ['asec_jen', 'ea_mark']},
            {'task_number': '2026-0023', 'title': 'Adviser Endorsement for Leadership Seminar', 'desc': 'Obtain official signatures from faculty advisers for the leadership workshop.', 'priority': 'medium', 'status': 'completed', 'progress': 100, 'due_date': '2026-07-30', 'org': csg_org, 'created_by': 'admin', 'assignees': ['em_david', 'gm_sophia', 'bm_rose']},
            {'task_number': '2026-0022', 'title': 'Office Supplies Requisition for CSG Secretariat', 'desc': 'Submit requisition forms for printer ink, paper, and organizational materials.', 'priority': 'low', 'status': 'supply', 'progress': 10, 'due_date': '2026-08-07', 'org': csg_org, 'created_by': 'admin', 'assignees': ['em_david', 'pro_chris', 'auditor_lea']},
            {'task_number': '2026-0021', 'title': 'PPSS Sound System Procurement', 'desc': 'Coordinate with Physical Plant & Site Services for AV equipment setup.', 'priority': 'high', 'status': 'ppss', 'progress': 50, 'due_date': '2026-08-01', 'org': csg_org, 'created_by': 'admin', 'assignees': ['em_david', 'ext_mark']},
            {'task_number': '2026-0020', 'title': 'OCA Event Approval for Cultural Night', 'desc': 'Prepare and submit event proposal paperwork to the Office of Cultural Affairs.', 'priority': 'urgent', 'status': 'oca', 'progress': 60, 'due_date': '2026-07-29', 'org': csg_org, 'created_by': 'admin', 'assignees': ['ext_mark']},
            {'task_number': '2026-0019', 'title': 'OSAS Facility Request Endorsement', 'desc': 'Submit formal facility reservation for the upcoming University Student Summit.', 'priority': 'medium', 'status': 'osas', 'progress': 40, 'due_date': '2026-07-31', 'org': csg_org, 'created_by': 'admin', 'assignees': ['asec_jen', 'pro_chris']},
            {'task_number': '2026-0018', 'title': 'Student Council Budget Audit Q1', 'desc': 'Review and process expense vouchers and receipts for Q1 student council events.', 'priority': 'high', 'status': 'accounting', 'progress': 25, 'due_date': '2026-08-03', 'org': csg_org, 'created_by': 'admin', 'assignees': ['em_david']},
            {'task_number': '2026-0017', 'title': 'Campus Eco-Waste Management Drive', 'desc': 'Organize campus-wide segregated recycling bins and information dissemination.', 'priority': 'medium', 'status': 'not_started', 'progress': 0, 'due_date': '2026-08-09', 'org': csg_org, 'created_by': 'admin', 'assignees': ['gm_sophia']},
            {'task_number': '2026-0016', 'title': 'Cook Ilocos Empanada', 'desc': 'hkdsjhfjkdshfaweafae fesfesfesfe', 'priority': 'low', 'status': 'not_started', 'progress': 0, 'due_date': '2026-07-31', 'org': csg_org, 'created_by': 'admin', 'assignees': ['vp_juan', 'treas_ben', 'auditor_lea', 'sec_anna', 'president']},
            {'task_number': '2026-0015', 'title': 'Community Service Event', 'desc': 'Coordinate the semestral community service activity.', 'priority': 'medium', 'status': 'to_advisers', 'progress': 0, 'due_date': '2026-08-20', 'org': csg_org, 'created_by': 'admin', 'assignees': ['president']},
            {'task_number': '2026-0014', 'title': 'Grant Application Review', 'desc': 'Review and process grant applications from student organizations.', 'priority': 'high', 'status': 'not_started', 'progress': 0, 'due_date': '2026-08-13', 'org': csg_org, 'created_by': 'admin', 'assignees': ['pro_chris', 'president']},
            {'task_number': '2026-0013', 'title': 'Membership Drive', 'desc': 'Plan and execute the membership drive for new student members.', 'priority': 'low', 'status': 'completed', 'progress': 100, 'due_date': '2026-07-13', 'org': csg_org, 'created_by': 'admin', 'assignees': ['sec_anna']},
        ]

        for t_info in tasks_data:
            creator = user_map.get(t_info['created_by'], admin_user)
            due_dt = datetime.datetime.strptime(t_info['due_date'], '%Y-%m-%d').date() if t_info['due_date'] else None
            
            task, created = Task.objects.get_or_create(
                task_number=t_info['task_number'],
                defaults={
                    'title': t_info['title'],
                    'description': t_info['desc'],
                    'priority': t_info['priority'],
                    'status': t_info['status'],
                    'progress': t_info['progress'],
                    'due_date': due_dt,
                    'organization': t_info['org'],
                    'created_by': creator,
                }
            )
            if not created:
                task.title = t_info['title']
                task.description = t_info['desc']
                task.priority = t_info['priority']
                task.status = t_info['status']
                task.progress = t_info['progress']
                task.due_date = due_dt
                task.organization = t_info['org']
                task.save()

            for assignee_username in t_info['assignees']:
                off_user = user_map.get(assignee_username)
                if off_user:
                    TaskAssignment.objects.get_or_create(
                        task=task,
                        officer=off_user,
                        defaults={'assigned_by': creator}
                    )
            self.stdout.write(f'  [+] Task: [{task.task_number}] {task.title} ({task.organization.name if task.organization else "Global"})')

        self.stdout.write(self.style.SUCCESS('\n[OK] Seed complete! Local snapshot data synced.'))