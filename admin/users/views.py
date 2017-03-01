from __future__ import unicode_literals

import csv
from furl import furl
from datetime import datetime, timedelta
from django.views.generic import FormView, DeleteView, ListView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.http import Http404, HttpResponse
from django.shortcuts import redirect

from osf.models.user import OSFUser
from osf.models.node import Node, NodeLog
from osf.models.spam import SpamStatus
from osf.models.tag import Tag
from framework.auth import get_user
from framework.auth.utils import impute_names
from framework.auth.core import generate_verification_key

from website.mailchimp_utils import subscribe_on_confirm

from admin.base.views import GuidFormView, GuidView
from osf.models.admin_log_entry import (
    update_admin_log,
    USER_2_FACTOR,
    USER_EMAILED,
    USER_REMOVED,
    USER_RESTORED,
    CONFIRM_SPAM)

from admin.users.serializers import serialize_user
from admin.users.forms import EmailResetForm, WorkshopForm
from admin.users.templatetags.user_extras import reverse_user
from website.settings import DOMAIN, SUPPORT_EMAIL


class UserDeleteView(PermissionRequiredMixin, DeleteView):
    """ Allow authorised admin user to remove/restore user

    Interface with OSF database. No admin models.
    """
    template_name = 'users/remove_user.html'
    context_object_name = 'user'
    object = None
    permission_required = 'osf.change_user'
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            if user.date_disabled is None or kwargs.get('is_spam'):
                user.disable_account()
                user.is_registered = False
                if 'spam_flagged' in user.system_tags or 'ham_confirmed' in user.system_tags:
                    if 'spam_flagged' in user.system_tags:
                        t = Tag.objects.get(name='spam_flagged', system=True)
                        user.tags.remove(t)
                    if 'ham_confirmed' in user.system_tags:
                        t = Tag.objects.get(name='ham_confirmed', system=True)
                        user.tags.remove(t)
                    if 'spam_confirmed' not in user.system_tags:
                        user.add_system_tag('spam_confirmed')
                flag = USER_REMOVED
                message = 'User account {} disabled'.format(user.pk)
            else:
                user.date_disabled = None
                subscribe_on_confirm(user)
                user.is_registered = True
                if 'spam_flagged' in user.system_tags or 'spam_confirmed' in user.system_tags:
                    if 'spam_flagged' in user.system_tags:
                        t = Tag.objects.get(name='spam_flagged', system=True)
                        user.tags.remove(t)
                    if 'spam_confirmed' in user.system_tags:
                        t = Tag.objects.get(name='spam_confirmed', system=True)
                        user.tags.remove('spam_confirmed')
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
    context_object_name = '-user'
    permission_required = ('common_auth.view_spam', 'osf.view_user')
    raise_exception = True

    def get_queryset(self):
        return OSFUser.objects.filter(tags__name=self.SPAM_TAG).order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'users': map(serialize_user, query_set),
            'page': page,
        }


class UserFlaggedSpamList(UserSpamList, DeleteView):
    SPAM_TAG = 'spam_flagged'
    template_name = 'users/flagged_spam_list.html'

    def delete(self, request, *args, **kwargs):
        if not request.user.get_perms('admin.mark_spam'):
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


class UserFormView(PermissionRequiredMixin, GuidFormView):
    template_name = 'users/search.html'
    object_type = 'user'
    permission_required = 'osf.view_user'
    raise_exception = True

    @property
    def success_url(self):
        return reverse_user(self.guid)


class UserView(PermissionRequiredMixin, GuidView):
    template_name = 'users/user.html'
    context_object_name = 'user'
    permission_required = 'osf.view_user'
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
    permission_required = 'osf.view_user'
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
        user_list = OSFUser.objects.filter(emails__contains=[email])
        return user_list[0] if user_list else None

    @staticmethod
    def find_user_by_full_name(full_name):
        user_list = OSFUser.objects.filter(fullname=full_name)
        return user_list[0] if user_list.count() == 1 else None

    @staticmethod
    def find_user_by_family_name(family_name):
        user_list = OSFUser.objects.filter(family_name=family_name)
        return user_list[0] if user_list.count() == 1 else None

    @staticmethod
    def get_user_logs_since_workshop(user, workshop_date):
        query_date = workshop_date + timedelta(days=1)
        return NodeLog.objects.filter(user=user, date__gt=query_date)

    @staticmethod
    def get_user_nodes_since_workshop(user, workshop_date):
        query_date = workshop_date + timedelta(days=1)
        return Node.objects.filter(creator=user, date_created__gt=query_date)

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

            workshop_date = datetime.strptime(row[1], '%m/%d/%y')
            nodes = self.get_user_nodes_since_workshop(user, workshop_date)
            user_logs = self.get_user_logs_since_workshop(user, workshop_date)
            last_log_date = user_logs.latest().date.strftime('%m/%d/%y') if user_logs else ''

            row.extend([
                user.pk, len(user_logs), len(nodes), last_log_date
            ])
            result.append(row)

        return result

    def form_invalid(self, form):
        super(UserWorkshopFormView, self).form_invalid(form)


class ResetPasswordView(PermissionRequiredMixin, FormView):
    form_class = EmailResetForm
    template_name = 'users/reset.html'
    context_object_name = 'user'
    permission_required = 'osf.change_user'
    raise_exception = True

    def get_context_data(self, **kwargs):
        user = OSFUser.load(self.kwargs.get('guid'))
        try:
            self.initial.setdefault('emails', [(r, r) for r in user.emails])
        except AttributeError:
            raise Http404(
                '{} with id "{}" not found.'.format(
                    self.context_object_name.title(),
                    self.kwargs.get('guid')
                ))
        kwargs.setdefault('guid', user._id)
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
