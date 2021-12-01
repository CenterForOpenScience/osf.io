from __future__ import unicode_literals

import csv
import pytz
from furl import furl
from datetime import datetime, timedelta
from django.db.models import F
from django.views.defaults import page_not_found
from django.views.generic import (
    View,
    FormView,
    DeleteView,
    ListView,
    TemplateView
)
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.core.paginator import Paginator

from osf.exceptions import UserStateError
from osf.models.base import Guid
from osf.models.user import OSFUser
from osf.models.node import Node, NodeLog
from osf.models.spam import SpamStatus
from framework.auth import get_user
from framework.auth.utils import impute_names
from framework.auth.core import generate_verification_key

from website.mailchimp_utils import subscribe_on_confirm
from website import search

from osf.models.admin_log_entry import (
    update_admin_log,
    USER_2_FACTOR,
    USER_EMAILED,
    USER_REMOVED,
    USER_RESTORED,
    USER_GDPR_DELETED,
    CONFIRM_SPAM,
    CONFIRM_HAM,
    REINDEX_ELASTIC,
)

from admin.users.forms import EmailResetForm, WorkshopForm, UserSearchForm, MergeUserForm, AddSystemTagForm
from admin.users.templatetags.user_extras import reverse_user
from website.settings import DOMAIN, OSF_SUPPORT_EMAIL
from django.urls import reverse_lazy


class UserMixin(PermissionRequiredMixin):

    def get_object(self):
        user = OSFUser.objects.get(guids___id=self.kwargs['guid'])
        user.guid = user._id
        return user

    def get_success_url(self):
        return reverse('users:user', kwargs={'guid': self.kwargs['guid']})


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

                if kwargs.get('is_spam'):
                    user.confirm_spam()
                flag = USER_REMOVED
                message = 'User account {} disabled'.format(user.pk)
            else:
                user.requested_deactivation = False
                user.date_disabled = None
                subscribe_on_confirm(user)
                user.is_registered = True
                user.tags.through.objects.filter(tag__name__in=['spam_flagged', 'spam_confirmed'], tag__system=True).delete()
                user.confirm_ham()
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


class UserGDPRDeleteView(PermissionRequiredMixin, DeleteView):
    """ Allow authorised admin user to totally erase user data.

    Interface with OSF database. No admin models.
    """
    template_name = 'users/GDPR_delete_user.html'
    context_object_name = 'user'
    object = None
    permission_required = 'osf.change_osfuser'
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            user.gdpr_delete()
            user.save()
            message = 'User {} was successfully GDPR deleted'.format(user._id)
            messages.success(request, message)
            update_admin_log(
                user_id=self.request.user.id,
                object_id=user.pk,
                object_repr='User',
                message=message,
                action_flag=USER_GDPR_DELETED
            )
        except UserStateError as e:
            messages.warning(request, str(e))

        return redirect(reverse_user(self.kwargs.get('guid')))

    def get_context_data(self, **kwargs):
        context = {}
        context.setdefault('guid', kwargs.get('object')._id)
        return super(UserGDPRDeleteView, self).get_context_data(**context)

    def get_object(self, queryset=None):
        user = OSFUser.load(self.kwargs.get('guid'))
        if user:
            return user
        else:
            raise Http404(
                '{} with id "{}" not found.'.format(
                    self.context_object_name.title(),
                    self.kwargs.get('guid')
                ))


class SpamUserView(UserMixin, View):
    """
    Allow authorized admin user to delete a spam user and mark all their nodes as private

    """

    template_name = 'users/remove_spam_user.html'

    def post(self, request, *args, **kwargs):
        user = self.get_object()

        for node in user.contributor_or_group_member_to:
            if not node.is_registration and not node.is_spam:
                node.confirm_spam(save=True)
                update_admin_log(
                    user_id=request.user.id,
                    object_id=node._id,
                    object_repr='Node',
                    message=f'Confirmed SPAM: {node._id} when user {user._id} marked as spam',
                    action_flag=CONFIRM_SPAM
                )
        return redirect(self.get_success_url())


