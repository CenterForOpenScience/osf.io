from __future__ import unicode_literals

from django.views.generic import UpdateView, DeleteView, ListView
from django.utils import timezone
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.defaults import page_not_found
from django.core.exceptions import PermissionDenied

from osf.models import SpamStatus
from osf.models.preprint import Preprint, PreprintLog, OSFUser
from osf.models.admin_log_entry import (
    update_admin_log,
    REINDEX_ELASTIC,
    REINDEX_SHARE,
    PREPRINT_REMOVED,
    PREPRINT_RESTORED,
    CONFIRM_SPAM,
)

from website.preprints.tasks import update_preprint_share
from website.project.views.register import osf_admin_change_status_identifier
from website import search

from framework.exceptions import PermissionsError
from admin.base.views import GuidFormView, GuidView
from admin.nodes.templatetags.node_extras import reverse_preprint
from admin.nodes.views import NodeDeleteBase, NodeRemoveContributorView, NodeConfirmSpamView, NodeConfirmHamView
from admin.preprints.serializers import serialize_preprint, serialize_simple_user_and_preprint_permissions
from admin.preprints.forms import ChangeProviderForm


class PreprintMixin(PermissionRequiredMixin):
    raise_exception = True

    def get_object(self, queryset=None):
        return Preprint.load(self.kwargs.get('guid'))


class PreprintFormView(PreprintMixin, GuidFormView):
    """ Allow authorized admin user to input specific preprint guid.
    Basic form. No admin models.
    """
    template_name = 'preprints/search.html'
    object_type = 'preprint'
    permission_required = 'osf.view_preprint'
    raise_exception = True

    @property
    def success_url(self):
        return reverse_preprint(self.guid)


class PreprintView(PreprintMixin, UpdateView, GuidView):
    """ Allow authorized admin user to view preprints
    View of OSF database. No admin models.
    """
    template_name = 'preprints/preprint.html'
    context_object_name = 'preprint'
    permission_required = 'osf.view_preprint'
    raise_exception = True
    form_class = ChangeProviderForm

    def get_success_url(self):
        return reverse_lazy('preprints:preprint', kwargs={'guid': self.kwargs.get('guid')})

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('osf.change_preprint'):
            raise PermissionsError("This user does not have permission to update this preprint's provider.")
        return super(PreprintView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        preprint = Preprint.load(self.kwargs.get('guid'))
        # TODO - we shouldn't need this serialized_preprint value -- https://openscience.atlassian.net/browse/OSF-7743
        kwargs['serialized_preprint'] = serialize_preprint(preprint)
        kwargs['change_provider_form'] = ChangeProviderForm(instance=preprint)
        kwargs.update({'SPAM_STATUS': SpamStatus})  # Pass spam status in to check against
        kwargs.update({'message': kwargs.get('message')})  # Pass spam status in to check against
        return super(PreprintView, self).get_context_data(**kwargs)


class PreprintSpamList(PermissionRequiredMixin, ListView):
    SPAM_STATE = SpamStatus.UNKNOWN

    paginate_by = 25
    paginate_orphans = 1
    ordering = ('created')
    context_object_name = 'preprint'
    permission_required = ('osf.view_spam', 'osf.view_preprint')
    raise_exception = True

    def get_queryset(self):
        return Preprint.objects.filter(spam_status=self.SPAM_STATE).order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'preprints': map(serialize_preprint, query_set),
            'page': page,
        }


class PreprintReindexShare(PreprintMixin, DeleteView):
    template_name = 'nodes/reindex_node_share.html'
    context_object_name = 'preprint'
    object = None
    permission_required = 'osf.view_preprint'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = {}
        context.setdefault('guid', kwargs.get('object')._id)
        context['link'] = 'preprints:reindex-share-preprint'
        context['resource_type'] = self.context_object_name
        return super(PreprintReindexShare, self).get_context_data(**context)

    def delete(self, request, *args, **kwargs):
        preprint = self.get_object()
        update_preprint_share(preprint)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=preprint._id,
            object_repr='Preprint',
            message='Preprint Reindexed (SHARE): {}'.format(preprint._id),
            action_flag=REINDEX_SHARE
        )
        return redirect(reverse_preprint(self.kwargs.get('guid')))


class PreprintReindexElastic(PreprintMixin, NodeDeleteBase):
    template_name = 'nodes/reindex_node_elastic.html'
    permission_required = 'osf.view_preprint'
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        preprint = self.get_object()
        search.search.update_preprint(preprint, bulk=False, async=False)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=preprint._id,
            object_repr='Preprint',
            message='Preprint Reindexed (Elastic): {}'.format(preprint._id),
            action_flag=REINDEX_ELASTIC
        )
        return redirect(reverse_preprint(self.kwargs.get('guid')))

    def get_context_data(self, **kwargs):
        context = super(PreprintReindexElastic, self).get_context_data(**kwargs)
        context['link'] = 'preprints:reindex-elastic-preprint'
        context['resource_type'] = 'preprint'
        return context


