from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger('django')


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        custom_response_data = {
            'success': False,
            'error': {
                'code': response.status_code,
                'type': exc.__class__.__name__,
                'details': response.data
            }
        }
        response.data = custom_response_data
    else:
        logger.error(f"Unhandled REST Framework Exception: {exc}", exc_info=True)
        response = Response({
            'success': False,
            'error': {
                'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'type': 'InternalServerError',
                'details': 'An unexpected server error occurred.'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response