class HamUserRestoreView(UserDeleteView):
    """
    Allow authorized admin user to undelete a ham user
    """

    template_name = 'users/restore_ham_user.html'

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        if not user:
            raise Http404(
                '{} with id "{}" not found.'.format(
                    self.context_object_name.title(),
                    self.kwargs.get('guid')
                ))
        user.tags.through.objects.filter(tag__name__in=['spam_flagged', 'spam_confirmed'], tag__system=True).delete()
        user.confirm_ham(save=True)
        for node in user.contributor_or_group_member_to:
            if node.is_spam:
                node.confirm_ham(save=True)
                update_admin_log(
                    user_id=request.user.id,
                    object_id=node._id,
                    object_repr='Node',
                    message='Confirmed HAM: {} when user {} marked as ham'.format(node._id, user._id),
                    action_flag=CONFIRM_SPAM
                )
        if not user.is_active:
            # Allow superclass to restore and mark ham
            kwargs.update({'is_spam': False})
            return super(HamUserRestoreView, self).delete(request, *args, **kwargs)
        return redirect(reverse_user(self.kwargs.get('guid')))


class UserSpamList(PermissionRequiredMixin, ListView):
    SPAM_STATUS = SpamStatus.UNKNOWN

    paginate_by = 25
    paginate_orphans = 1
    ordering = ('date_disabled')
    permission_required = ('osf.view_spam', 'osf.view_osfuser')
    raise_exception = True

    def get_queryset(self):
        return OSFUser.objects.filter(
            spam_status=self.SPAM_STATUS
        ).order_by(
            self.ordering
        ).annotate(guid=F('guids___id'))

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'users': query_set,
            'page': page,
            'SPAM_STATUS': SpamStatus,
        }


class UserFlaggedSpamList(UserSpamList, DeleteView):
    SPAM_STATUS = SpamStatus.FLAGGED
    template_name = 'users/flagged_spam_list.html'

    def delete(self, request, *args, **kwargs):
        if not request.user.has_perm('osf.mark_spam'):
            raise PermissionDenied("You don't have permission to update this user's spam status.")

        data = dict(request.POST)

        action = data.pop('action')[0]
        data.pop('csrfmiddlewaretoken', None)

        if action == 'spam':
            for user_id in list(data):
                user = OSFUser.objects.get(id=user_id)
                user.confirm_spam()
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=user_id,
                    object_repr='User',
                    message=f'Confirmed SPAM: {user_id}',
                    action_flag=CONFIRM_SPAM
                )
                user.save()

        if action == 'ham':
            for user_id in list(data):
                user = OSFUser.objects.get(id=user_id)
                user.confirm_ham(save=True)
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=user_id,
                    object_repr='User',
                    message=f'Confirmed HAM: {user_id}',
                    action_flag=CONFIRM_HAM
                )
                user.save()

        return redirect('users:flagged-spam')


class UserKnownSpamList(UserSpamList):
    SPAM_STATUS = SpamStatus.SPAM
    template_name = 'users/known_spam_list.html'


class UserKnownHamList(UserSpamList):
    SPAM_STATUS = SpamStatus.HAM
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
            raise Http404(f'user with id "{self.kwargs.get("guid")}" not found.')
        update_admin_log(
            user_id=self.request.user.id,
            object_id=user.pk,
            object_repr='User',
            message='Removed 2 factor auth for user {}'.format(user.pk),
            action_flag=USER_2_FACTOR
        )
        return redirect(self.get_success_url())


class UserAddSystemTag(PermissionRequiredMixin, FormView):

    template_name = 'users/add_system_tag.html'
    object_type = 'osfuser'
    permission_required = 'osf.change_osfuser'
    raise_exception = True
    form_class = AddSystemTagForm

    def get_success_url(self, *args, **kwargs):
        return reverse('users:user', kwargs={'guid': self.kwargs.get('guid')})

    def get_object(self, queryset=None):
        return OSFUser.load(self.kwargs.get('guid'))

    def get_context_data(self, **kwargs):
        return {'guid': self.get_object()._id}

    def form_valid(self, form):
        user = self.get_object()
        system_tag_to_add = form.cleaned_data['system_tag_to_add']
        user.add_system_tag(system_tag_to_add)
        user.save()

        return super().form_valid(form)


