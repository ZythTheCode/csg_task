import time
import logging
from unittest.mock import patch, MagicMock, PropertyMock
from django.test import SimpleTestCase, RequestFactory, override_settings
from django.http import HttpResponse

from core.middleware import PerformanceMonitoringMiddleware


class PerformanceMonitoringMiddlewareTests(SimpleTestCase):
    """Tests for PerformanceMonitoringMiddleware."""

    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=HttpResponse("OK"))

    def _make_queries_side_effect(self, initial_count, final_queries):
        """
        Create a property mock for connection.queries that returns
        an empty list initially (before request) and final_queries after.
        """
        call_count = [0]

        class QueryList:
            """Simulates connection.queries growing during request."""
            def __init__(self, initial, final):
                self._initial = initial
                self._final = final
                self._called_len = 0

            def __len__(self):
                self._called_len += 1
                if self._called_len == 1:
                    return self._initial
                return self._initial + len(self._final)

            def __getitem__(self, key):
                full = [None] * self._initial + self._final
                return full[key]

        return QueryList(initial_count, final_queries)

    @override_settings(DEBUG=True)
    @patch('core.middleware.connection')
    def test_adds_headers_in_debug_mode(self, mock_connection):
        """In DEBUG mode, X-Query-Count and X-Query-Time-Ms headers are added."""
        queries = self._make_queries_side_effect(0, [
            {'time': '0.001', 'sql': 'SELECT 1'},
            {'time': '0.002', 'sql': 'SELECT 2'},
        ])
        type(mock_connection).queries = PropertyMock(return_value=queries)
        mock_connection.queries = queries

        middleware = PerformanceMonitoringMiddleware(self.get_response)
        request = self.factory.get('/test/')
        response = middleware(request)

        self.assertIn('X-Query-Count', response)
        self.assertIn('X-Query-Time-Ms', response)
        self.assertEqual(response['X-Query-Count'], '2')

    @override_settings(DEBUG=False)
    @patch('core.middleware.connection')
    def test_no_headers_in_production(self, mock_connection):
        """In production (DEBUG=False), no performance headers are added."""
        queries = self._make_queries_side_effect(0, [
            {'time': '0.001', 'sql': 'SELECT 1'},
        ])
        mock_connection.queries = queries

        middleware = PerformanceMonitoringMiddleware(self.get_response)
        request = self.factory.get('/test/')
        response = middleware(request)

        self.assertNotIn('X-Query-Count', response)
        self.assertNotIn('X-Query-Time-Ms', response)

    @override_settings(DEBUG=True)
    @patch('core.middleware.connection')
    def test_logs_warning_on_high_query_count(self, mock_connection):
        """Logs WARNING when query count exceeds threshold."""
        queries = self._make_queries_side_effect(0, [
            {'time': '0.001', 'sql': 'SELECT 1'},
            {'time': '0.001', 'sql': 'SELECT 2'},
            {'time': '0.001', 'sql': 'SELECT 3'},
        ])
        mock_connection.queries = queries

        with patch('core.middleware.QUERY_COUNT_THRESHOLD', 2):
            middleware = PerformanceMonitoringMiddleware(self.get_response)
            request = self.factory.get('/test-path/')

            with self.assertLogs('csg.performance', level='WARNING') as cm:
                middleware(request)

            self.assertTrue(
                any('High query count' in msg and '/test-path/' in msg and '3 queries' in msg for msg in cm.output)
            )

    @override_settings(DEBUG=True)
    @patch('core.middleware.connection')
    def test_logs_warning_on_slow_request(self, mock_connection):
        """Logs WARNING when request duration exceeds threshold."""
        queries = self._make_queries_side_effect(0, [])
        mock_connection.queries = queries

        def slow_response(request):
            time.sleep(0.05)  # 50ms
            return HttpResponse("OK")

        with patch('core.middleware.REQUEST_DURATION_THRESHOLD_MS', 10):
            middleware = PerformanceMonitoringMiddleware(slow_response)
            request = self.factory.get('/slow-path/')

            with self.assertLogs('csg.performance', level='WARNING') as cm:
                middleware(request)

            self.assertTrue(
                any('Slow request' in msg and '/slow-path/' in msg for msg in cm.output)
            )

    @override_settings(DEBUG=True)
    @patch('core.middleware.connection')
    def test_query_time_calculation(self, mock_connection):
        """X-Query-Time-Ms correctly sums individual query times."""
        queries = self._make_queries_side_effect(0, [
            {'time': '0.100', 'sql': 'SELECT 1'},
            {'time': '0.200', 'sql': 'SELECT 2'},
        ])
        mock_connection.queries = queries

        middleware = PerformanceMonitoringMiddleware(self.get_response)
        request = self.factory.get('/test/')
        response = middleware(request)

        # 0.100 + 0.200 = 0.300 seconds = 300ms
        self.assertEqual(response['X-Query-Time-Ms'], '300')

    @override_settings(DEBUG=True)
    @patch('core.middleware.connection')
    def test_query_count_is_accurate(self, mock_connection):
        """X-Query-Count reflects the number of queries during request."""
        queries = self._make_queries_side_effect(0, [
            {'time': '0.001', 'sql': 'SELECT 1'},
            {'time': '0.002', 'sql': 'SELECT 2'},
            {'time': '0.001', 'sql': 'SELECT 3'},
        ])
        mock_connection.queries = queries

        middleware = PerformanceMonitoringMiddleware(self.get_response)
        request = self.factory.get('/test/')
        response = middleware(request)

        self.assertEqual(response['X-Query-Count'], '3')

    @override_settings(DEBUG=True)
    @patch('core.middleware.connection')
    def test_no_warning_below_threshold(self, mock_connection):
        """No warning logged when query count and duration are within thresholds."""
        queries = self._make_queries_side_effect(0, [
            {'time': '0.001', 'sql': 'SELECT 1'},
        ])
        mock_connection.queries = queries

        with patch('core.middleware.QUERY_COUNT_THRESHOLD', 15):
            with patch('core.middleware.REQUEST_DURATION_THRESHOLD_MS', 2000):
                middleware = PerformanceMonitoringMiddleware(self.get_response)
                request = self.factory.get('/test/')

                # Should not produce any warning logs
                logger = logging.getLogger('csg.performance')
                with patch.object(logger, 'warning') as mock_warn:
                    middleware(request)
                    mock_warn.assert_not_called()


