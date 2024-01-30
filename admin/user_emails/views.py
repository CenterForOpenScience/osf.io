from __future__ import unicode_literals

import logging

from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.defaults import page_not_found, permission_denied
from django.views.generic import FormView
from django.views.generic import ListView

from admin.base.views import GuidView
from admin.rdm.utils import RdmPermissionMixin
from admin.user_emails.forms import UserEmailsSearchForm
from osf.models.user import OSFUser, Email
from website import mailchimp_utils
from website import mails
from website import settings
from admin.base.utils import render_bad_request_response

logger = logging.getLogger(__name__)


class RdmAdminRequiredMixin(UserPassesTestMixin, RdmPermissionMixin):
    """
    Includes methods of UserPassesTestMixin and RdmPermissionMixin
    Only permitted if superuser or administrator
    """

    raise_exception = True

    def test_func(self):
        """check user authentication"""
        # login check
        if not self.is_authenticated:
            return False

        # permitted if superuser or administrator
        if self.is_super_admin or self.is_admin:
            return True
        return False

class UserEmailsFormView(RdmAdminRequiredMixin, FormView):
    template_name = 'user_emails/search.html'
    object_type = 'osfuser'
    raise_exception = True
    form_class = UserEmailsSearchForm

    def __init__(self, *args, **kwargs):
        self.redirect_url = reverse('user-emails:search')
        super(UserEmailsFormView, self).__init__(*args, **kwargs)

    def form_valid(self, form):
        guid = form.cleaned_data['guid']
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']
        request_user = self.request.user

        if guid or email:
            if email:
                try:
                    users_query = OSFUser.objects.filter(is_active=True, is_registered=True)
                    users_query = users_query.filter(Q(username=email) | Q(emails__address=email))
                    if self.is_admin:
                        now_institutions_id = list(request_user.affiliated_institutions.all().values_list('pk', flat=True))
                        users_query = users_query.filter(affiliated_institutions__in=now_institutions_id)
                    user = users_query.distinct('id').get()
                    guid = user.guids.first()._id
                except OSFUser.DoesNotExist:
                    msg = 'User with email address {} not found.'.format(email)
                    return page_not_found(self.request, AttributeError(msg))
                except OSFUser.MultipleObjectsReturned:
                    msg = 'Multiple users with email address {} found, please notify DevOps.'.format(email)
                    return page_not_found(self.request, AttributeError(msg))
            self.redirect_url = reverse('user-emails:search_list_guid', kwargs={'guid': guid})
        elif name:
            self.redirect_url = reverse('user-emails:search_list', kwargs={'name': name})

        return super(UserEmailsFormView, self).form_valid(form)

    @property
    def success_url(self):
        return self.redirect_url


class UserEmailsSearchList(RdmAdminRequiredMixin, ListView):
    template_name = 'user_emails/user_list.html'
    raise_exception = True
    form_class = UserEmailsSearchForm
    paginate_by = 25

    def get(self, request, *args, **kwargs):
        keyword = self.kwargs.get('name')
        guid = self.kwargs.get('guid')
        if not keyword and not guid:
            return render_bad_request_response(request=request, error_msgs='missing name or guid parameter')
        return super(UserEmailsSearchList, self).get(request, *args, **kwargs)

    def get_queryset(self):
        keyword = self.kwargs.get('name')
        guid = self.kwargs.get('guid')
        request_user = self.request.user

        if guid:
            users_query = OSFUser.objects.filter(guids___id=guid)
        else:
            users_query = OSFUser.objects.filter(is_active=True, is_registered=True)
            users_query = users_query.filter(fullname__icontains=keyword)
        if self.is_admin:
            now_institutions_id = list(request_user.affiliated_institutions.all().values_list('pk', flat=True))
            users_query = users_query.filter(affiliated_institutions__in=now_institutions_id)
        users_query = users_query.order_by('fullname').only(
            'guids', 'eppn', 'username', 'fullname'
        )
        return users_query

    def get_context_data(self, **kwargs):
        users = self.get_queryset()
        page_size = self.get_paginate_by(users)
        paginator, page, query_set, is_paginated = self.paginate_queryset(users, page_size)
        kwargs['page'] = page
        kwargs['users'] = [{
            'id': user.guids.first()._id,
            'eppn': user.eppn,
            'username': user.username,
            'name': user.fullname,
            'affiliation': user.affiliated_institutions.first(),
        } for user in query_set]
        return super(UserEmailsSearchList, self).get_context_data(**kwargs)


class UserEmailsView(RdmAdminRequiredMixin, GuidView):
    template_name = 'user_emails/user_emails.html'
    # to avoid the context 'user', let use another object name
    context_object_name = 'osf_user'
    raise_exception = True

    def get_context_data(self, **kwargs):
        if self.request.session.get('from') == 'post':
            del self.request.session['from']
        elif 'message' in self.request.session:
            del self.request.session['message']
        kwargs = super(UserEmailsView, self).get_context_data(**kwargs)
        return kwargs

    def get_object(self, queryset=None):
        request_user = self.request.user
        user = OSFUser.load(self.kwargs.get('guid'))

        if self.is_admin:
            now_institutions_id = list(request_user.affiliated_institutions.all().values_list('pk', flat=True))
            all_institution_users_id = list(OSFUser.objects.filter(affiliated_institutions__in=now_institutions_id).distinct().values_list('pk', flat=True))

            if user.pk not in all_institution_users_id:
                return self.handle_no_permission()

        return {
            'id': user._id,
            'eppn': user.eppn,
            'username': user.username,
            'name': user.fullname,
            'affiliations': user.affiliated_institutions.all(),
            'emails': user.emails.values_list('address', flat=True),
        }


class UserPrimaryEmail(RdmAdminRequiredMixin, View):
    raise_exception = True

    def post(self, request, *args, **kwargs):
        request_user = self.request.user
        user = OSFUser.load(self.kwargs.get('guid'))
        primary_email = request.POST.get('primary_email')
        username = None

        if self.is_admin:
            now_institutions_id = list(request_user.affiliated_institutions.all().values_list('pk', flat=True))
            all_institution_users_id = list(OSFUser.objects.filter(affiliated_institutions__in=now_institutions_id).distinct().values_list('pk', flat=True))

            if user.pk not in all_institution_users_id:
                return permission_denied(self.request, Exception('You cannot access this specific page'))

        # Refer to website.profile.views.update_user
        if primary_email:
            primary_email_address = primary_email.strip().lower()
            user_emails = [each.strip().lower() for each in user.emails.values_list('address', flat=True)]
            all_emails = [each.strip().lower() for each in Email.objects.values_list('address', flat=True)]
            unavailable_emails = [each for each in all_emails if each not in user_emails]
            if primary_email_address in unavailable_emails:
                request.session['from'] = 'post'
                request.session['message'] = 'Email "{}" cannot be used'.format(primary_email_address)
                return redirect(reverse('user-emails:user', kwargs={'guid': user._id}))

            if primary_email_address not in user_emails:
                user.emails.create(address=primary_email_address.lower().strip())
            username = primary_email_address

        # make sure the new username has already been confirmed
        old_primary_email = ''
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

            old_primary_email = user.username
            user.username = username

        user.save()
        # remove old primary email to use for other purposes
        user.emails.filter(address=old_primary_email).delete()

        return redirect(reverse('user-emails:user', kwargs={'guid': user._id}))