class PreprintRemoveContributorView(NodeRemoveContributorView):
    """ Allow authorized admin user to remove preprint contributor
    Interface with OSF database. No admin models.
    """
    context_object_name = 'preprint'
    permission_required = ('osf.view_preprint', 'osf.change_preprint')

    def add_contributor_removed_log(self, preprint, user):
        osf_log = PreprintLog(
            action=PreprintLog.CONTRIB_REMOVED,
            user=None,
            params={
                'preprint': preprint._id,
                'contributors': user._id
            },
            should_hide=True,
        )
        return osf_log.save()

    def delete(self, request, *args, **kwargs):
        super(PreprintRemoveContributorView, self).delete(request, args, kwargs)
        return redirect(reverse_preprint(self.kwargs.get('guid')))

    def get_context_data(self, **kwargs):
        context = {}
        preprint, user = kwargs.get('object')
        context.setdefault('guid', preprint._id)
        context.setdefault('user', serialize_simple_user_and_preprint_permissions(preprint, user))
        context.setdefault('resource_type', 'preprint')
        context.setdefault('link', 'preprints:remove_user')
        return super(NodeRemoveContributorView, self).get_context_data(**context)

    def get_object(self, queryset=None):
        return (Preprint.load(self.kwargs.get('guid')),
                OSFUser.load(self.kwargs.get('user_id')))


class PreprintDeleteView(PreprintMixin, NodeDeleteBase):
    """ Allow authorized admin user to remove/hide preprints
    Interface with OSF database. No admin models.
    """
    template_name = 'nodes/remove_node.html'
    object = None
    permission_required = ('osf.view_preprint', 'osf.delete_preprint')
    raise_exception = True
    context_object_name = 'preprint'

    def get_context_data(self, **kwargs):
        context = super(PreprintDeleteView, self).get_context_data(**kwargs)
        context['link'] = 'preprints:remove'
        context['resource_type'] = self.context_object_name
        return context

    def delete(self, request, *args, **kwargs):
        try:
            preprint = self.get_object()
            flag = None
            osf_flag = None
            message = None
            if preprint.deleted:
                preprint.deleted = None
                flag = PREPRINT_RESTORED
                message = 'Preprint {} restored.'.format(preprint.pk)
            else:
                preprint.deleted = timezone.now()
                flag = PREPRINT_REMOVED
                message = 'Preprint {} removed.'.format(preprint.pk)
                osf_flag = PreprintLog.DELETED
            preprint.save()
            if flag is not None:
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=preprint.pk,
                    object_repr='Preprint',
                    message=message,
                    action_flag=flag
                )
            if osf_flag is not None:
                # Log invisibly on the OSF.
                osf_log = PreprintLog(
                    action=osf_flag,
                    user=None,
                    params={
                        'preprint': preprint._id,
                    },
                    should_hide=True,
                )
                osf_log.save()
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    '{} with id "{}" not found.'.format(
                        self.context_object_name.title(),
                        kwargs.get('guid')
                    )
                )
            )
        return redirect(reverse_preprint(self.kwargs.get('guid')))


class PreprintFlaggedSpamList(PreprintSpamList, DeleteView):
    SPAM_STATE = SpamStatus.FLAGGED
    template_name = 'preprints/flagged_spam_list.html'

    def delete(self, request, *args, **kwargs):
        if not request.user.has_perm('auth.mark_spam'):
            raise PermissionDenied('You do not have permission to update a preprint flagged as spam.')
        preprint_ids = [
            pid for pid in request.POST.keys()
            if pid != 'csrfmiddlewaretoken'
        ]
        for pid in preprint_ids:
            preprint = Preprint.load(pid)
            osf_admin_change_status_identifier(preprint)
            preprint.confirm_spam(save=True)
            update_admin_log(
                user_id=self.request.user.id,
                object_id=pid,
                object_repr='Preprint',
                message='Confirmed SPAM: {}'.format(pid),
                action_flag=CONFIRM_SPAM
            )
        return redirect('preprints:flagged-spam')


class PreprintKnownSpamList(PreprintSpamList):
    SPAM_STATE = SpamStatus.SPAM
    template_name = 'preprints/known_spam_list.html'


class PreprintKnownHamList(PreprintSpamList):
    SPAM_STATE = SpamStatus.HAM
    template_name = 'preprints/known_spam_list.html'


class PreprintConfirmSpamView(PreprintMixin, NodeConfirmSpamView):
    object_type = 'Preprint'

    def delete(self, request, *args, **kwargs):
        super(PreprintConfirmSpamView, self).delete(request, args, kwargs)
        return redirect(reverse_preprint(self.kwargs.get('guid')))

    def get_context_data(self, **kwargs):
        context = super(PreprintConfirmSpamView, self).get_context_data(**kwargs)
        context['link'] = 'preprints:confirm-spam'
        return context


class PreprintConfirmHamView(PreprintMixin, NodeConfirmHamView):
    object_type = 'Preprint'

    def get_context_data(self, **kwargs):
        context = super(PreprintConfirmHamView, self).get_context_data(**kwargs)
        context['link'] = 'preprints:confirm-ham'
        return context

    def delete(self, request, *args, **kwargs):
        super(PreprintConfirmHamView, self).delete(request, args, kwargs)
        return redirect(reverse_preprint(self.kwargs.get('guid')))