from django.db import OperationalError
from core.middleware import DatabaseRetryMiddleware


class DatabaseRetryMiddlewareTests(SimpleTestCase):
    """Tests for DatabaseRetryMiddleware."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_normal_request_passes_through(self):
        """Normal requests without errors pass through unchanged."""
        get_response = MagicMock(return_value=HttpResponse("OK", status=200))
        middleware = DatabaseRetryMiddleware(get_response)
        request = self.factory.get('/test/')

        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")
        get_response.assert_called_once_with(request)

    @patch('core.middleware.connection')
    def test_retries_on_connection_failure(self, mock_connection):
        """Retries once after closing the connection on OperationalError."""
        success_response = HttpResponse("OK", status=200)
        get_response = MagicMock(
            side_effect=[OperationalError("connection refused"), success_response]
        )
        middleware = DatabaseRetryMiddleware(get_response)
        request = self.factory.get('/test/')

        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        mock_connection.close.assert_called_once()
        self.assertEqual(get_response.call_count, 2)

    @patch('core.middleware.connection')
    def test_retries_on_connect_timeout(self, mock_connection):
        """Retries on connect_timeout errors."""
        success_response = HttpResponse("OK", status=200)
        get_response = MagicMock(
            side_effect=[OperationalError("connect_timeout expired"), success_response]
        )
        middleware = DatabaseRetryMiddleware(get_response)
        request = self.factory.get('/test/')

        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        mock_connection.close.assert_called_once()

    @patch('core.middleware.connection')
    def test_returns_503_when_retry_also_fails(self, mock_connection):
        """Returns HTTP 503 with friendly message when retry also fails."""
        get_response = MagicMock(
            side_effect=OperationalError("connection refused")
        )
        middleware = DatabaseRetryMiddleware(get_response)
        request = self.factory.get('/test/')

        response = middleware(request)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertIn(b'Database temporarily unavailable', response.content)

    def test_reraises_non_connection_operational_errors(self):
        """Non-connection OperationalErrors are re-raised, not retried."""
        get_response = MagicMock(
            side_effect=OperationalError("relation does not exist")
        )
        middleware = DatabaseRetryMiddleware(get_response)
        request = self.factory.get('/test/')

        with self.assertRaises(OperationalError) as ctx:
            middleware(request)

        self.assertIn("relation does not exist", str(ctx.exception))
