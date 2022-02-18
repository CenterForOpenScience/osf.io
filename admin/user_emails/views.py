from __future__ import unicode_literals

import logging

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.defaults import page_not_found
from django.views.generic import FormView
from django.views.generic import ListView
from rest_framework import status as http_status

from admin.base.views import GuidView
from admin.user_emails.forms import UserEmailsSearchForm
from framework.exceptions import HTTPError
from osf.models.user import OSFUser
from website import mailchimp_utils
from website import mails
from website import settings

logger = logging.getLogger(__name__)


class UserEmailsFormView(PermissionRequiredMixin, FormView):
    template_name = 'user_emails/search.html'
    object_type = 'osfuser'
    permission_required = 'osf.view_osfuser'
    raise_exception = True
    form_class = UserEmailsSearchForm

    def __init__(self, *args, **kwargs):
        self.redirect_url = reverse('user-emails:search')
        super(UserEmailsFormView, self).__init__(*args, **kwargs)

    def form_valid(self, form):
        guid = form.cleaned_data['guid']
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']

        if guid or email:
            if email:
                try:
                    user = OSFUser.objects.filter(Q(username=email) | Q(emails__address=email)).distinct('id').get()
                    guid = user.guids.first()._id
                except OSFUser.DoesNotExist:
                    return page_not_found(self.request, AttributeError('User with email address {} not found.'.format(email)))
                except OSFUser.MultipleObjectsReturned:
                    return page_not_found(self.request, AttributeError('Multiple users with email address {} found, please notify DevOps.'.format(email)))
            self.redirect_url = reverse('user-emails:user', kwargs={'guid': guid})
        elif name:
            self.redirect_url = reverse('user-emails:search_list', kwargs={'name': name})

        return super(UserEmailsFormView, self).form_valid(form)

    @property
    def success_url(self):
        return self.redirect_url


class UserEmailsSearchList(PermissionRequiredMixin, ListView):
    template_name = 'user_emails/user_list.html'
    permission_required = 'osf.view_osfuser'
    raise_exception = True
    form_class = UserEmailsSearchForm
    paginate_by = 25

    def get_queryset(self):
        query = OSFUser.objects.filter(fullname__icontains=self.kwargs['name']).only(
            'guids', 'fullname', 'username', 'date_confirmed', 'date_disabled'
        )
        return query

    def get_context_data(self, **kwargs):
        users = self.get_queryset()
        page_size = self.get_paginate_by(users)
        paginator, page, query_set, is_paginated = self.paginate_queryset(users, page_size)
        kwargs['page'] = page
        kwargs['users'] = [{
            'name': user.fullname,
            'username': user.username,
            'id': user.guids.first()._id,
            'confirmed': user.date_confirmed,
            'disabled': user.date_disabled if user.is_disabled else None
        } for user in query_set]
        return super(UserEmailsSearchList, self).get_context_data(**kwargs)


class UserEmailsView(PermissionRequiredMixin, GuidView):
    template_name = 'user_emails/user_emails.html'
    context_object_name = 'user'
    permission_required = 'osf.view_osfuser'
    raise_exception = True

    def get_context_data(self, **kwargs):
        kwargs = super(UserEmailsView, self).get_context_data(**kwargs)
        return kwargs

    def get_object(self, queryset=None):
        user = OSFUser.load(self.kwargs.get('guid'))

        return {
            'username': user.username,
            'name': user.fullname,
            'id': user._id,
            'emails': user.emails.values_list('address', flat=True),
        }


class UserPrimaryEmail(PermissionRequiredMixin, View):
    permission_required = 'osf.view_osfuser'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        user = OSFUser.load(self.kwargs.get('guid'))
        primary_email = request.POST.get('primary_email')
        username = None

        # Refer to website.profile.views.update_user
        if primary_email:
            primary_email_address = primary_email.strip().lower()
            if primary_email_address not in [each.strip().lower() for each in user.emails.values_list('address', flat=True)]:
                raise HTTPError(http_status.HTTP_403_FORBIDDEN)
            username = primary_email_address

        # make sure the new username has already been confirmed
        if username and username != user.username and user.emails.filter(address=username).exists():

            mails.send_mail(
                user.username,
                mails.PRIMARY_EMAIL_CHANGED,
                user=user,
                new_address=username,
                can_change_preferences=False,
                osf_contact_email=settings.OSF_CONTACT_EMAIL
            )

            # Remove old primary email from subscribed mailing lists
            for list_name, subscription in user.mailchimp_mailing_lists.items():
                if subscription:
                    mailchimp_utils.unsubscribe_mailchimp_async(list_name, user._id, username=user.username)
            user.username = username

        user.save()

        return redirect(reverse('user-emails:user', kwargs={'guid': user._id}))
