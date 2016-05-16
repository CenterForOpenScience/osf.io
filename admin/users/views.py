from __future__ import unicode_literals

from furl import furl
from django.views.generic import FormView, DeleteView
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.views.defaults import page_not_found

from website.settings import SUPPORT_EMAIL, DOMAIN
from website.security import random_string
from framework.auth import get_user

from website.project.model import User
from website.mailchimp_utils import subscribe_on_confirm

from admin.base.views import GuidFormView, GuidView
from admin.users.templatetags.user_extras import reverse_user
from admin.base.utils import OSFAdmin
from admin.common_auth.logs import (
    update_admin_log,
    USER_2_FACTOR,
    USER_EMAILED,
    USER_REMOVED,
    USER_RESTORED,
)

from admin.users.serializers import serialize_user
from admin.users.forms import EmailResetForm


class UserDeleteView(OSFAdmin, DeleteView):
    """ Allow authorised admin user to remove/restore user

    Interface with OSF database. No admin models.
    """
    template_name = 'users/remove_user.html'
    context_object_name = 'user'
    object = None

    def delete(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            flag = None
            message = None
            if user.date_disabled is None:
                user.disable_account()
                flag = USER_REMOVED
                message = 'User account {} disabled'.format(user.pk)
            else:
                user.date_disabled = None
                subscribe_on_confirm(user)
                flag = USER_RESTORED
                message = 'User account {} reenabled'.format(user.pk)
            user.save()
            if flag is not None:
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=user.pk,
                    object_repr='User',
                    message=message,
                    action_flag=flag
                )
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    '{} with id "{}" not found.'.format(
                        self.context_object_name.title(),
                        self.kwargs.get('guid')
                    )
                )
            )
        return redirect(reverse_user(self.kwargs.get('guid')))

    def get_context_data(self, **kwargs):
        context = {}
        context.setdefault('guid', kwargs.get('object').pk)
        return super(UserDeleteView, self).get_context_data(**context)

    def get_object(self, queryset=None):
        return User.load(self.kwargs.get('guid'))

class User2FactorDeleteView(UserDeleteView):
    """ Allow authorised admin user to remove 2 factor authentication.

    Interface with OSF database. No admin models.
    """
    template_name = 'users/remove_2_factor.html'

    def delete(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            user.delete_addon('twofactor')
            update_admin_log(
                user_id=self.request.user.id,
                object_id=user.pk,
                object_repr='User',
                message='Removed 2 factor auth for user {}'.format(user.pk),
                action_flag=USER_2_FACTOR
            )
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    '{} with id "{}" not found.'.format(
                        self.context_object_name.title(),
                        self.kwargs.get('guid')
                    )
                )
            )
        return redirect(reverse_user(self.kwargs.get('guid')))


class UserFormView(OSFAdmin, GuidFormView):
    template_name = 'users/search.html'
    object_type = 'user'

    @property
    def success_url(self):
        return reverse_user(self.guid)


class UserView(OSFAdmin, GuidView):
    template_name = 'users/user.html'
    context_object_name = 'user'

    def get_object(self, queryset=None):
        return serialize_user(User.load(self.kwargs.get('guid')))


class ResetPasswordView(OSFAdmin, FormView):
    form_class = EmailResetForm
    template_name = 'users/reset.html'

    def get(self, request, *args, **kwargs):
        try:
            return super(ResetPasswordView, self).get(request, *args, **kwargs)
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    'User with id "{}" not found.'.format(
                        self.kwargs.get('guid')
                    )
                )
            )

    def post(self, request, *args, **kwargs):
        try:
            return super(ResetPasswordView, self).post(request, *args, **kwargs)
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    'User with id "{}" not found.'.format(
                        self.kwargs.get('guid')
                    )
                )
            )

    def get_context_data(self, **kwargs):
        user = User.load(self.kwargs.get('guid'))
        try:
            self.initial.setdefault('emails', [(r, r) for r in user.emails])
        except AttributeError:
            raise
        kwargs.setdefault('guid', user.pk)
        return super(ResetPasswordView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        email = form.cleaned_data.get('emails')
        user = get_user(email)
        if user is None or user.pk != self.kwargs.get('guid'):
            raise AttributeError
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
        update_admin_log(
            user_id=self.request.user.id,
            object_id=user.pk,
            object_repr='User',
            message='Emailed user {} a reset link.'.format(user.pk),
            action_flag=USER_EMAILED
        )
        return super(ResetPasswordView, self).form_valid(form)

    @property
    def success_url(self):
        return reverse_user(self.kwargs.get('guid'))
