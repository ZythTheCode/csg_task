from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from officers.models import Position, Officer
from tasks.models import Task, TaskAssignment, TaskComment
from notifications.models import Notification
import random
import datetime

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds the database with updated CSG positions and sample data'

    def handle(self, *args, **kwargs):
        self.stdout.write('[*] Seeding CSG Task Management System...')

        # ── POSITIONS ────────────────────────────
        positions_titles = [
            'President',
            'Vice President',
            'Secretary',
            'Treasurer',
            'Auditor',
            'P.R.O.',
            'Business Manager',
            'Executive Assistant',
            'Assistant Secretary',
            'Assistant Treasurer',
            'Events Manager',
            'Graphics and Media',
            'P.V.',
        ]

        # Clear out old positions and re-create updated list
        positions = {}
        for title in positions_titles:
            pos, _ = Position.objects.get_or_create(title=title)
            positions[title] = pos

        # Remove any positions not in the new list
        Position.objects.exclude(title__in=positions_titles).delete()

        # ── USERS & OFFICERS ─────────────────────
        users_data = [
            ('admin', 'Admin', 'CSG', 'admin@csg.edu.ph', 'super_admin', '2024-9000', 'President'),
            ('president', 'Maria', 'Santos', 'president@csg.edu.ph', 'president', '2024-0001', 'President'),
            ('vp_juan', 'Juan', 'Dela Cruz', 'juan@csg.edu.ph', 'executive', '2024-0002', 'Vice President'),
            ('sec_anna', 'Anna', 'Reyes', 'anna@csg.edu.ph', 'executive', '2024-0003', 'Secretary'),
            ('treas_ben', 'Benjamin', 'Torres', 'ben@csg.edu.ph', 'executive', '2024-0004', 'Treasurer'),
            ('auditor_lea', 'Lea', 'Garcia', 'lea@csg.edu.ph', 'executive', '2024-0005', 'Auditor'),
            ('pro_chris', 'Christopher', 'Lim', 'chris@csg.edu.ph', 'executive', '2024-0006', 'P.R.O.'),
            ('bm_rose', 'Roselyn', 'Cruz', 'rose@csg.edu.ph', 'executive', '2024-0007', 'Business Manager'),
            ('ea_mark', 'Mark', 'Villanueva', 'mark@csg.edu.ph', 'executive', '2024-0008', 'Executive Assistant'),
            ('asec_jen', 'Jennifer', 'Bautista', 'jen@csg.edu.ph', 'committee_head', '2024-0009', 'Assistant Secretary'),
            ('atreas_mike', 'Michael', 'Ramos', 'mike@csg.edu.ph', 'committee_head', '2024-0010', 'Assistant Treasurer'),
            ('em_david', 'David', 'Flores', 'david@csg.edu.ph', 'committee_head', '2024-0011', 'Events Manager'),
            ('gm_sophia', 'Sophia', 'Mendoza', 'sophia@csg.edu.ph', 'committee_head', '2024-0012', 'Graphics and Media'),
            ('pv_alex', 'Alex', 'Navarro', 'alex@csg.edu.ph', 'executive', '2024-0013', 'P.V.'),
        ]

        officers_list = []
        for username, first, last, email, role, sid, pos_title in users_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first, 'last_name': last,
                    'email': email, 'role': role,
                }
            )
            if created:
                user.set_password('csg2025')
                user.save()

            if role != 'super_admin':
                officer = Officer.objects.filter(user=user).first()
                if not officer:
                    officer = Officer.objects.filter(student_id=sid).first()
                if not officer:
                    officer = Officer(user=user, student_id=sid)
                else:
                    officer.user = user
                    officer.student_id = sid
                officer.position = positions.get(pos_title)
                officer.save()
                officers_list.append(user)

            self.stdout.write(f'  [+] User: {first} {last} ({role}) - Position: {pos_title}')

        admin_user = User.objects.filter(username='admin').first()

        # ── TASKS ────────────────────────────────
        today = timezone.now().date()
        tasks_data = [
            ('Prepare Annual Financial Report', 'Compile all financial transactions and prepare the annual report for submission to the administration.', 'high', 'completed', -30, 100, today - datetime.timedelta(days=30)),
            ('Organize Freshmen Orientation', 'Plan and execute the freshmen orientation program for incoming students.', 'urgent', 'completed', -20, 100, today - datetime.timedelta(days=5)),
            ('Update CSG Constitution', 'Review and propose amendments to the CSG constitution for ratification.', 'medium', 'to_advisers', 15, 60, None),
            ('Social Media Campaign Q3', 'Create and schedule social media content for the third quarter campaign.', 'medium', 'processing', 10, 45, None),
            ('Scholarship Monitoring Report', 'Collect and verify scholarship recipient data for the semester.', 'high', 'osas', -2, 90, None),
            ('Budget Proposal 2026', 'Prepare the annual budget proposal for the next academic year.', 'high', 'accounting', 20, 10, None),
            ('Inter-University Debate', 'Coordinate participation in the inter-university debate competition.', 'medium', 'not_started', 25, 0, None),
            ('Year-End Report', 'Consolidate all accomplishments for the year-end report.', 'urgent', 'overdue', -5, 30, None),
            ('Website Redesign Graphics', 'Oversee the redesign and branding assets for the CSG website.', 'medium', 'processing', 30, 55, None),
            ('Executive Assistant Briefing', 'Prepare briefing documents for upcoming student council summit.', 'high', 'oca', 14, 5, None),
            ('Audit Report Semester 1', 'Complete internal audit of all funds and expenses for Semester 1.', 'high', 'completed', -15, 100, today - datetime.timedelta(days=15)),
            ('Student Assembly Planning', 'Organize the quarterly student assembly agenda and logistics.', 'medium', 'ppss', 7, 70, None),
            ('Membership Drive Event', 'Plan and execute the membership drive for new student members.', 'low', 'completed', -10, 100, today - datetime.timedelta(days=10)),
            ('Grant Application Review', 'Review and process grant applications from student organizations.', 'high', 'supply', 21, 0, None),
            ('Community Service Activity', 'Coordinate the semestral community service activity.', 'medium', 'not_started', 28, 0, None),
            ('Campus Eco-Waste Management Drive', 'Organize campus-wide segregated recycling bins and information dissemination.', 'medium', 'not_started', 14, 0, None),
            ('Student Council Budget Audit Q1', 'Review and process expense vouchers and receipts for Q1 student council events.', 'high', 'accounting', 8, 25, None),
            ('OSAS Facility Request Endorsement', 'Submit formal facility reservation for the upcoming University Student Summit.', 'medium', 'osas', 5, 40, None),
            ('OCA Event Approval for Cultural Night', 'Prepare and submit event proposal paperwork to the Office of Cultural Affairs.', 'urgent', 'oca', 3, 60, None),
            ('PPSS Sound System Procurement', 'Coordinate with Physical Plant & Site Services for AV equipment setup.', 'high', 'ppss', 6, 50, None),
            ('Office Supplies Requisition for CSG Secretariat', 'Submit requisition forms for printer ink, paper, and organizational materials.', 'low', 'supply', 12, 10, None),
            ('Adviser Endorsement for Leadership Seminar', 'Obtain official signatures from faculty advisers for the leadership workshop.', 'medium', 'to_advisers', 4, 75, None),
            ('Student Grievance Hotline Setup', 'Establish an online feedback form and ticketing system for student complaints.', 'high', 'processing', 10, 30, None),
            ('Annual Campus Clean-up Drive Logistics', 'Coordinate volunteer registration and equipment distribution for campus cleanup.', 'medium', 'not_started', 20, 0, None),
            ('Mid-Year Constitutional Review Assembly', 'Conduct mid-year review of council resolutions and bylaws.', 'urgent', 'completed', -2, 100, today),
        ]

        created_tasks = []
        assignee_pool = officers_list[:10]  # top officers for assignments
        for i, (title, desc, priority, status, due_days, progress, completion_date) in enumerate(tasks_data):
            if not Task.objects.filter(title=title).exists():
                task = Task(
                    title=title,
                    description=desc,
                    priority=priority,
                    status=status,
                    due_date=today + datetime.timedelta(days=due_days),
                    progress=progress,
                    completion_date=completion_date,
                    created_by=admin_user,
                )
                task.save()

                # Assign 1-3 officers
                assigned = random.sample(assignee_pool, k=min(random.randint(1, 3), len(assignee_pool)))
                for officer_user in assigned:
                    TaskAssignment.objects.get_or_create(
                        task=task, officer=officer_user,
                        defaults={'assigned_by': admin_user}
                    )

                # Add a sample comment
                commenter = random.choice(assigned)
                TaskComment.objects.create(
                    task=task, author=commenter,
                    content=random.choice([
                        'Working on this task. Will update progress soon.',
                        'Task is proceeding as planned.',
                        'Encountered minor delays but still on track.',
                        'Completed initial phase. Moving to next steps.',
                        'Requesting additional support for this task.',
                    ])
                )

                created_tasks.append(task)
                self.stdout.write(f'  [+] Task: [{task.task_number}] {title}')

        # ── NOTIFICATIONS ─────────────────────────
        for user in officers_list[:5]:
            Notification.objects.get_or_create(
                recipient=user,
                title='Welcome to CSG Task System',
                defaults={
                    'message': 'You have been added to the CSG Task Management System. Check your assigned tasks.',
                    'notification_type': 'system',
                }
            )

        self.stdout.write(self.style.SUCCESS('\n[OK] Seed complete! Positions updated:'))
        for title in positions_titles:
            self.stdout.write(f'  - {title}')
    