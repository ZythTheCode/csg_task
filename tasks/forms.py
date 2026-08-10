from django import forms
from .models import Task, TaskComment, TaskAttachment
from accounts.models import User


class TaskForm(forms.ModelForm):
    assigned_officers = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Assigned Officers'
    )

    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'status', 'due_date', 'assigned_officers', 'progress']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Task title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Task description'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'progress': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
        }

    def __init__(self, *args, user=None, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            org = user.get_organization(request) if hasattr(user, 'get_organization') else getattr(user, 'organization', None)
            if org:
                self.fields['assigned_officers'].queryset = User.objects.filter(is_active=True, organization=org).exclude(role__in=['super_admin', 'super_super_admin']).order_by('first_name', 'last_name')
            else:
                self.fields['assigned_officers'].queryset = User.objects.filter(is_active=True, organization__isnull=False).exclude(role__in=['super_admin', 'super_super_admin']).order_by('organization__name', 'first_name', 'last_name')
        if self.instance and self.instance.pk:
            self.fields['assigned_officers'].initial = self.instance.assigned_officers.all()


class TaskProgressForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['progress', 'status']
        widgets = {
            'progress': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add a comment or remark...'
            }),
        }


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = TaskAttachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }
