from django.views.generic import FormView
from django.core.mail import send_mail

from framework.auth.views import forgot_password_generate_link
from website.project.model import User
from website.settings import SUPPORT_EMAIL

from admin.base.views import GuidFormView, GuidView
from admin.users.templatetags.user_extras import reverse_user
from .serializers import serialize_user
from .forms import EmailResetForm


class UserFormView(GuidFormView):
    template_name = 'users/search.html'
    object_type = 'user'

    @property
    def success_url(self):
        return reverse_user(self.guid)


class UserView(GuidView):
    template_name = 'users/user.html'
    context_object_name = 'user'

    def get_object(self, queryset=None):
        self.guid = self.kwargs.get('guid', None)
        return serialize_user(User.load(self.guid))


class ResetPasswordView(FormView):
    form_class = EmailResetForm

    def __init__(self):
        self.guid = None
        super(ResetPasswordView, self).__init__()

    def form_valid(self, form):
        email = form.cleaned_data_get('email')
        send_mail(
            subject='OSF Reset Password',
            message='Follow this link to reset your password: {}'.format(
                forgot_password_generate_link(email)
            ),
            from_email=SUPPORT_EMAIL,
            recipient_list=[email]
        )
