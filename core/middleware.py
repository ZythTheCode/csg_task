import time
import logging

from django.conf import settings
from django.db import OperationalError, connection
from django.http import HttpResponse

logger = logging.getLogger('csg.performance')

QUERY_COUNT_THRESHOLD = getattr(settings, 'PERF_QUERY_COUNT_THRESHOLD', 15)
REQUEST_DURATION_THRESHOLD_MS = getattr(settings, 'PERF_REQUEST_DURATION_THRESHOLD_MS', 2000)


class PerformanceMonitoringMiddleware:
    """
    Middleware that tracks query count and request duration.
    In DEBUG mode: adds X-Query-Count and X-Query-Time-Ms headers.
    Always: logs warnings when thresholds are exceeded.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        initial_queries = len(connection.queries)

        response = self.get_response(request)

        duration_ms = int((time.time() - start_time) * 1000)
        query_count = len(connection.queries) - initial_queries
        query_time_ms = int(sum(
            float(q.get('time', 0)) for q in connection.queries[initial_queries:]
        ) * 1000)

        # Log warnings for threshold violations
        if query_count > QUERY_COUNT_THRESHOLD:
            logger.warning(
                f"High query count: {request.path} executed {query_count} queries"
            )
        if duration_ms > REQUEST_DURATION_THRESHOLD_MS:
            logger.warning(
                f"Slow request: {request.path} took {duration_ms}ms"
            )

        # Add debug headers only in DEBUG mode
        if settings.DEBUG:
            response['X-Query-Count'] = str(query_count)
            response['X-Query-Time-Ms'] = str(query_time_ms)

        return response


class DatabaseRetryMiddleware:
    """Retry database connection failures once before returning 503."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except OperationalError as e:
            if 'connect_timeout' in str(e) or 'connection' in str(e).lower():
                try:
                    connection.close()
                    return self.get_response(request)
                except OperationalError:
                    return HttpResponse(
                        'Database temporarily unavailable. Please try again.',
                        status=503,
                        content_type='text/plain'
                    )
            raise
