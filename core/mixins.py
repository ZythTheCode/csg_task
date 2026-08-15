"""
Mixins for Django class-based views to support AJAX fragment responses.

The FragmentResponseMixin enables partial page updates by detecting
fragment request headers and returning only the content block HTML
instead of the full page template.
"""

from django.http import HttpResponse
from django.template.response import TemplateResponse


# Fragment marker constants
FRAGMENT_START = '<!-- FRAGMENT_START -->'
FRAGMENT_END = '<!-- FRAGMENT_END -->'
FRAGMENT_SCRIPTS_START = '<!-- FRAGMENT_SCRIPTS_START -->'
FRAGMENT_SCRIPTS_END = '<!-- FRAGMENT_SCRIPTS_END -->'


class FragmentResponseMixin:
    """
    Mixin for Django CBVs that returns only the content block
    when the request includes both X-Requested-With: XMLHttpRequest
    and X-Fragment: true headers.

    Add this mixin to existing class-based views (before other mixins
    in the MRO) to enable AJAX partial page navigation without
    modifying the view's core logic.

    Usage:
        class MyView(FragmentResponseMixin, LoginRequiredMixin, TemplateView):
            template_name = 'my_template.html'
    """

    def _is_fragment_request(self):
        """
        Check whether the current request is an AJAX fragment request.

        Returns True if both headers are present:
        - X-Requested-With: XMLHttpRequest
        - X-Fragment: true
        """
        return (
            self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            and self.request.headers.get('X-Fragment') == 'true'
        )

    def render_to_response(self, context, **response_kwargs):
        """
        Override render_to_response to return fragment-only content
        for AJAX fragment requests, or the full page for standard requests.
        """
        if self._is_fragment_request():
            return self._render_fragment(context, **response_kwargs)
        return super().render_to_response(context, **response_kwargs)

    def _render_fragment(self, context, **response_kwargs):
        """
        Render the full template, then extract the content between
        fragment markers and return only that content + scripts as
        an HttpResponse with appropriate headers.

        Falls back to returning the full response if markers are not found
        (graceful degradation).
        """
        context['is_fragment'] = True
        response = super().render_to_response(context, **response_kwargs)

        # Force render if it's a TemplateResponse (lazy rendering)
        if isinstance(response, TemplateResponse):
            response.render()

        # Decode the rendered content
        content = response.content.decode('utf-8')

        # Extract HTML between FRAGMENT_START and FRAGMENT_END markers
        fragment_start_idx = content.find(FRAGMENT_START)
        fragment_end_idx = content.find(FRAGMENT_END)

        if fragment_start_idx == -1 or fragment_end_idx == -1:
            # Markers not found — graceful degradation: return full response
            page_title = context.get('page_title', '')
            response['X-Page-Title'] = page_title
            response['X-Fragment-Response'] = 'true'
            return response

        # Slice content between markers (after the start marker, before the end marker)
        fragment_content = content[
            fragment_start_idx + len(FRAGMENT_START):fragment_end_idx
        ].strip()

        # Extract scripts between FRAGMENT_SCRIPTS_START and FRAGMENT_SCRIPTS_END
        scripts_start_idx = content.find(FRAGMENT_SCRIPTS_START)
        scripts_end_idx = content.find(FRAGMENT_SCRIPTS_END)

        fragment_scripts = ''
        if scripts_start_idx != -1 and scripts_end_idx != -1:
            fragment_scripts = content[
                scripts_start_idx + len(FRAGMENT_SCRIPTS_START):scripts_end_idx
            ].strip()

        # Combine content + scripts as the response body
        body = fragment_content
        if fragment_scripts:
            body = body + '\n' + fragment_scripts

        # Build an HttpResponse with the extracted fragment
        fragment_response = HttpResponse(body, content_type='text/html; charset=utf-8')

        # Set response headers
        page_title = context.get('page_title', '')
        fragment_response['X-Page-Title'] = page_title
        fragment_response['X-Fragment-Response'] = 'true'

        return fragment_response
