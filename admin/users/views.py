from __future__ import unicode_literals

import csv
import pytz
from furl import furl
from datetime import datetime, timedelta
from django.db.models import Q
from django.views.defaults import page_not_found
from django.views.generic import FormView, DeleteView, ListView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.http import Http404, HttpResponse
from django.shortcuts import redirect

from osf.models.base import Guid
from osf.models.user import OSFUser
from osf.models.node import Node, NodeLog
from osf.models.spam import SpamStatus
from framework.auth import get_user
from framework.auth.utils import impute_names
from framework.auth.core import generate_verification_key

from website.mailchimp_utils import subscribe_on_confirm
from website import search

from admin.base.views import GuidView
from osf.models.admin_log_entry import (
    update_admin_log,
    USER_2_FACTOR,
    USER_EMAILED,
    USER_REMOVED,
    USER_RESTORED,
    CONFIRM_SPAM,
    REINDEX_ELASTIC,
)

from admin.users.serializers import serialize_user
from admin.users.forms import EmailResetForm, WorkshopForm, UserSearchForm, MergeUserForm
from admin.users.templatetags.user_extras import reverse_user
from website.settings import DOMAIN, OSF_SUPPORT_EMAIL


class UserDeleteView(PermissionRequiredMixin, DeleteView):
    """ Allow authorised admin user to remove/restore user

    Interface with OSF database. No admin models.
    """
    template_name = 'users/remove_user.html'
    context_object_name = 'user'
    object = None
    permission_required = 'osf.change_osfuser'
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            if user.date_disabled is None or kwargs.get('is_spam'):
                user.disable_account()
                user.is_registered = False
                if 'spam_flagged' in user.system_tags:
                    user.tags.through.objects.filter(tag__name='spam_flagged').delete()
                if 'ham_confirmed' in user.system_tags:
                    user.tags.through.objects.filter(tag__name='ham_confirmed').delete()

                if kwargs.get('is_spam') and 'spam_confirmed' not in user.system_tags:
                    user.add_system_tag('spam_confirmed')
                flag = USER_REMOVED
                message = 'User account {} disabled'.format(user.pk)
            else:
                user.requested_deactivation = False
                user.date_disabled = None
                subscribe_on_confirm(user)
                user.is_registered = True
                user.tags.through.objects.filter(tag__name__in=['spam_flagged', 'spam_confirmed'], tag__system=True).delete()
                if 'ham_confirmed' not in user.system_tags:
                    user.add_system_tag('ham_confirmed')
                flag = USER_RESTORED
                message = 'User account {} reenabled'.format(user.pk)
            user.save()
        except AttributeError:
            raise Http404(
                '{} with id "{}" not found.'.format(
                    self.context_object_name.title(),
                    self.kwargs.get('guid')
                ))
        update_admin_log(
            user_id=self.request.user.id,
            object_id=user.pk,
            object_repr='User',
            message=message,
            action_flag=flag
        )
        return redirect(reverse_user(self.kwargs.get('guid')))

    def get_context_data(self, **kwargs):
        context = {}
        context.setdefault('guid', kwargs.get('object')._id)
        return super(UserDeleteView, self).get_context_data(**context)

    def get_object(self, queryset=None):
        return OSFUser.load(self.kwargs.get('guid'))


class SpamUserDeleteView(UserDeleteView):
    """
    Allow authorized admin user to delete a spam user and mark all their nodes as private

    """

    template_name = 'users/remove_spam_user.html'

    def delete(self, request, *args, **kwargs):
        try:
            user = self.get_object()
        except AttributeError:
            raise Http404(
                '{} with id "{}" not found.'.format(
                    self.context_object_name.title(),
                    self.kwargs.get('guid')
                ))
        if user:
            for node in user.contributor_to:
                if not node.is_registration and not node.is_spam:
                    node.confirm_spam(save=True)
                    update_admin_log(
                        user_id=request.user.id,
                        object_id=node._id,
                        object_repr='Node',
                        message='Confirmed SPAM: {} when user {} marked as spam'.format(node._id, user._id),
                        action_flag=CONFIRM_SPAM
                    )

        kwargs.update({'is_spam': True})
        return super(SpamUserDeleteView, self).delete(request, *args, **kwargs)


