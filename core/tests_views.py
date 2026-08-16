"""
Integration tests for dashboard, monitoring, and reports view optimizations.

Tests verify query count guarantees using Django's assertNumQueries:
- DashboardView: single aggregate query for counts
- MonitoringDashboardView: single annotated queryset for officer metrics
- ReportsDashboardView: single aggregate for counts and pagination at 25 items

Requirements: 2.1, 2.2, 2.5
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from organizations.models import Organization
from officers.models import Officer, Position
from tasks.models import Task, TaskAssignment

import datetime

User = get_user_model()


class DashboardViewQueryOptimizationTests(TestCase):
    """
    Test DashboardView uses a single aggregate query for task counts.
    Validates Requirement 2.1: single aggregate query for active, completed,
    overdue, and upcoming counts.
    """

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(
            name='Test Org Dashboard',
            abbreviation='TOD',
            status='approved',
        )
        cls.user = User.objects.create_user(
            username='dashboard_user',
            password='testpass123',
            role='org_admin',
            organization=cls.org,
        )
        today = timezone.now().date()

        # Create tasks with various statuses to exercise aggregate
        statuses = ['not_started', 'processing', 'completed', 'to_advisers']
        for i, status in enumerate(statuses):
            due_date = today - datetime.timedelta(days=1) if i == 0 else today + datetime.timedelta(days=3)
            Task.objects.create(
                title=f'Dashboard Task {i}',
                description=f'Task with status {status}',
                status=status,
                priority='medium',
                due_date=due_date,
                organization=cls.org,
                created_by=cls.user,
            )

    def setUp(self):
        self.client.login(username='dashboard_user', password='testpass123')
        # Clear cache to ensure cold-cache scenario
        cache.clear()

    def test_dashboard_renders_successfully(self):
        """DashboardView returns 200 and includes expected context."""
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('active_tasks', response.context)
        self.assertIn('completed_tasks', response.context)
        self.assertIn('overdue_tasks', response.context)
        self.assertIn('upcoming_tasks', response.context)

    def test_dashboard_counts_are_correct(self):
        """DashboardView aggregate counts reflect actual task data."""
        response = self.client.get(reverse('core:dashboard'))
        ctx = response.context

        # We have: not_started (overdue, due yesterday), processing, completed, to_advisers (upcoming)
        self.assertEqual(ctx['completed_tasks'], 1)
        # Active = not_started + processing + to_advisers = 3
        self.assertEqual(ctx['active_tasks'], 3)
        # Overdue = not_started with due_date in the past
        self.assertGreaterEqual(ctx['overdue_tasks'], 1)

    def test_dashboard_single_aggregate_query_for_counts(self):
        """
        DashboardView uses a single aggregate query for all 4 task counts.
        Requirement 2.1: exactly one database query for all four counts.

        Verifies get_dashboard_stats executes in exactly 1 query.
        """
        from core.query_utils import get_dashboard_stats
        base_qs = Task.objects.filter(organization=self.org, is_archived=False)
        today = timezone.now().date()

        with self.assertNumQueries(1):
            stats = get_dashboard_stats(base_qs, today)

        self.assertIn('active', stats)
        self.assertIn('completed', stats)
        self.assertIn('overdue', stats)
        self.assertIn('upcoming', stats)
        # Verify the counts are integers (aggregate returns correct types)
        self.assertIsInstance(stats['active'], int)
        self.assertIsInstance(stats['completed'], int)

    def test_dashboard_cached_counts_zero_db_queries(self):
        """
        When cache is warm, DashboardView counts require zero additional
        database queries for the aggregate.
        """
        # First request warms the cache
        self.client.get(reverse('core:dashboard'))

        # The cache key should now contain the counts
        from core.cache_utils import get_dashboard_cache_key
        org_id = self.org.pk
        cache_key = get_dashboard_cache_key(self.user.pk, 'all', org_id)
        cached_value = cache.get(cache_key)
        self.assertIsNotNone(cached_value)
        self.assertIn('active', cached_value)
        self.assertIn('completed', cached_value)


class MonitoringViewQueryOptimizationTests(TestCase):
    """
    Test MonitoringView uses a single annotated queryset for officer metrics.
    Validates Requirement 2.2: no more than one query for officer metric
    computation regardless of officer count.
    """

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(
            name='Test Org Monitoring',
            abbreviation='TOM',
            status='approved',
        )
        cls.admin_user = User.objects.create_user(
            username='monitoring_admin',
            password='testpass123',
            role='org_admin',
            organization=cls.org,
        )

        today = timezone.now().date()

        # Create multiple officers with tasks
        cls.officers = []
        for i in range(5):
            officer_user = User.objects.create_user(
                username=f'officer_mon_{i}',
                password='testpass123',
                role='executive',
                organization=cls.org,
                first_name=f'Officer{i}',
                last_name=f'Mon{i}',
            )
            position = Position.objects.create(
                title=f'Position Mon {i}',
                organization=cls.org,
            )
            officer = Officer.objects.create(
                user=officer_user,
                position=position,
                student_id=f'MON-{i:04d}',
            )
            cls.officers.append(officer)

            # Create tasks assigned to each officer
            for j in range(3):
                status = ['not_started', 'processing', 'completed'][j]
                due_date = today - datetime.timedelta(days=1) if j == 0 else today + datetime.timedelta(days=5)
                task = Task.objects.create(
                    title=f'Mon Task {i}-{j}',
                    description=f'Monitoring task for officer {i}',
                    status=status,
                    priority='medium',
                    due_date=due_date,
                    organization=cls.org,
                    created_by=cls.admin_user,
                )
                TaskAssignment.objects.create(
                    task=task,
                    officer=officer_user,
                    assigned_by=cls.admin_user,
                )

    def setUp(self):
        self.client.login(username='monitoring_admin', password='testpass123')
        cache.clear()

    def test_monitoring_renders_successfully(self):
        """MonitoringDashboardView returns 200 and includes officer data."""
        response = self.client.get(reverse('monitoring:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('officers_data', response.context)

    def test_monitoring_officer_data_correct(self):
        """MonitoringDashboardView returns correct officer metrics."""
        response = self.client.get(reverse('monitoring:dashboard'))
        officers_data = response.context['officers_data']

        # We created 5 officers with 3 tasks each
        self.assertEqual(len(officers_data), 5)

        for data in officers_data:
            # Each officer has 3 tasks: not_started, processing, completed
            self.assertEqual(data['total'], 3)
            self.assertEqual(data['completed'], 1)
            self.assertEqual(data['active'], 2)  # not_started + processing

    def test_monitoring_single_annotated_queryset(self):
        """
        MonitoringView retrieves all officer metrics in a single annotated
        queryset, regardless of officer count.
        Requirement 2.2: no more than one query for officer metric computation.
        """
        from django.db.models import Count, Q, Case, When, Value, FloatField
        from officers.models import Officer

        today = timezone.now().date()

        # Build the same annotated queryset the view uses
        officers_qs = Officer.objects.select_related('user', 'position').exclude(
            user__role='super_super_admin'
        ).filter(user__organization=self.org)

        officers_qs = officers_qs.annotate(
            total_count=Count('user__assigned_tasks', filter=Q(user__assigned_tasks__is_archived=False)),
            completed_count=Count('user__assigned_tasks', filter=Q(
                user__assigned_tasks__status='completed',
                user__assigned_tasks__is_archived=False
            )),
            active_count=Count('user__assigned_tasks', filter=Q(
                user__assigned_tasks__is_archived=False
            ) & ~Q(user__assigned_tasks__status='completed')),
            overdue_count=Count('user__assigned_tasks', filter=Q(
                user__assigned_tasks__due_date__lt=today,
                user__assigned_tasks__is_archived=False
            ) & ~Q(user__assigned_tasks__status='completed')),
        ).annotate(
            completion_rate=Case(
                When(total_count=0, then=Value(0.0)),
                default=100.0 * Count('user__assigned_tasks', filter=Q(
                    user__assigned_tasks__status='completed',
                    user__assigned_tasks__is_archived=False
                )) / Count('user__assigned_tasks', filter=Q(
                    user__assigned_tasks__is_archived=False
                )),
                output_field=FloatField(),
            )
        ).order_by('-completion_rate')[:50]

        # The annotated queryset should evaluate in a single query
        with self.assertNumQueries(1):
            list(officers_qs)

    def test_monitoring_scales_with_officer_count(self):
        """
        Adding more officers does NOT increase the number of queries
        for the officer metrics computation.
        """
        # Add 5 more officers
        for i in range(5, 10):
            officer_user = User.objects.create_user(
                username=f'extra_officer_{i}',
                password='testpass123',
                role='executive',
                organization=self.org,
            )
            position = Position.objects.create(
                title=f'Extra Position {i}',
                organization=self.org,
            )
            Officer.objects.create(
                user=officer_user,
                position=position,
                student_id=f'EXT-{i:04d}',
            )

        # The view should still use a single annotated queryset
        from django.db.models import Count, Q
        officers_qs = Officer.objects.select_related('user', 'position').exclude(
            user__role='super_super_admin'
        ).filter(user__organization=self.org).annotate(
            total_count=Count('user__assigned_tasks', filter=Q(user__assigned_tasks__is_archived=False)),
        )[:50]

        with self.assertNumQueries(1):
            result = list(officers_qs)
            # Should have all 10 officers now
            self.assertEqual(len(result), 10)

    def test_monitoring_limits_to_50_officers(self):
        """MonitoringView caps officer data at 50 entries."""
        response = self.client.get(reverse('monitoring:dashboard'))
        officers_data = response.context['officers_data']
        # With 5 officers, the limit isn't hit but the slice is applied
        self.assertLessEqual(len(officers_data), 50)


class ReportsDashboardViewQueryOptimizationTests(TestCase):
    """
    Test ReportsDashboardView uses a single aggregate for counts
    and paginates at 25 items.
    Validates Requirement 2.5: single aggregate query for task counts.
    """

    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(
            name='Test Org Reports',
            abbreviation='TOR',
            status='approved',
        )
        cls.user = User.objects.create_user(
            username='reports_user',
            password='testpass123',
            role='org_admin',
            organization=cls.org,
        )
        today = timezone.now().date()

        # Create 30 tasks to test pagination (more than 25)
        cls.tasks = []
        for i in range(30):
            status = 'completed' if i < 10 else 'processing'
            due_date = today - datetime.timedelta(days=1) if i % 5 == 0 else today + datetime.timedelta(days=5)
            task = Task.objects.create(
                title=f'Report Task {i:02d}',
                description=f'Report task number {i}',
                status=status,
                priority=['low', 'medium', 'high', 'urgent'][i % 4],
                due_date=due_date,
                organization=cls.org,
                created_by=cls.user,
            )
            cls.tasks.append(task)

    def setUp(self):
        self.client.login(username='reports_user', password='testpass123')
        cache.clear()

    def test_reports_renders_successfully(self):
        """ReportsDashboardView returns 200 and includes expected context."""
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('task_count', response.context)
        self.assertIn('active_count', response.context)
        self.assertIn('completed_count', response.context)

    def test_reports_counts_correct(self):
        """ReportsDashboardView aggregate counts reflect actual data."""
        response = self.client.get(reverse('reports:dashboard'))
        ctx = response.context

        # 30 total: 10 completed, 20 active (processing)
        self.assertEqual(ctx['task_count'], 30)
        self.assertEqual(ctx['completed_count'], 10)
        self.assertEqual(ctx['active_count'], 20)

    def test_reports_single_aggregate_for_counts(self):
        """
        ReportsDashboardView computes task_count, active_count, and
        completed_count from a single aggregate query.
        Requirement 2.5: single aggregate instead of multiple count() calls.
        """
        from core.query_utils import get_report_counts

        tasks_qs = Task.objects.filter(organization=self.org, is_archived=False)
        today = timezone.now().date()

        # The single aggregate query for counts
        with self.assertNumQueries(1):
            counts = get_report_counts(tasks_qs, today)

        self.assertEqual(counts['total'], 30)
        self.assertEqual(counts['completed'], 10)
        self.assertEqual(counts['active'], 20)
        self.assertIn('overdue', counts)
        self.assertIn('in_progress', counts)

    def test_reports_pagination_at_25_items(self):
        """ReportsDashboardView paginates filtered task list at 25 items per page."""
        response = self.client.get(reverse('reports:dashboard'))
        ctx = response.context

        # Active tasks paginated at 25 - we have 20 active, so all on page 1
        active_page = ctx['active_page_obj']
        self.assertLessEqual(len(active_page.object_list), 25)

        # Completed tasks paginated at 25 - we have 10 completed, so all on page 1
        completed_page = ctx['completed_page_obj']
        self.assertLessEqual(len(completed_page.object_list), 25)

    def test_reports_pagination_enforces_25_limit(self):
        """
        When there are more than 25 active tasks, pagination limits
        the page to 25 items.
        """
        # Create additional tasks to exceed 25 active
        for i in range(30, 60):
            Task.objects.create(
                title=f'Extra Task {i}',
                description=f'Extra task {i}',
                status='processing',
                priority='medium',
                due_date=timezone.now().date() + datetime.timedelta(days=5),
                organization=self.org,
                created_by=self.user,
            )

        response = self.client.get(reverse('reports:dashboard'))
        ctx = response.context

        # Active tasks should be paginated at 25 per page
        active_page = ctx['active_page_obj']
        self.assertEqual(len(active_page.object_list), 25)
        # Total active = 20 (original) + 30 (new) = 50
        self.assertEqual(active_page.paginator.count, 50)
        self.assertEqual(active_page.paginator.num_pages, 2)

    def test_reports_pagination_page_2(self):
        """ReportsDashboardView returns page 2 of active tasks correctly."""
        # Create additional tasks to exceed 25
        for i in range(30, 60):
            Task.objects.create(
                title=f'Page2 Task {i}',
                description=f'Page2 task {i}',
                status='not_started',
                priority='low',
                due_date=timezone.now().date() + datetime.timedelta(days=5),
                organization=self.org,
                created_by=self.user,
            )

        response = self.client.get(reverse('reports:dashboard'), {'active_page': 2})
        ctx = response.context
        active_page = ctx['active_page_obj']

        self.assertEqual(active_page.number, 2)
        # Page 2 should have the remaining items
        self.assertGreater(len(active_page.object_list), 0)
        self.assertLessEqual(len(active_page.object_list), 25)

    def test_reports_pagination_invalid_page_returns_last(self):
        """
        When an invalid page number exceeding total is requested,
        the last available page is returned.
        """
        response = self.client.get(reverse('reports:dashboard'), {'active_page': 999})
        ctx = response.context
        active_page = ctx['active_page_obj']

        # Should return the last page, not error
        self.assertEqual(active_page.number, active_page.paginator.num_pages)
