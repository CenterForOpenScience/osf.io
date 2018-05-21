from __future__ import unicode_literals

from django.views.generic import UpdateView, DeleteView
from django.utils import timezone
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.defaults import page_not_found

from osf.models.preprint import Preprint, PreprintLog, OSFUser
from osf.models.admin_log_entry import update_admin_log, REINDEX_SHARE, CONTRIBUTOR_REMOVED, PREPRINT_REMOVED, PREPRINT_RESTORED

from website.preprints.tasks import update_preprint_share

from framework.exceptions import PermissionsError
from admin.base.views import GuidFormView, GuidView
from admin.nodes.templatetags.node_extras import reverse_preprint
from admin.nodes.views import NodeDeleteBase
from admin.preprints.serializers import serialize_preprint, serialize_simple_user_and_preprint_permissions
from admin.preprints.forms import ChangeProviderForm


class PreprintFormView(PermissionRequiredMixin, GuidFormView):
    """ Allow authorized admin user to input specific preprint guid.

    Basic form. No admin models.
    """
    template_name = 'preprints/search.html'
    object_type = 'preprint'
    permission_required = 'osf.osf_admin_view_preprint'
    raise_exception = True

    @property
    def success_url(self):
        return reverse_preprint(self.guid)


class PreprintView(PermissionRequiredMixin, UpdateView, GuidView):
    """ Allow authorized admin user to view preprints

    View of OSF database. No admin models.
    """
    template_name = 'preprints/preprint.html'
    context_object_name = 'preprint'
    permission_required = 'osf.osf_admin_view_preprint'
    raise_exception = True
    form_class = ChangeProviderForm

    def get_success_url(self):
        return reverse_lazy('preprints:preprint', kwargs={'guid': self.kwargs.get('guid')})

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('osf.change_preprint'):
            raise PermissionsError("This user does not have permission to update this preprint's provider.")
        return super(PreprintView, self).post(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return Preprint.load(self.kwargs.get('guid'))

    def get_context_data(self, **kwargs):
        preprint = Preprint.load(self.kwargs.get('guid'))
        # TODO - we shouldn't need this serialized_preprint value -- https://openscience.atlassian.net/browse/OSF-7743
        kwargs['serialized_preprint'] = serialize_preprint(preprint)
        kwargs['change_provider_form'] = ChangeProviderForm(instance=preprint)
        return super(PreprintView, self).get_context_data(**kwargs)


class PreprintReindexShare(PermissionRequiredMixin, DeleteView):
    template_name = 'preprints/reindex_preprint_share.html'
    context_object_name = 'preprint'
    object = None
    permission_required = 'osf.osf_admin_view_preprint'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = {}
        context.setdefault('guid', kwargs.get('object')._id)
        return super(PreprintReindexShare, self).get_context_data(**context)

    def get_object(self, queryset=None):
        return Preprint.load(self.kwargs.get('guid'))

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


class PreprintRemoveContributorView(PermissionRequiredMixin, DeleteView):
    """ Allow authorized admin user to remove preprint contributor

    Interface with OSF database. No admin models.
    """
    template_name = 'preprints/remove_preprintcontributor.html'
    context_object_name = 'preprint'
    permission_required = ('osf.osf_admin_view_preprint', 'osf.change_preprint')
    raise_exception = True

    def delete(self, request, *args, **kwargs):
        try:
            preprint, user = self.get_object()
            if preprint.remove_contributor(user, None, log=False):
                update_admin_log(
                    user_id=self.request.user.id,
                    object_id=preprint.pk,
                    object_repr='Contributor',
                    message='User {} removed from preprint {}.'.format(
                        user.pk, preprint.pk
                    ),
                    action_flag=CONTRIBUTOR_REMOVED
                )
                # Log invisibly on the OSF.
                osf_log = PreprintLog(
                    action=PreprintLog.CONTRIB_REMOVED,
                    user=None,
                    params={
                        'preprint': preprint._id,
                        'contributors': user.pk
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

    def get_context_data(self, **kwargs):
        context = {}
        preprint, user = kwargs.get('object')
        context.setdefault('guid', preprint._id)
        context.setdefault('user', serialize_simple_user_and_preprint_permissions(preprint, user))
        context.setdefault('is_preprint', True)
        return super(PreprintRemoveContributorView, self).get_context_data(**context)

    def get_object(self, queryset=None):
        return (Preprint.load(self.kwargs.get('guid')),
                OSFUser.load(self.kwargs.get('user_id')))


class PreprintDeleteView(PermissionRequiredMixin, NodeDeleteBase):
    """ Allow authorized admin user to remove/hide preprints

    Interface with OSF database. No admin models.
    """
    template_name = 'preprints/remove_preprint.html'
    object = None
    permission_required = ('osf.osf_admin_view_preprint', 'osf.delete_preprint')
    raise_exception = True
    context_object_name = 'preprint'

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
                osf_flag = PreprintLog.CREATED
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