class HamUserRestoreView(UserDeleteView):
    """
    Allow authorized admin user to undelete a ham user
    """

    template_name = 'users/restore_ham_user.html'

    def delete(self, request, *args, **kwargs):
        try:
            user = self.get_object()
        except AttributeError:
            raise Http404(
                '{} with id "{}" not found.'.format(
                    self.context_object_name.title(),
                    self.kwargs.get('guid')
                ))
        if user:
            for node in user.contributor_to:
                if node.is_spam:
                    node.confirm_ham(save=True)
                    update_admin_log(
                        user_id=request.user.id,
                        object_id=node._id,
                        object_repr='Node',
                        message='Confirmed HAM: {} when user {} marked as ham'.format(node._id, user._id),
                        action_flag=CONFIRM_SPAM
                    )

        kwargs.update({'is_spam': False})
        return super(HamUserRestoreView, self).delete(request, *args, **kwargs)


class UserSpamList(PermissionRequiredMixin, ListView):
    SPAM_TAG = 'spam_flagged'

    paginate_by = 25
    paginate_orphans = 1
    ordering = ('date_disabled')
    context_object_name = '-osfuser'
    permission_required = ('osf.view_spam', 'osf.view_osfuser')
    raise_exception = True

    def get_queryset(self):
        return OSFUser.objects.filter(tags__name=self.SPAM_TAG).order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'users': list(map(serialize_user, query_set)),
            'page': page,
        }


class UserFlaggedSpamList(UserSpamList, DeleteView):
    SPAM_TAG = 'spam_flagged'
    template_name = 'users/flagged_spam_list.html'

    def delete(self, request, *args, **kwargs):
        if not request.user.get_perms('osf.mark_spam'):
            raise PermissionDenied("You don't have permission to update this user's spam status.")
        user_ids = [
            uid for uid in request.POST.keys()
            if uid != 'csrfmiddlewaretoken'
        ]
        for uid in user_ids:
            user = OSFUser.load(uid)
            if 'spam_flagged' in user.system_tags:
                user.system_tags.remove('spam_flagged')
            user.add_system_tag('spam_confirmed')
            user.save()
            update_admin_log(
                user_id=self.request.user.id,
                object_id=uid,
                object_repr='User',
                message='Confirmed SPAM: {}'.format(uid),
                action_flag=CONFIRM_SPAM
            )
        return redirect('users:flagged-spam')


class UserKnownSpamList(UserSpamList):
    SPAM_TAG = 'spam_confirmed'
    template_name = 'users/known_spam_list.html'

class UserKnownHamList(UserSpamList):
    SPAM_TAG = 'ham_confirmed'
    template_name = 'users/known_spam_list.html'

class User2FactorDeleteView(UserDeleteView):
    """ Allow authorised admin user to remove 2 factor authentication.

    Interface with OSF database. No admin models.
    """
    template_name = 'users/remove_2_factor.html'

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        try:
            user.delete_addon('twofactor')
        except AttributeError:
            raise Http404(
                '{} with id "{}" not found.'.format(
                    self.context_object_name.title(),
                    self.kwargs.get('guid')
                ))
        update_admin_log(
            user_id=self.request.user.id,
            object_id=user.pk,
            object_repr='User',
            message='Removed 2 factor auth for user {}'.format(user.pk),
            action_flag=USER_2_FACTOR
        )
        return redirect(reverse_user(self.kwargs.get('guid')))


class UserFormView(PermissionRequiredMixin, FormView):
    template_name = 'users/search.html'
    object_type = 'osfuser'
    permission_required = 'osf.view_osfuser'
    raise_exception = True
    form_class = UserSearchForm

    def __init__(self, *args, **kwargs):
        self.redirect_url = None
        super(UserFormView, self).__init__(*args, **kwargs)

    def form_valid(self, form):
        guid = form.cleaned_data['guid']
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']

        if guid or email:
            if email:
                try:
                    user = OSFUser.objects.filter(Q(username=email) | Q(emails__address=email)).get()
                    guid = user.guids.first()._id
                except OSFUser.DoesNotExist:
                    return page_not_found(self.request, AttributeError('User with email address {} not found.'.format(email)))
            self.redirect_url = reverse('users:user', kwargs={'guid': guid})
        elif name:
            self.redirect_url = reverse('users:search_list', kwargs={'name': name})

        return super(UserFormView, self).form_valid(form)

    @property
    def success_url(self):
        return self.redirect_url

