"""
OverdueTaskMiddleware (Disabled)
─────────────────────────
Task overdue state is computed dynamically using task.is_overdue property (due_date < today and status != 'completed').
Task status values store the workflow stage (Not Started, Processing, etc.) and are never mutated to 'overdue'.
"""

class OverdueTaskMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def _sweep_if_needed(self, request):
        pass
