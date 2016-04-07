from django.views.generic import FormView
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.views.defaults import page_not_found
from furl import furl

from website.settings import SUPPORT_EMAIL, DOMAIN
from website.security import random_string
from framework.auth import get_user

from website.project.model import User
from website.mailchimp_utils import subscribe_on_confirm

from admin.base.views import GuidFormView, GuidView
from admin.users.templatetags.user_extras import reverse_user

from .serializers import serialize_user
from .forms import EmailResetForm


def disable_user(request, guid):
    user = User.load(guid)
    user.disable_account()
    user.save()
    return redirect(reverse_user(guid))


def reactivate_user(request, guid):
    user = User.load(guid)
    user.date_disabled = None
    subscribe_on_confirm(user)
    user.save()
    return redirect(reverse_user(guid))


def remove_2_factor(request, guid):
    user = User.load(guid)
    try:
        user.delete_addon('twofactor')
    except AttributeError:
        page_not_found(request)
    return redirect(reverse_user(guid))


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
    template_name = 'users/reset.html'

    def __init__(self):
        self.guid = None
        super(ResetPasswordView, self).__init__()

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())  # TODO: 1.9xx

    def get_context_data(self, **kwargs):
        self.guid = self.kwargs.get('guid', None)
        try:
            user = User.load(self.guid)
        except AttributeError:
            raise
        self.initial.setdefault('emails', [(r, r) for r in user.emails])
        kwargs.setdefault('guid', self.guid)
        kwargs.setdefault('form', self.get_form())  # TODO: 1.9 xx
        return super(ResetPasswordView, self).get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        self.guid = self.kwargs.get('guid', None)
        return super(ResetPasswordView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        email = form.cleaned_data.get('emails')
        user = get_user(email)
        if user is None:
            raise TypeError
        reset_abs_url = furl(DOMAIN)
        user.verification_key = random_string(20)
        user.save()
        reset_abs_url.path.add(('resetpassword/{}'.format(user.verification_key)))

        send_mail(
            subject='Reset OSF Password',
            message='Follow this link to reset your password: {}'.format(
                reset_abs_url.url
            ),
            from_email=SUPPORT_EMAIL,
            recipient_list=[email]
        )
        return super(ResetPasswordView, self).form_valid(form)

    @property
    def success_url(self):
        return reverse_user(self.guid)