class UserMergeAccounts(PermissionRequiredMixin, FormView):
    template_name = 'users/merge_accounts_modal.html'
    permission_required = 'osf.view_osfuser'
    object_type = 'osfuser'
    raise_exception = True
    form_class = MergeUserForm

    def get_context_data(self, **kwargs):
        return {'guid': self.get_object()._id}

    def get_object(self, queryset=None):
        return OSFUser.load(self.kwargs.get('guid'))

    def form_valid(self, form):
        user = self.get_object()
        guid_to_be_merged = form.cleaned_data['user_guid_to_be_merged']

        user_to_be_merged = OSFUser.objects.get(guids___id=guid_to_be_merged, guids___id__isnull=False)
        user.merge_user(user_to_be_merged)

        return redirect(reverse_user(user._id))

    def form_invalid(self, form):
        raise Http404(
            '{} not found.'.format(
                form.cleaned_data.get('user_guid_to_be_merged', 'guid')
            ))

class UserSearchList(PermissionRequiredMixin, ListView):
    template_name = 'users/list.html'
    permission_required = 'osf.view_osfuser'
    raise_exception = True
    form_class = UserSearchForm
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
        return super(UserSearchList, self).get_context_data(**kwargs)


class UserView(PermissionRequiredMixin, GuidView):
    template_name = 'users/user.html'
    context_object_name = 'user'
    permission_required = 'osf.view_osfuser'
    raise_exception = True

    def get_context_data(self, **kwargs):
        kwargs = super(UserView, self).get_context_data(**kwargs)
        kwargs.update({'SPAM_STATUS': SpamStatus})  # Pass spam status in to check against
        return kwargs

    def get_object(self, queryset=None):
        return serialize_user(OSFUser.load(self.kwargs.get('guid')))


class UserWorkshopFormView(PermissionRequiredMixin, FormView):
    form_class = WorkshopForm
    object_type = 'user'
    template_name = 'users/workshop.html'
    permission_required = 'osf.view_osfuser'
    raise_exception = True

    def form_valid(self, form):
        csv_file = form.cleaned_data['document']
        final = self.parse(csv_file)
        file_name = csv_file.name
        results_file_name = '{}_user_stats.csv'.format(file_name.replace(' ', '_').strip('.csv'))
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(results_file_name)
        writer = csv.writer(response)
        for row in final:
            writer.writerow(row)
        return response

    @staticmethod
    def find_user_by_email(email):
        user_list = OSFUser.objects.filter(emails__address=email)
        return user_list[0] if user_list.exists() else None

    @staticmethod
    def find_user_by_full_name(full_name):
        user_list = OSFUser.objects.filter(fullname=full_name)
        return user_list[0] if user_list.count() == 1 else None

    @staticmethod
    def find_user_by_family_name(family_name):
        user_list = OSFUser.objects.filter(family_name=family_name)
        return user_list[0] if user_list.count() == 1 else None

    @staticmethod
    def get_num_logs_since_workshop(user, workshop_date):
        query_date = workshop_date + timedelta(days=1)
        return NodeLog.objects.filter(user=user, date__gt=query_date).count()

    @staticmethod
    def get_num_nodes_since_workshop(user, workshop_date):
        query_date = workshop_date + timedelta(days=1)
        return Node.objects.filter(creator=user, created__gt=query_date).count()

    @staticmethod
    def get_user_latest_log(user, workshop_date):
        query_date = workshop_date + timedelta(days=1)
        return NodeLog.objects.filter(user=user, date__gt=query_date).latest('date')

    def parse(self, csv_file):
        """ Parse and add to csv file.

        :param csv_file: Comma separated
        :return: A list
        """
        result = []
        csv_reader = csv.reader(csv_file)

        for index, row in enumerate(csv_reader):
            if index == 0:
                row.extend([
                    'OSF ID', 'Logs Since Workshop', 'Nodes Created Since Workshop', 'Last Log Date'
                ])
                result.append(row)
                continue

            email = row[5]
            user_by_email = self.find_user_by_email(email)

            if not user_by_email:
                full_name = row[4]
                try:
                    family_name = impute_names(full_name)['family']
                except UnicodeDecodeError:
                    row.extend(['Unable to parse name'])
                    result.append(row)
                    continue

                user_by_name = self.find_user_by_full_name(full_name) or self.find_user_by_family_name(family_name)
                if not user_by_name:
                    row.extend(['', 0, 0, ''])
                    result.append(row)
                    continue
                else:
                    user = user_by_name

            else:
                user = user_by_email

            workshop_date = pytz.utc.localize(datetime.strptime(row[1], '%m/%d/%y'))
            nodes = self.get_num_nodes_since_workshop(user, workshop_date)
            user_logs = self.get_num_logs_since_workshop(user, workshop_date)
            last_log_date = self.get_user_latest_log(user, workshop_date).date.strftime('%m/%d/%y') if user_logs else ''

            row.extend([
                user._id, user_logs, nodes, last_log_date
            ])
            result.append(row)

        return result

    def form_invalid(self, form):
        super(UserWorkshopFormView, self).form_invalid(form)


