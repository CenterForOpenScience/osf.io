from django import forms
from osf.models import NotificationType


class NotificationTypeForm(forms.ModelForm):
    class Meta:
        model = NotificationType
        fields = '__all__'
