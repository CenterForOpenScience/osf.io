from __future__ import unicode_literals

from furl import furl
import csv
from datetime import datetime, timedelta
from django.views.generic import FormView, DeleteView, ListView
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.http import Http404, HttpResponse
from modularodm import Q

from website.project.spam.model import SpamStatus
from website.settings import SUPPORT_EMAIL, DOMAIN
from website.security import random_string
from framework.auth import get_user
from framework.auth.utils import impute_names

from website.project.model import User, NodeLog, Node
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
    CONFIRM_SPAM)

from admin.users.serializers import serialize_user
from admin.users.forms import EmailResetForm, WorkshopForm


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
            if user.date_disabled is None or kwargs.get('is_spam'):
                user.disable_account()
                user.is_registered = False
                if 'spam_flagged' in user.system_tags or 'ham_confirmed' in user.system_tags:
                    if 'spam_flagged' in user.system_tags:
                        user.system_tags.remove('spam_flagged')
                    if 'ham_confirmed' in user.system_tags:
                        user.system_tags.remove('ham_confirmed')
                    if 'spam_confirmed' not in user.system_tags:
                        user.system_tags.append('spam_confirmed')
                flag = USER_REMOVED
                message = 'User account {} disabled'.format(user.pk)
            else:
                user.date_disabled = None
                subscribe_on_confirm(user)
                user.is_registered = True
                if 'spam_flagged' in user.system_tags or 'spam_confirmed' in user.system_tags:
                    if 'spam_flagged' in user.system_tags:
                        user.system_tags.remove('spam_flagged')
                    if 'spam_confirmed' in user.system_tags:
                        user.system_tags.remove('spam_confirmed')
                    if 'ham_confirmed' not in user.system_tags:
                        user.system_tags.append('ham_confirmed')
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
        context.setdefault('guid', kwargs.get('object').pk)
        return super(UserDeleteView, self).get_context_data(**context)

    def get_object(self, queryset=None):
        return User.load(self.kwargs.get('guid'))


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


class UserSpamList(OSFAdmin, ListView):
    SPAM_TAG = 'spam_flagged'

    paginate_by = 25
    paginate_orphans = 1
    ordering = ('date_disabled')
    context_object_name = '-user'

    def get_queryset(self):
        query = (
            Q('system_tags', 'eq', self.SPAM_TAG)
        )
        return User.find(query).sort(self.ordering)

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
        user_ids = [
            uid for uid in request.POST.keys()
            if uid != 'csrfmiddlewaretoken'
        ]
        for uid in user_ids:
            user = User.load(uid)
            if 'spam_flagged' in user.system_tags:
                user.system_tags.remove('spam_flagged')
            user.system_tags.append('spam_confirmed')
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


class UserFormView(OSFAdmin, GuidFormView):
    template_name = 'users/search.html'
    object_type = 'user'

    @property
    def success_url(self):
        return reverse_user(self.guid)


class UserView(OSFAdmin, GuidView):
    template_name = 'users/user.html'
    context_object_name = 'user'

    def get_context_data(self, **kwargs):
        kwargs = super(UserView, self).get_context_data(**kwargs)
        kwargs.update({'SPAM_STATUS': SpamStatus})  # Pass spam status in to check against
        return kwargs

    def get_object(self, queryset=None):
        return serialize_user(User.load(self.kwargs.get('guid')))


class UserWorkshopFormView(OSFAdmin, FormView):
    form_class = WorkshopForm
    object_type = 'user'
    template_name = 'users/workshop.html'

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
        user_list = User.find_by_email(email=email)
        return user_list[0] if user_list else None

    @staticmethod
    def find_user_by_full_name(full_name):
        user_list = User.find(Q('fullname', 'eq', full_name))
        return user_list[0] if user_list.count() == 1 else None

    @staticmethod
    def find_user_by_family_name(family_name):
        user_list = User.find(Q('family_name', 'eq', family_name))
        return user_list[0] if user_list.count() == 1 else None

    @staticmethod
    def get_user_logs_since_workshop(user, workshop_date):
        query_date = workshop_date + timedelta(days=1)
        query = Q('user', 'eq', user._id) & Q('date', 'gt', query_date)
        return list(NodeLog.find(query=query))

    @staticmethod
    def get_user_nodes_since_workshop(user, workshop_date):
        query_date = workshop_date + timedelta(days=1)
        query = Q('creator', 'eq', user._id) & Q('date_created', 'gt', query_date)
        return list(Node.find(query=query))

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

            try:
                last_log_date = user_logs[-1].date.strftime('%m/%d/%y')
            except IndexError:
                last_log_date = ''

            row.extend([
                user.pk, len(user_logs), len(nodes), last_log_date
            ])
            result.append(row)

        return result

    def form_invalid(self, form):
        super(UserWorkshopFormView, self).form_invalid(form)


class ResetPasswordView(OSFAdmin, FormView):
    form_class = EmailResetForm
    template_name = 'users/reset.html'
    context_object_name = 'user'

    def get_context_data(self, **kwargs):
        user = User.load(self.kwargs.get('guid'))
        try:
            self.initial.setdefault('emails', [(r, r) for r in user.emails])
        except AttributeError:
            raise Http404(
                '{} with id "{}" not found.'.format(
                    self.context_object_name.title(),
                    self.kwargs.get('guid')
                ))
        kwargs.setdefault('guid', user.pk)
        return super(ResetPasswordView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        email = form.cleaned_data.get('emails')
        user = get_user(email)
        if user is None or user.pk != self.kwargs.get('guid'):
            return HttpResponse(
                '{} with id "{}" and email "{}" not found.'.format(
                    self.context_object_name.title(),
                    self.kwargs.get('guid'),
                    email
                ),
                status=409
            )
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