class GetUserLink(PermissionRequiredMixin, TemplateView):
    permission_required = 'osf.change_osfuser'
    template_name = 'users/get_link.html'
    raise_exception = True

    def get_link(self, user):
        raise NotImplementedError()

    def get_link_type(self):
        # Used in the title of the link modal
        raise NotImplementedError()

    def get_claim_links(self, user):
        return None

    def get_context_data(self, **kwargs):
        user = OSFUser.load(self.kwargs.get('guid'))

        kwargs['user_link'] = self.get_link(user)
        kwargs['username'] = user.username
        kwargs['title'] = self.get_link_type()
        kwargs['node_claim_links'] = self.get_claim_links(user)

        return super(GetUserLink, self).get_context_data(**kwargs)


class GetUserConfirmationLink(GetUserLink):
    def get_link(self, user):
        return user.get_confirmation_url(user.username, force=True)

    def get_link_type(self):
        return 'User Confirmation'


class GetPasswordResetLink(GetUserLink):
    def get_link(self, user):
        user.verification_key_v2 = generate_verification_key(verification_type='password')
        user.verification_key_v2['expires'] = datetime.utcnow().replace(tzinfo=pytz.utc) + timedelta(hours=48)
        user.save()

        reset_abs_url = furl(DOMAIN)
        reset_abs_url.path.add(('resetpassword/{}/{}'.format(user._id, user.verification_key_v2['token'])))
        return reset_abs_url

    def get_link_type(self):
        return 'Password Reset'


class GetUserClaimLinks(GetUserLink):
    def get_claim_links(self, user):
        links = []

        for guid, value in user.unclaimed_records.items():
            obj = Guid.load(guid)
            url = '{base_url}user/{uid}/{project_id}/claim/?token={token}'.format(
                base_url=DOMAIN,
                uid=user._id,
                project_id=guid,
                token=value['token']
            )
            links.append('Claim URL for {} {}: {}'.format(obj.content_type.model, obj._id, url))

        return links or ['User currently has no active unclaimed records for any nodes.']

    def get_link(self, user):
        return None

    def get_link_type(self):
        return 'Claim User'


class ResetPasswordView(PermissionRequiredMixin, FormView):
    form_class = EmailResetForm
    template_name = 'users/reset.html'
    context_object_name = 'user'
    permission_required = 'osf.change_osfuser'
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        self.user = OSFUser.load(self.kwargs.get('guid'))
        if self.user is None:
            raise Http404(
                '{} with id "{}" not found.'.format(
                    self.context_object_name.title(),
                    self.kwargs.get('guid')
                ))
        return super(ResetPasswordView, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        self.initial = {
            'guid': self.user._id,
            'emails': [(r, r) for r in self.user.emails.values_list('address', flat=True)],
        }
        return super(ResetPasswordView, self).get_initial()

    def get_context_data(self, **kwargs):
        kwargs.setdefault('guid', self.user._id)
        kwargs.setdefault('emails', self.user.emails)
        return super(ResetPasswordView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        email = form.cleaned_data.get('emails')
        user = get_user(email)
        if user is None or user._id != self.kwargs.get('guid'):
            return HttpResponse(
                '{} with id "{}" and email "{}" not found.'.format(
                    self.context_object_name.title(),
                    self.kwargs.get('guid'),
                    email
                ),
                status=409
            )
        reset_abs_url = furl(DOMAIN)

        user.verification_key_v2 = generate_verification_key(verification_type='password')
        user.save()

        reset_abs_url.path.add(('resetpassword/{}/{}'.format(user._id, user.verification_key_v2['token'])))

        send_mail(
            subject='Reset OSF Password',
            message='Follow this link to reset your password: {}'.format(
                reset_abs_url.url
            ),
            from_email=OSF_SUPPORT_EMAIL,
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


class UserReindexElastic(UserDeleteView):
    template_name = 'users/reindex_user_elastic.html'

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        search.search.update_user(user, async_update=False)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=user._id,
            object_repr='User',
            message='User Reindexed (Elastic): {}'.format(user._id),
            action_flag=REINDEX_ELASTIC
        )
        return redirect(reverse_user(self.kwargs.get('guid')))