class UserSearchView(PermissionRequiredMixin, FormView):
    template_name = 'users/search.html'
    object_type = 'osfuser'
    permission_required = 'osf.view_osfuser'
    raise_exception = True
    form_class = UserSearchForm
    success_url = reverse_lazy('users:search')

    def __init__(self, *args, **kwargs):
        self.redirect_url = None
        super().__init__(*args, **kwargs)

    def form_valid(self, form):
        guid = form.cleaned_data['guid']
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']
        print(locals())
        if name:
            return redirect(reverse('users:search_list', kwargs={'name': name}))

        if email:
            user = get_user(email)
            if not user:
                return page_not_found(
                    self.request,
                    AttributeError(f'resource with id "{email}" not found.')
                )
            return redirect(reverse('users:user', kwargs={'guid': user._id}))

        if guid:
            user = OSFUser.load(guid)
            if not user:
                return page_not_found(
                    self.request,
                    AttributeError(f'resource with id "{guid}" not found.')
                )

            return redirect(reverse('users:user', kwargs={'guid': guid}))

        return super().form_valid(form)


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
        return OSFUser.objects.filter(
            fullname__icontains=self.kwargs['name']
        ).annotate(
            guid=F('guids___id')
        )

    def get_context_data(self, **kwargs):
        users = self.get_queryset()
        page_size = self.get_paginate_by(users)
        paginator, page, query_set, is_paginated = self.paginate_queryset(users, page_size)
        return super().get_context_data(
            **kwargs,
            **{
                'page': page,
                'users': query_set
            }
        )


class UserView(UserMixin, TemplateView):
    template_name = 'users/user.html'
    paginate_by = 10
    permission_required = 'osf.view_osfuser'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()

        # Django template does not like attributes with underscores for some reason
        preprints = user.preprints.filter(
            deleted=None
        ).annotate(
            guid=F('guids___id')
        ).order_by(
            'title'
        )

        nodes = user.contributor_or_group_member_to.annotate(
            guid=F('guids___id')
        ).order_by(
            'title'
        )
        context.update(self.get_paginated_queryset(preprints, 'preprint'))
        context.update(self.get_paginated_queryset(nodes, 'node'))

        context.update({'user': user})
        context.update({'potential_spam_profile_content': user._get_spam_content({
            'schools': user.schools,
            'jobs': user.jobs
        })})
        context.update({'form': EmailResetForm(initial={
            'emails': [(r, r) for r in self.get_object().emails.values_list('address', flat=True)],
        })})
        return context

    def get_paginated_queryset(self, queryset, resource_type):
        page_num = self.request.GET.get(f'{resource_type}_page', 1)
        paginator = Paginator(queryset, self.paginate_by)
        queryset = paginator.page(page_num)
        return {
            f'{resource_type}s': queryset,
            f'{resource_type}_page': paginator.page(page_num),
            f'current_{resource_type}': f'&{resource_type}_page=' + str(queryset.number)
        }


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


class GetUserLink(UserMixin, TemplateView):
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
        user = self.get_object()
        return super().get_context_data(**{
                'user':  user,
                'user_link': self.get_link(user),
                'title':  self.get_link_type(),
                'node_claim_links': self.get_claim_links(user),
        }, **kwargs)


class GetUserConfirmationLink(GetUserLink):
    def get_link(self, user):
        try:
            return user.get_confirmation_url(user.username, force=True)
        except KeyError as e:
            return str(e)

    def get_link_type(self):
        return 'User Confirmation'


class GetPasswordResetLink(GetUserLink):
    def get_link(self, user):
        user.verification_key_v2 = generate_verification_key(verification_type='password')
        user.verification_key_v2['expires'] = datetime.utcnow().replace(tzinfo=pytz.utc) + timedelta(hours=48)
        user.save()

        reset_abs_url = furl(DOMAIN)
        reset_abs_url.path.add(f'resetpassword/{user._id}/{user.verification_key_v2["token"]}')
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


class ResetPasswordView(UserMixin, View):
    permission_required = 'osf.change_osfuser'

    def post(self, request, *args, **kwargs):
        email = self.request.POST['emails']
        user = get_user(email)
        if user is None or user._id != self.kwargs.get('guid'):
            return HttpResponse(
                f'user with id "{self.kwargs.get("guid")}" and email "{email}" not found.',
                status=409
            )

        reset_abs_url = furl(DOMAIN)
        reset_abs_url.path.add(f'resetpassword/{user._id}/{user.verification_key_v2["token"]}')

        user.verification_key_v2 = generate_verification_key(verification_type='password')
        user.save()

        send_mail(
            subject='Reset OSF Password',
            message=f'Follow this link to reset your password: {reset_abs_url.url}',
            from_email=OSF_SUPPORT_EMAIL,
            recipient_list=[email]
        )
        update_admin_log(
            user_id=self.request.user.id,
            object_id=user.pk,
            object_repr='User',
            message=f'Emailed user {user.pk} a reset link.',
            action_flag=USER_EMAILED
        )

        return redirect(self.get_success_url())


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
