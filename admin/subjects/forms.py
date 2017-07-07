from django import forms

from osf.models.subject import Subject


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['text', 'highlighted']
