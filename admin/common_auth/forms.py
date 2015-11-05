from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.forms import ModelForm
from models import AdminUser

class RegistrationForm(ModelForm):
	username = forms.CharField(label=(u'User Name'))
	email = forms.EmailField(label=(u'Email Address'))
	password = forms.CharField(label=(u'Password'), widget=forms.PasswordInput(render_value=False))

	class Meta:
		model = AdminUser
		exclude = ('user',)

	def clean_username(self):
		username = self.cleaned_data['username']
		try:
			User.objects.get(username=username)
		except User.DoesNotExist:
			return username
		raise forms.ValidationError("Username taken, please select another.")

	def clean_password(self):
		password = self.cleaned_data['password']
		if len(password) < 5:
			raise forms.ValidationError("Password must be at least 5 characters in length.")
		return password

class LoginForm(forms.Form):
	username = forms.CharField(label=(u'User Name'))
	password = forms.CharField(label=(u'Password'), widget=forms.PasswordInput(render_value=False))

	def clean(self):
		username = self.cleaned_data.get('username')
		password = self.cleaned_data.get('password')
		if not username or not password:
			raise forms.ValidationError("Please enter the missing information.")
			return self.cleaned_data
		user = authenticate(username=username, password=password)
		if not user:
			raise forms.ValidationError("Invalid username/password combination. Please try again.")
		return self.cleaned_data
