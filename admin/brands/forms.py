from django import forms

from osf.models import Brand
from django.forms.widgets import TextInput

class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = '__all__'
        widgets = {
            'primary_color': TextInput(attrs={'class': 'colorpicker'}),
            'secondary_color': TextInput(attrs={'class': 'colorpicker'}),
            'hero_logo_image': TextInput(attrs={'placeholder': 'Logo image should be max height of 100px'}),
            'topnav_logo_image': TextInput(attrs={'placeholder': 'Logo should be max height of 40px'}),
            'hero_background_image': TextInput(attrs={'placeholder': 'Background image should be max height of 300px'}),
        }
