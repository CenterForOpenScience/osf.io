import pytz
import markupsafe
import logging

from django.apps import apps
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.functional import cached_property
from guardian.shortcuts import assign_perm, get_perms, remove_perm, get_group_perms

from include import IncludeQuerySet

from api.providers.workflows import Workflows, PUBLIC_STATES
from framework import status
from framework.auth.core import get_user
from framework.analytics import increment_user_activity_counters
from framework.exceptions import PermissionsError
from osf.exceptions import (
    InvalidTriggerError,
    ValidationValueError,
    UserStateError,
    BlacklistedEmailError
)
from osf.models.node_relation import NodeRelation
from osf.models.nodelog import NodeLog
from osf.models.subject import Subject
from osf.models.spam import SpamMixin, SpamStatus
from osf.models.tag import Tag
from osf.models.validators import validate_subject_hierarchy, validate_email, expand_subject_hierarchy
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.machines import ReviewsMachine, NodeRequestMachine, PreprintRequestMachine
from osf.utils.permissions import ADMIN, REVIEW_GROUPS, READ, WRITE
from osf.utils.workflows import DefaultStates, DefaultTriggers, ReviewStates, ReviewTriggers
from osf.utils.requests import get_request_and_user_id
from website.project import signals as project_signals
from website import settings, mails, language


logger = logging.getLogger(__name__)

class Versioned(models.Model):
    """A Model mixin class that saves delta versions."""

    @classmethod
    def _sig_pre_delete(cls, instance, *args, **kwargs):
        """dispatch the pre_delete method to a regular instance method. """
        return instance.sig_pre_delete(*args, **kwargs)

    @classmethod
    def _sig_post_delete(cls, instance, *args, **kwargs):
        """dispatch the post_delete method to a regular instance method. """
        return instance.sig_post_delete(*args, **kwargs)

    @classmethod
    def _sig_pre_save(cls, instance, *args, **kwargs):
        """dispatch the pre_save method to a regular instance method. """
        return instance.sig_pre_save(*args, **kwargs)

    @classmethod
    def _sig_post_save(cls, instance, *args, **kwargs):
        """dispatch the post_save method to a regular instance method. """
        return instance.sig_post_save(*args, **kwargs)

    @classmethod
    def connect(cls, signal):
        """Connect a django signal with this model."""
        # List all signals you want to connect with here:
        from django.db.models.signals import (pre_save, post_save, pre_delete, post_delete)
        sig_handler = {
            pre_save: cls._sig_pre_save,
            post_save: cls._sig_post_save,
            pre_delete: cls._sig_pre_delete,
            post_delete: cls._sig_post_delete,
        }[signal]
        signal.connect(sig_handler, sender=cls)

    class Meta:
        abstract = True


class Loggable(models.Model):

    last_logged = NonNaiveDateTimeField(db_index=True, null=True, blank=True, default=timezone.now)

    def add_log(self, action, params, auth, foreign_user=None, log_date=None, save=True, request=None):
        AbstractNode = apps.get_model('osf.AbstractNode')
        user = None
        if auth:
            user = auth.user
        elif request:
            user = request.user

        params['node'] = params.get('node') or params.get('project') or self._id
        original_node = self if self._id == params['node'] else AbstractNode.load(params.get('node'))

        log = NodeLog(
            action=action, user=user, foreign_user=foreign_user,
            params=params, node=self, original_node=original_node
        )

        if log_date:
            log.date = log_date
        log.save()

        self._complete_add_log(log, action, user, save)

        return log

    def _complete_add_log(self, log, action, user=None, save=True):
        if self.logs.count() == 1:
            log_date = log.date if hasattr(log, 'date') else log.created
            self.last_logged = log_date.replace(tzinfo=pytz.utc)
        else:
            recent_log = self.logs.first()
            log_date = recent_log.date if hasattr(log, 'date') else recent_log.created
            self.last_logged = log_date

        if save:
            self.save()
        if user and not getattr(self, 'is_collection', None):
            increment_user_activity_counters(user._primary_key, action, self.last_logged.isoformat())

    class Meta:
        abstract = True


class Taggable(models.Model):

    tags = models.ManyToManyField('Tag', related_name='%(class)s_tagged')

    def update_tags(self, new_tags, auth=None, save=True, log=True, system=False):
        old_tags = set(self.tags.values_list('name', flat=True))
        to_add = (set(new_tags) - old_tags)
        to_remove = (old_tags - set(new_tags))
        if to_add:
            self.add_tags(to_add, auth=auth, save=save, log=log, system=system)
        if to_remove:
            self.remove_tags(to_remove, auth=auth, save=save)

    def add_tags(self, tags, auth=None, save=True, log=True, system=False):
        """
        Optimization method for use with update_tags. Unlike add_tag, already assumes tag is
        not on the object.
        """
        if not system and not auth:
            raise ValueError('Must provide auth if adding a non-system tag')
        for tag in tags:
            tag_instance, created = Tag.all_tags.get_or_create(name=tag, system=system)
            self.tags.add(tag_instance)
            # TODO: Logging belongs in on_tag_added hook
            if log:
                self.add_tag_log(tag_instance, auth)
            self.on_tag_added(tag_instance)
        if save:
            self.save()

    def add_tag(self, tag, auth=None, save=True, log=True, system=False):
        if not system and not auth:
            raise ValueError('Must provide auth if adding a non-system tag')

        if not isinstance(tag, Tag):
            tag_instance, created = Tag.all_tags.get_or_create(name=tag, system=system)
        else:
            tag_instance = tag

        if not self.tags.filter(id=tag_instance.id).exists():
            self.tags.add(tag_instance)
            # TODO: Logging belongs in on_tag_added hook
            if log:
                self.add_tag_log(tag_instance, auth)
            if save:
                self.save()
            self.on_tag_added(tag_instance)
        return tag_instance

    def remove_tag(self, *args, **kwargs):
        raise NotImplementedError('Removing tags requires that remove_tag is implemented')

    def add_system_tag(self, tag, save=True):
        if isinstance(tag, Tag) and not tag.system:
            raise ValueError('Non-system tag passed to add_system_tag')
        return self.add_tag(tag=tag, auth=None, save=save, log=False, system=True)

    def add_tag_log(self, *args, **kwargs):
        raise NotImplementedError('Logging requires that add_tag_log method is implemented')

    def on_tag_added(self, tag):
        pass

    class Meta:
        abstract = True


class AddonModelMixin(models.Model):

    # from addons.base.apps import BaseAddonConfig
    settings_type = None
    ADDONS_AVAILABLE = sorted([config for config in apps.get_app_configs() if config.name.startswith('addons.') and
        config.label != 'base'], key=lambda config: config.name)

    class Meta:
        abstract = True

    @classmethod
    def get_addon_key(cls, config):
        return 2 << cls.ADDONS_AVAILABLE.index(config)

    @property
    def addons(self):
        return self.get_addons()

    def get_addons(self):
        return [_f for _f in [
            self.get_addon(config.short_name)
            for config in self.ADDONS_AVAILABLE
        ] if _f]

    def get_oauth_addons(self):
        # TODO: Using hasattr is a dirty hack - we should be using issubclass().
        #       We can't, because importing the parent classes here causes a
        #       circular import error.
        return [
            addon for addon in self.get_addons()
            if hasattr(addon, 'oauth_provider')
        ]

    def has_addon(self, addon_name, deleted=False):
        return bool(self.get_addon(addon_name, deleted=deleted))

    def get_addon_names(self):
        return [each.short_name for each in self.get_addons()]

    def get_or_add_addon(self, name, *args, **kwargs):
        addon = self.get_addon(name)
        if addon:
            return addon
        return self.add_addon(name, *args, **kwargs)

    def get_addon(self, name, deleted=False):
        try:
            settings_model = self._settings_model(name)
        except LookupError:
            return None
        if not settings_model:
            return None
        try:
            settings_obj = settings_model.objects.get(owner=self)
            if not settings_obj.deleted or deleted:
                return settings_obj
        except ObjectDoesNotExist:
            pass
        return None

    def add_addon(self, addon_name, auth=None, override=False, _force=False):
        """Add an add-on to the node.

        :param str addon_name: Name of add-on
        :param Auth auth: Consolidated authorization object
        :param bool override: For shell use only, Allows adding of system addons
        :param bool _force: For migration testing ONLY. Do not set to True
            in the application, or else projects will be allowed to have
            duplicate addons!
        :return bool: Add-on was added

        """
        if not override and addon_name in settings.SYSTEM_ADDED_ADDONS[self.settings_type]:
            return False

        # Reactivate deleted add-on if present
        addon = self.get_addon(addon_name, deleted=True)
        if addon:
            if addon.deleted:
                addon.undelete(save=True)
                return addon
            if not _force:
                return False

        config = apps.get_app_config('addons_{}'.format(addon_name))
        model = self._settings_model(addon_name, config=config)
        ret = model(owner=self)
        ret.on_add()
        ret.save(clean=False)  # TODO This doesn't feel right
        return ret

    def config_addons(self, config, auth=None, save=True):
        """Enable or disable a set of add-ons.

        :param dict config: Mapping between add-on names and enabled / disabled
            statuses
        """
        for addon_name, enabled in config.items():
            if enabled:
                self.add_addon(addon_name, auth)
            else:
                self.delete_addon(addon_name, auth)
        if save:
            self.save()

    def delete_addon(self, addon_name, auth=None, _force=False):
        """Delete an add-on from the node.

        :param str addon_name: Name of add-on
        :param Auth auth: Consolidated authorization object
        :param bool _force: For migration testing ONLY. Do not set to True
            in the application, or else projects will be allowed to delete
            mandatory add-ons!
        :return bool: Add-on was deleted
        """
        addon = self.get_addon(addon_name)
        if not addon:
            return False
        if self.settings_type in addon.config.added_mandatory and not _force:
            raise ValueError('Cannot delete mandatory add-on.')
        if getattr(addon, 'external_account', None):
            addon.deauthorize(auth=auth)
        addon.delete(save=True)
        return True

    def _settings_model(self, addon_model, config=None):
        if not config:
            config = apps.get_app_config('addons_{}'.format(addon_model))
        return getattr(config, '{}_settings'.format(self.settings_type))


class NodeLinkMixin(models.Model):

    class Meta:
        abstract = True

    def add_node_link(self, node, auth, save=True):
        """Add a node link to a node.

        :param Node node: Node to add
        :param Auth auth: Consolidated authorization
        :param bool save: Save changes
        :return: Created pointer
        """
        try:
            self.check_node_link(child_node=node, parent_node=self)
            self.check_node_link(child_node=self, parent_node=node)
        except ValueError as e:
            raise ValueError(e.message)

        if self.is_registration:
            raise self.state_error('Cannot add a node link to a registration')

        # Append node link
        node_relation, created = NodeRelation.objects.get_or_create(
            parent=self,
            child=node,
            is_node_link=True
        )

        # Add log
        if hasattr(self, 'add_log'):
            self.add_log(
                action=NodeLog.NODE_LINK_CREATED,
                params={
                    'parent_node': self.parent_id,
                    'node': self._id,
                    'pointer': {
                        'id': node._id,
                        'url': node.url,
                        'title': node.title,
                        'category': node.category,
                    },
                },
                auth=auth,
                save=False,
            )

        # Optionally save changes
        if save:
            self.save()

        return node_relation

    add_pointer = add_node_link  # For v1 compat

    def check_node_link(self, child_node, parent_node):
        if child_node._id == parent_node._id:
            raise ValueError(
                'Cannot link node \'{}\' to itself.'.format(child_node._id)
            )
        existant_relation = NodeRelation.objects.filter(parent=parent_node, child=child_node).first()
        if existant_relation and existant_relation.is_node_link:
            raise ValueError(
                'Target Node \'{}\' already pointed to by \'{}\'.'.format(child_node._id, parent_node._id)
            )
        elif existant_relation and not existant_relation.is_node_link:
            raise ValueError(
                'Target Node \'{}\' is already a child of \'{}\'.'.format(child_node._id, parent_node._id)
            )

    def rm_node_link(self, node_relation, auth):
        """Remove a pointer.

        :param Pointer pointer: Pointer to remove
        :param Auth auth: Consolidated authorization
        """
        AbstractNode = apps.get_model('osf.AbstractNode')

        node_rel = None
        if isinstance(node_relation, NodeRelation):
            try:
                node_rel = self.node_relations.get(is_node_link=True, id=node_relation.id)
            except NodeRelation.DoesNotExist:
                raise ValueError('Node link does not belong to the requested node.')
        elif isinstance(node_relation, AbstractNode):
            try:
                node_rel = self.node_relations.get(is_node_link=True, child__id=node_relation.id)
            except NodeRelation.DoesNotExist:
                raise ValueError('Node link does not belong to the requested node.')
        if node_rel is not None:
            node_rel.delete()

        node = node_rel.child
        # Add log
        if hasattr(self, 'add_log'):
            self.add_log(
                action=NodeLog.POINTER_REMOVED,
                params={
                    'parent_node': self.parent_id,
                    'node': self._primary_key,
                    'pointer': {
                        'id': node._id,
                        'url': node.url,
                        'title': node.title,
                        'category': node.category,
                    },
                },
                auth=auth,
                save=False,
            )

    rm_pointer = rm_node_link  # For v1 compat

    @property
    def nodes_pointer(self):
        """For v1 compat"""
        return self.linked_nodes

    def fork_node_link(self, node_relation, auth, save=True):
        """Replace a linked node with a fork.

        :param NodeRelation node_relation:
        :param Auth auth:
        :param bool save:
        :return: Forked node
        """
        # Fail if pointer not contained in `nodes`
        try:
            node = self.node_relations.get(is_node_link=True, id=node_relation.id).child
        except NodeRelation.DoesNotExist:
            raise ValueError('Node link {0} not in list'.format(node_relation._id))

        # Fork node to which current nodelink points
        forked = node.fork_node(auth)
        if forked is None:
            raise ValueError('Could not fork node')

        if hasattr(self, 'add_log'):
            # Add log
            self.add_log(
                NodeLog.NODE_LINK_FORKED,
                params={
                    'parent_node': self.parent_id,
                    'node': self._id,
                    'pointer': {
                        'id': node._id,
                        'url': node.url,
                        'title': node.title,
                        'category': node.category,
                    },
                },
                auth=auth,
                save=False,
            )

        # Optionally save changes
        if save:
            self.save()

        # Return forked content
        return forked

    fork_pointer = fork_node_link  # For v1 compat


class CommentableMixin(object):
    """Abstract class that defines the interface for models that have comments attached to them."""

    @property
    def target_type(self):
        """ The object "type" used in the OSF v2 API. E.g. Comment objects have the type 'comments'."""
        raise NotImplementedError

    @property
    def root_target_page(self):
        """The page type associated with the object/Comment.root_target.
        E.g. For a WikiPage, the page name is 'wiki'."""
        raise NotImplementedError

    is_deleted = False

    def belongs_to_node(self, node_id):
        """Check whether an object (e.g. file, wiki, comment) is attached to the specified node."""
        raise NotImplementedError

    def get_extra_log_params(self, comment):
        """Return extra data to pass as `params` to `Node.add_log` when a new comment is
        created, edited, deleted or restored."""
        return {}


class MachineableMixin(models.Model):
    TriggersClass = DefaultTriggers

    class Meta:
        abstract = True

    # NOTE: machine_state should rarely/never be modified directly -- use the state transition methods below
    machine_state = models.CharField(max_length=15, db_index=True, choices=DefaultStates.choices(), default=DefaultStates.INITIAL.value)

    date_last_transitioned = models.DateTimeField(null=True, blank=True, db_index=True)

    @property
    def MachineClass(self):
        raise NotImplementedError()

    def run_submit(self, user):
        """Run the 'submit' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
        """
        return self._run_transition(self.TriggersClass.SUBMIT.value, user=user)

    def run_accept(self, user, comment, **kwargs):
        """Run the 'accept' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
            comment: Text describing why.
        """
        return self._run_transition(self.TriggersClass.ACCEPT.value, user=user, comment=comment, **kwargs)

    def run_reject(self, user, comment):
        """Run the 'reject' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
            comment: Text describing why.
        """
        return self._run_transition(self.TriggersClass.REJECT.value, user=user, comment=comment)

    def run_edit_comment(self, user, comment):
        """Run the 'edit_comment' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
            comment: New comment text.
        """
        return self._run_transition(self.TriggersClass.EDIT_COMMENT.value, user=user, comment=comment)

    def _run_transition(self, trigger, **kwargs):
        machine = self.MachineClass(self, 'machine_state')
        trigger_fn = getattr(machine, trigger)
        with transaction.atomic():
            result = trigger_fn(**kwargs)
            action = machine.action
            if not result or action is None:
                valid_triggers = machine.get_triggers(self.machine_state)
                raise InvalidTriggerError(trigger, self.machine_state, valid_triggers)
            return action


class NodeRequestableMixin(MachineableMixin):
    """
    Inherited by NodeRequest. Defines the MachineClass.
    """

    class Meta:
        abstract = True

    MachineClass = NodeRequestMachine


class PreprintRequestableMixin(MachineableMixin):
    """
    Inherited by PreprintRequest. Defines the MachineClass
    """

    class Meta:
        abstract = True

    MachineClass = PreprintRequestMachine


class ReviewableMixin(MachineableMixin):
    """Something that may be included in a reviewed collection and is subject to a reviews workflow.
    """
    TriggersClass = ReviewTriggers

    machine_state = models.CharField(max_length=15, db_index=True, choices=ReviewStates.choices(), default=ReviewStates.INITIAL.value)

    class Meta:
        abstract = True

    MachineClass = ReviewsMachine

    @property
    def in_public_reviews_state(self):
        public_states = PUBLIC_STATES.get(self.provider.reviews_workflow)
        if not public_states:
            return False
        return self.machine_state in public_states

    def run_withdraw(self, user, comment):
        """Run the 'withdraw' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
            comment: Text describing why.
        """
        return self._run_transition(self.TriggersClass.WITHDRAW.value, user=user, comment=comment)


class GuardianMixin(models.Model):
    """ Helper for managing object-level permissions with django-guardian
    Expects:
      - Permissions to be defined in class Meta->permissions
      - Groups to be defined in self.groups
      - Group naming scheme to:
        * Be defined in self.group_format
        * Use `self` and `group` as format params. E.g: model_{self.id}_{group}
    """
    class Meta:
        abstract = True

    @property
    def groups(self):
        raise NotImplementedError()

    @property
    def group_format(self):
        raise NotImplementedError()

    @property
    def perms_list(self):
        # Django expects permissions to be specified in an N-ple of 2-ples
        return [p[0] for p in self._meta.permissions]

    @property
    def group_names(self):
        return [self.format_group(name) for name in self.groups.keys()]

    @property
    def group_objects(self):
        # TODO: consider subclassing Group if this becomes inefficient
        return Group.objects.filter(name__in=self.group_names)

    def format_group(self, name):
        if name not in self.groups:
            raise ValueError('Invalid group: "{}"'.format(name))
        return self.group_format.format(self=self, group=name)

    def get_group(self, name):
        return Group.objects.get(name=self.format_group(name))

    def update_group_permissions(self):
        for group_name, group_permissions in self.groups.items():
            group, created = Group.objects.get_or_create(name=self.format_group(group_name))
            to_remove = set(get_perms(group, self)).difference(group_permissions)
            for p in to_remove:
                remove_perm(p, group, self)
            for p in group_permissions:
                assign_perm(p, group, self)

    def get_permissions(self, user):
        return list(set(get_perms(user, self)) & set(self.perms_list))


class ReviewProviderMixin(GuardianMixin):
    """A reviewed/moderated collection of objects.
    """

    REVIEWABLE_RELATION_NAME = None
    groups = REVIEW_GROUPS
    group_format = 'reviews_{self.readable_type}_{self.id}_{group}'

    class Meta:
        abstract = True

    reviews_workflow = models.CharField(null=True, blank=True, max_length=15, choices=Workflows.choices())
    reviews_comments_private = models.NullBooleanField()
    reviews_comments_anonymous = models.NullBooleanField()

    @property
    def is_reviewed(self):
        return self.reviews_workflow is not None

    def get_reviewable_state_counts(self):
        assert self.REVIEWABLE_RELATION_NAME, 'REVIEWABLE_RELATION_NAME must be set to compute state counts'
        qs = getattr(self, self.REVIEWABLE_RELATION_NAME)
        if isinstance(qs, IncludeQuerySet):
            qs = qs.include(None)
        qs = qs.filter(deleted__isnull=True, is_public=True).values('machine_state').annotate(count=models.Count('*'))
        counts = {state.value: 0 for state in ReviewStates}
        counts.update({row['machine_state']: row['count'] for row in qs if row['machine_state'] in counts})
        return counts

    def get_request_state_counts(self):
        # import stuff here to get around circular imports
        from osf.models import PreprintRequest
        qs = PreprintRequest.objects.filter(
            target__provider__id=self.id,
            target__is_public=True,
            target__deleted__isnull=True,
        )
        qs = qs.values('machine_state').annotate(count=models.Count('*'))
        counts = {state.value: 0 for state in DefaultStates}
        counts.update({row['machine_state']: row['count'] for row in qs if row['machine_state'] in counts})
        return counts

    def add_to_group(self, user, group):
        # Add default notification subscription
        notification = self.notification_subscriptions.get(_id='{}_new_pending_submissions'.format(self._id))
        user_id = user.id
        is_subscriber = notification.none.filter(id=user_id).exists() \
                        or notification.email_digest.filter(id=user_id).exists() \
                        or notification.email_transactional.filter(id=user_id).exists()
        if not is_subscriber:
            notification.add_user_to_subscription(user, 'email_transactional', save=True)
        return self.get_group(group).user_set.add(user)

    def remove_from_group(self, user, group, unsubscribe=True):
        _group = self.get_group(group)
        if group == ADMIN:
            if _group.user_set.filter(id=user.id).exists() and not _group.user_set.exclude(id=user.id).exists():
                raise ValueError('Cannot remove last admin.')
        if unsubscribe:
            # remove notification subscription
            notification = self.notification_subscriptions.get(_id='{}_new_pending_submissions'.format(self._id))
            notification.remove_user_from_subscription(user, save=True)

        return _group.user_set.remove(user)


class TaxonomizableMixin(models.Model):

    class Meta:
        abstract = True

    subjects = models.ManyToManyField(blank=True, to='osf.Subject', related_name='%(class)ss')

    @cached_property
    def subject_hierarchy(self):
        if self.subjects.exists():
            return [
                s.object_hierarchy for s in self.subjects.exclude(children__in=self.subjects.all()).select_related('parent')
            ]
        return []

    @property
    def subjects_relationship_url(self):
        return self.absolute_api_v2_url + 'relationships/subjects/'

    @property
    def subjects_url(self):
        return self.absolute_api_v2_url + 'subjects/'

    def check_subject_perms(self, auth):
        AbstractNode = apps.get_model('osf.AbstractNode')
        Preprint = apps.get_model('osf.Preprint')
        CollectionSubmission = apps.get_model('osf.CollectionSubmission')

        if isinstance(self, AbstractNode):
            if not self.has_permission(auth.user, ADMIN):
                raise PermissionsError('Only admins can change subjects.')
        elif isinstance(self, Preprint):
            if not self.has_permission(auth.user, WRITE):
                raise PermissionsError('Must have admin or write permissions to change a preprint\'s subjects.')
        elif isinstance(self, CollectionSubmission):
            if not self.guid.referent.has_permission(auth.user, ADMIN) and not auth.user.has_perms(self.collection.groups[ADMIN], self.collection):
                raise PermissionsError('Only admins can change subjects.')
        return

    def add_subjects_log(self, old_subjects, auth):
        self.add_log(
            action=NodeLog.SUBJECTS_UPDATED,
            params={
                'subjects': list(self.subjects.values('_id', 'text')),
                'old_subjects': list(Subject.objects.filter(id__in=old_subjects).values('_id', 'text'))
            },
            auth=auth,
            save=False,
        )
        return

    def assert_subject_format(self, subj_list, expect_list, error_msg):
        """ Helper for asserting subject request is formatted properly
        """
        is_list = type(subj_list) is list

        if (expect_list and not is_list) or (not expect_list and is_list):
            raise ValidationValueError('Subjects are improperly formatted. {}'.format(error_msg))

    def set_subjects(self, new_subjects, auth, add_log=True):
        """ Helper for setting M2M subjects field from list of hierarchies received from UI.
        Only authorized admins may set subjects.

        :param list[list[Subject._id]] new_subjects: List of subject hierarchies to be validated and flattened
        :param Auth auth: Auth object for requesting user
        :param bool add_log: Whether or not to add a log (if called on a Loggable object)

        :return: None
        """
        self.check_subject_perms(auth)
        self.assert_subject_format(new_subjects, expect_list=True, error_msg='Expecting list of lists.')

        old_subjects = list(self.subjects.values_list('id', flat=True))
        self.subjects.clear()
        for subj_list in new_subjects:
            self.assert_subject_format(subj_list, expect_list=True, error_msg='Expecting list of lists.')
            subj_hierarchy = []
            for s in subj_list:
                subj_hierarchy.append(s)
            if subj_hierarchy:
                validate_subject_hierarchy(subj_hierarchy)
                for s_id in subj_hierarchy:
                    self.subjects.add(Subject.load(s_id))

        if add_log and hasattr(self, 'add_log'):
            self.add_subjects_log(old_subjects, auth)

        self.save(old_subjects=old_subjects)

    def set_subjects_from_relationships(self, subjects_list, auth, add_log=True):
        """ Helper for setting M2M subjects field from list of flattened subjects received from UI.
        Only authorized admins may set subjects.

        :param list[Subject._id] new_subjects: List of flattened subject hierarchies
        :param Auth auth: Auth object for requesting user
        :param bool add_log: Whether or not to add a log (if called on a Loggable object)

        :return: None
        """
        self.check_subject_perms(auth)
        self.assert_subject_format(subjects_list, expect_list=True, error_msg='Expecting a list of subjects.')
        if subjects_list:
            self.assert_subject_format(subjects_list[0], expect_list=False, error_msg='Expecting a list of subjects.')

        old_subjects = list(self.subjects.values_list('id', flat=True))
        self.subjects.clear()
        for subj in expand_subject_hierarchy(subjects_list):
            self.subjects.add(subj)

        if add_log and hasattr(self, 'add_log'):
            self.add_subjects_log(old_subjects, auth)

        self.save(old_subjects=old_subjects)


class ContributorMixin(models.Model):
    """
    ContributorMixin containing methods for managing contributors.

    Works for both Nodes and Preprints. Preprints don't have hierarchies
    or OSF Groups, so there may be overrides for this.
    """
    class Meta:
        abstract = True

    DEFAULT_CONTRIBUTOR_PERMISSIONS = WRITE

    @property
    def log_class(self):
        # PreprintLog or NodeLog, for example
        raise NotImplementedError()

    @property
    def contributor_class(self):
        # PreprintContributor or Contributor, for example
        raise NotImplementedError()

    @property
    def contributor_kwargs(self):
        # Dictionary with object type as the key, self as the value
        raise NotImplementedError()

    @property
    def log_params(self):
        # Generic params to build log
        raise NotImplementedError()

    @property
    def order_by_contributor_field(self):
        # 'contributor___order', for example
        raise NotImplementedError()

    @property
    def contributor_email_template(self):
        # default contributor email template as a string
        raise NotImplementedError()

    def get_addons(self):
        raise NotImplementedError()

    def update_or_enqueue_on_resource_updated(self):
        raise NotImplementedError()

    @property
    def contributors(self):
        # NOTE: _order field is generated by order_with_respect_to = 'node'
        return self._contributors.order_by(self.order_by_contributor_field)

    @property
    def admin_contributor_or_group_member_ids(self):
        # Admin contributors or group members on parent, or current resource
        return self._get_admin_user_ids(include_self=True)

    def is_contributor_or_group_member(self, user):
        """
        Whether the user has explicit permissions to the resource -
        They must be a contributor or a member of an osf group with permissions
        Implicit admins not included.
        """
        return self.has_permission(user, READ, check_parent=False)

    def is_contributor(self, user):
        """
        Return whether ``user`` is a contributor on the resource.
        (Does not include whether user has permissions via a group.)
        """
        kwargs = self.contributor_kwargs
        kwargs['user'] = user
        return user is not None and self.contributor_class.objects.filter(**kwargs).exists()

    def is_admin_contributor(self, user):
        """
        Return whether ``user`` is a contributor on the resource and their contributor permissions are "admin".
        Doesn't factor in group member permissions.

        Important: having admin permissions through group membership but being a write contributor doesn't suffice.
        """
        if not user or user.is_anonymous:
            return False

        return self.has_permission(user, ADMIN) and self.get_group(ADMIN) in user.groups.all()

    def active_contributors(self, include=lambda n: True):
        """
        Returns active contributors, group members excluded
        """
        for contrib in self.contributors.filter(is_active=True):
            if include(contrib):
                yield contrib

    def get_admin_contributors(self, users):
        """Of the provided users, return the ones who are admin contributors on the node. Excludes contributors on node links and
        inactive users.
        """
        return (each.user for each in self._get_admin_contributors_query(users))

    def _get_admin_contributors_query(self, users):
        """
        Returns Contributor queryset whose objects have admin permissions to the node.
        Group permissions not included.
        """
        Preprint = apps.get_model('osf.Preprint')

        query_dict = {
            'user__in': users,
            'user__is_active': True,
            'user__groups': self.get_group(ADMIN).id
        }
        if isinstance(self, Preprint):
            query_dict['preprint'] = self
        else:
            query_dict['node'] = self

        return self.contributor_class.objects.select_related('user').filter(**query_dict)

    def add_contributor(self, contributor, permissions=None, visible=True,
                        send_email=None, auth=None, log=True, save=False):
        """Add a contributor to the project.

        :param User contributor: The contributor to be added
        :param list permissions: Permissions to grant to the contributor. Array of all permissions if node,
         highest permission to grant, if contributor, as a string.
        :param bool visible: Contributor is visible in project dashboard
        :param str send_email: Email preference for notifying added contributor
        :param Auth auth: All the auth information including user, API key
        :param bool log: Add log to self
        :param bool save: Save after adding contributor
        :returns: Whether contributor was added
        """
        send_email = send_email or self.contributor_email_template
        # If user is merged into another account, use master account
        contrib_to_add = contributor.merged_by if contributor.is_merged else contributor
        if contrib_to_add.is_disabled:
            raise ValidationValueError('Deactivated users cannot be added as contributors.')

        if not contrib_to_add.is_registered and not contrib_to_add.unclaimed_records:
            raise UserStateError('This contributor cannot be added. If the problem persists please report it '
                                       'to ' + language.SUPPORT_LINK)

        if self.is_contributor(contrib_to_add):
            if permissions is None:
                return False
            # Permissions must be overridden if changed when contributor is
            # added to parent he/she is already on a child of.
            else:
                self.set_permissions(contrib_to_add, permissions)
                if save:
                    self.save()
                return False
        else:
            kwargs = self.contributor_kwargs
            kwargs['user'] = contrib_to_add
            contributor_obj, created = self.contributor_class.objects.get_or_create(**kwargs)
            contributor_obj.visible = visible

            # Add default contributor permissions
            permissions = permissions or self.DEFAULT_CONTRIBUTOR_PERMISSIONS

            self.add_permission(contrib_to_add, permissions, save=True)
            contributor_obj.save()

            if log:
                params = self.log_params
                params['contributors'] = [contrib_to_add._id]
                self.add_log(
                    action=self.log_class.CONTRIB_ADDED,
                    params=params,
                    auth=auth,
                    save=False,
                )
            if save:
                self.save()

            if self._id and contrib_to_add:
                project_signals.contributor_added.send(self,
                                                       contributor=contributor,
                                                       auth=auth, email_template=send_email, permissions=permissions)

            # enqueue on_node_updated/on_preprint_updated to update DOI metadata when a contributor is added
            if self.get_identifier_value('doi'):
                request, user_id = get_request_and_user_id()
                self.update_or_enqueue_on_resource_updated(user_id, first_save=False, saved_fields=['contributors'])
            return contrib_to_add

    def add_contributors(self, contributors, auth=None, log=True, save=False):
        """Add multiple contributors

        :param list contributors: A list of dictionaries of the form:
            {
                'user': <User object>,
                'permissions': <String highest permission, 'admin', for example>
                'visible': <Boolean indicating whether or not user is a bibliographic contributor>
            }
        :param auth: All the auth information including user, API key.
        :param log: Add log to self
        :param save: Save after adding contributor
        """
        for contrib in contributors:
            self.add_contributor(
                contributor=contrib['user'], permissions=contrib['permissions'],
                visible=contrib['visible'], auth=auth, log=False, save=False,
            )
        if log and contributors:
            params = self.log_params
            params['contributors'] = [
                contrib['user']._id
                for contrib in contributors
            ]
            self.add_log(
                action=self.log_class.CONTRIB_ADDED,
                params=params,
                auth=auth,
                save=False,
            )
        if save:
            self.save()

    def add_unregistered_contributor(self, fullname, email, auth, send_email=None,
                                     visible=True, permissions=None, save=False, existing_user=None):
        """Add a non-registered contributor to the project.

        :param str fullname: The full name of the person.
        :param str email: The email address of the person.
        :param Auth auth: Auth object for the user adding the contributor.
        :param User existing_user: the unregister_contributor if it is already created, otherwise None
        :returns: The added contributor
        :raises: DuplicateEmailError if user with given email is already in the database.
        """
        OSFUser = apps.get_model('osf.OSFUser')
        send_email = send_email or self.contributor_email_template

        if email:
            try:
                validate_email(email)
            except BlacklistedEmailError:
                raise ValidationError('Unregistered contributor email address domain is blacklisted.')

        # Create a new user record if you weren't passed an existing user
        contributor = existing_user if existing_user else OSFUser.create_unregistered(fullname=fullname, email=email)

        contributor.add_unclaimed_record(self, referrer=auth.user,
                                         given_name=fullname, email=email)
        try:
            contributor.save()
        except ValidationError:  # User with same email already exists
            contributor = get_user(email=email)
            # Unregistered users may have multiple unclaimed records, so
            # only raise error if user is registered.
            if contributor.is_registered or self.is_contributor(contributor):
                raise

            contributor.add_unclaimed_record(
                self, referrer=auth.user, given_name=fullname, email=email
            )

            contributor.save()

        self.add_contributor(
            contributor, permissions=permissions, auth=auth,
            visible=visible, send_email=send_email, log=True, save=False
        )
        self.save()
        return contributor

    def add_contributor_registered_or_not(self, auth, user_id=None,
                                          full_name=None, email=None, send_email=None,
                                          permissions=None, bibliographic=True, index=None, save=False):
        OSFUser = apps.get_model('osf.OSFUser')
        send_email = send_email or self.contributor_email_template

        if user_id:
            contributor = OSFUser.load(user_id)
            if not contributor:
                raise ValueError('User with id {} was not found.'.format(user_id))

            if self.contributor_set.filter(user=contributor).exists():
                raise ValidationValueError('{} is already a contributor.'.format(contributor.fullname))

            if contributor.is_registered:
                contributor = self.add_contributor(contributor=contributor, auth=auth, visible=bibliographic,
                                     permissions=permissions, send_email=send_email, save=True)
            else:
                if not full_name:
                    raise ValueError(
                        'Cannot add unconfirmed user {} to resource {}. You need to provide a full_name.'
                        .format(user_id, self._id)
                    )
                contributor = self.add_unregistered_contributor(
                    fullname=full_name, email=contributor.username, auth=auth,
                    send_email=send_email, permissions=permissions,
                    visible=bibliographic, existing_user=contributor, save=True
                )

        else:
            contributor = get_user(email=email)
            if contributor and self.contributor_set.filter(user=contributor).exists():
                raise ValidationValueError('{} is already a contributor.'.format(contributor.fullname))

            if contributor and contributor.is_registered:
                self.add_contributor(contributor=contributor, auth=auth, visible=bibliographic,
                                    send_email=send_email, permissions=permissions, save=True)
            else:
                contributor = self.add_unregistered_contributor(
                    fullname=full_name, email=email, auth=auth,
                    send_email=send_email, permissions=permissions,
                    visible=bibliographic, save=True
                )

        auth.user.email_last_sent = timezone.now()
        auth.user.save()

        if index is not None:
            self.move_contributor(contributor=contributor, index=index, auth=auth, save=True)

        contributor_obj = self.contributor_set.get(user=contributor)
        return contributor_obj

    def replace_contributor(self, old, new):
        """
        Replacing unregistered contributor with a verified user
        """
        try:
            contrib_obj = self.contributor_set.get(user=old)
        except self.contributor_class.DoesNotExist:
            return False
        contrib_obj.user = new
        contrib_obj.save()

        # Remove unclaimed record for the project
        if self._id in old.unclaimed_records:
            del old.unclaimed_records[self._id]
            old.save()

        # For the read, write, and admin Django group attached to the node/preprint,
        # add the new user to the group, and remove the old.  This
        # will give the new user the appropriate permissions.
        for group_name in self.groups.keys():
            if self.belongs_to_permission_group(old, group_name):
                self.get_group(group_name).user_set.remove(old)
                self.get_group(group_name).user_set.add(new)
        return True

    # TODO: optimize me
    def update_contributor(self, user, permission, visible, auth, save=False):
        """ TODO: this method should be updated as a replacement for the main loop of
        Node#manage_contributors. Right now there are redundancies, but to avoid major
        feature creep this will not be included as this time.

        Also checks to make sure unique admin is not removing own admin privilege.
        """
        OSFUser = apps.get_model('osf.OSFUser')

        if not self.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can modify contributor permissions')

        if permission:
            admins = OSFUser.objects.filter(id__in=self._get_admin_contributors_query(self._contributors.all()).values_list('user_id', flat=True))
            if not admins.count() > 1:
                # has only one admin
                admin = admins.first()
                if (admin == user or getattr(admin, 'user', None) == user) and ADMIN != permission:
                    error_msg = '{} is the only admin.'.format(user.fullname)
                    raise self.state_error(error_msg)
            if not self.contributor_set.filter(user=user).exists():
                raise ValueError(
                    'User {0} not in contributors'.format(user.fullname)
                )
            if not self.get_group(permission).user_set.filter(id=user.id).exists():
                self.set_permissions(user, permission, save=False)
                permissions_changed = {
                    user._id: permission
                }
                params = self.log_params
                params['contributors'] = permissions_changed
                self.add_log(
                    action=self.log_class.PERMISSIONS_UPDATED,
                    params=params,
                    auth=auth,
                    save=False
                )
                with transaction.atomic():
                    if [READ] in permissions_changed.values():
                        project_signals.write_permissions_revoked.send(self)
        if visible is not None:
            self.set_visible(user, visible, auth=auth)

        if save:
            self.save()

    def remove_contributor(self, contributor, auth, log=True):
        """Remove a contributor from this node.

        :param contributor: User object, the contributor to be removed
        :param auth: All the auth information including user, API key.
        """
        if isinstance(contributor, self.contributor_class):
            contributor = contributor.user

        # remove unclaimed record if necessary
        if self._id in contributor.unclaimed_records:
            del contributor.unclaimed_records[self._id]
            contributor.save()

        # If user is the only visible contributor, return False
        if not self.contributor_set.exclude(user=contributor).filter(visible=True).exists():
            return False

        # Node must have at least one registered admin user
        admin_query = self._get_admin_contributors_query(self._contributors.all()).exclude(user=contributor)
        if not admin_query.exists():
            return False

        contrib_obj = self.contributor_set.get(user=contributor)
        contrib_obj.delete()

        self.clear_permissions(contributor)
        # After remove callback
        self.disconnect_addons(contributor, auth)

        if log:
            params = self.log_params
            params['contributors'] = [contributor._id]
            self.add_log(
                action=self.log_class.CONTRIB_REMOVED,
                params=params,
                auth=auth,
                save=False,
            )

        self.save()
        # send signal to remove this user from project subscriptions
        project_signals.contributor_removed.send(self, user=contributor)

        # enqueue on_node_updated/on_preprint_updated to update DOI metadata when a contributor is removed
        if self.get_identifier_value('doi'):
            request, user_id = get_request_and_user_id()
            self.update_or_enqueue_on_resource_updated(user_id, first_save=False, saved_fields=['contributors'])
        return True

    def remove_contributors(self, contributors, auth=None, log=True, save=False):

        results = []
        removed = []

        for contrib in contributors:
            outcome = self.remove_contributor(
                contributor=contrib, auth=auth, log=False,
            )
            results.append(outcome)
            removed.append(contrib._id)
        if log:
            params = self.log_params
            params['contributors'] = removed
            self.add_log(
                action=self.log_class.CONTRIB_REMOVED,
                params=params,
                auth=auth,
                save=False,
            )

        if save:
            self.save()

        return all(results)

    def move_contributor(self, contributor, auth, index, save=False):
        OSFUser = apps.get_model('osf.OSFUser')
        if not self.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can modify contributor order')
        if isinstance(contributor, OSFUser):
            contributor = self.contributor_set.get(user=contributor)
        contributor_ids = list(self.get_contributor_order())
        old_index = contributor_ids.index(contributor.id)
        contributor_ids.insert(index, contributor_ids.pop(old_index))
        self.set_contributor_order(contributor_ids)
        params = self.log_params
        params['contributors'] = contributor.user._id
        self.add_log(
            action=self.log_class.CONTRIB_REORDERED,
            params=params,
            auth=auth,
            save=False,
        )
        if save:
            self.save()
        # enqueue on_node_updated/on_preprint_updated to update DOI metadata when a contributor is moved
        if self.get_identifier_value('doi'):
            request, user_id = get_request_and_user_id()
            self.update_or_enqueue_on_resource_updated(user_id, first_save=False, saved_fields=['contributors'])

    # TODO: Optimize me
    def manage_contributors(self, user_dicts, auth, save=False):
        """Reorder and remove contributors.

        :param list user_dicts: Ordered list of contributors represented as
            dictionaries of the form:
            {'id': <id>, 'permission': <One of 'read', 'write', 'admin'>, 'visible': bool}
        :param Auth auth: Consolidated authentication information
        :param bool save: Save changes
        :raises: ValueError if any users in `users` not in contributors or if
            no admin contributors remaining
        """
        OSFUser = apps.get_model('osf.OSFUser')

        with transaction.atomic():
            users = []
            user_ids = []
            permissions_changed = {}
            visibility_removed = []
            to_retain = []
            to_remove = []
            for user_dict in user_dicts:
                user = OSFUser.load(user_dict['id'])
                if user is None:
                    raise ValueError('User not found')
                if not self.contributors.filter(id=user.id).exists():
                    raise ValueError(
                        'User {0} not in contributors'.format(user.fullname)
                    )

                permission = user_dict.get('permission', None) or user_dict.get('permissions', None)
                if not self.belongs_to_permission_group(user, permission):
                    # Validate later
                    self.set_permissions(user, permission, validate=False, save=False)
                    permissions_changed[user._id] = permission

                # visible must be added before removed to ensure they are validated properly
                if user_dict['visible']:
                    self.set_visible(user,
                                     visible=True,
                                     auth=auth)
                else:
                    visibility_removed.append(user)
                users.append(user)
                user_ids.append(user_dict['id'])

            for user in visibility_removed:
                self.set_visible(user,
                                 visible=False,
                                 auth=auth)

            for user in self.contributors.all():
                if user._id in user_ids:
                    to_retain.append(user)
                else:
                    to_remove.append(user)

            if users is None or not self._get_admin_contributors_query(users).exists():
                error_message = 'Must have at least one registered admin contributor'
                raise self.state_error(error_message)

            if to_retain != users:
                # Ordered Contributor PKs, sorted according to the passed list of user IDs
                sorted_contrib_ids = [
                    each.id for each in sorted(self.contributor_set.all(), key=lambda c: user_ids.index(c.user._id))
                ]
                self.set_contributor_order(sorted_contrib_ids)
                params = self.log_params
                params['contributors'] = [
                    user._id
                    for user in users
                ]
                self.add_log(
                    action=self.log_class.CONTRIB_REORDERED,
                    params=params,
                    auth=auth,
                    save=False,
                )

            if to_remove:
                self.remove_contributors(to_remove, auth=auth, save=False)

            if permissions_changed:
                params = self.log_params
                params['contributors'] = permissions_changed
                self.add_log(
                    action=self.log_class.PERMISSIONS_UPDATED,
                    params=params,
                    auth=auth,
                    save=False,
                )
            if save:
                self.save()

            with transaction.atomic():
                if to_remove or permissions_changed and [READ] in permissions_changed.values():
                    project_signals.write_permissions_revoked.send(self)

    @property
    def visible_contributors(self):
        OSFUser = apps.get_model('osf.OSFUser')
        return OSFUser.objects.filter(
            contributor__node=self,
            contributor__visible=True
        ).order_by('contributor___order')

    # visible_contributor_ids was moved to this property
    @property
    def visible_contributor_ids(self):
        return self.contributor_set.filter(visible=True) \
            .order_by('_order') \
            .values_list('user__guids___id', flat=True)

    def get_visible(self, user):
        try:
            contributor = self.contributor_set.get(user=user)
        except self.contributor_class.DoesNotExist:
            raise ValueError(u'User {0} not in contributors'.format(user))
        return contributor.visible

    def set_visible(self, user, visible, log=True, auth=None, save=False):
        if not self.is_contributor(user):
            raise ValueError(u'User {0} not in contributors'.format(user))
        kwargs = self.contributor_kwargs
        kwargs['user'] = user
        kwargs['visible'] = True
        if visible and not self.contributor_class.objects.filter(**kwargs).exists():
            set_visible_kwargs = kwargs
            set_visible_kwargs['visible'] = False
            self.contributor_class.objects.filter(**set_visible_kwargs).update(visible=True)
        elif not visible and self.contributor_class.objects.filter(**kwargs).exists():
            num_visible_kwargs = self.contributor_kwargs
            num_visible_kwargs['visible'] = True
            if self.contributor_class.objects.filter(**num_visible_kwargs).count() == 1:
                raise ValueError('Must have at least one visible contributor')
            self.contributor_class.objects.filter(**kwargs).update(visible=False)
        else:
            return
        message = (
            self.log_class.MADE_CONTRIBUTOR_VISIBLE if visible else self.log_class.MADE_CONTRIBUTOR_INVISIBLE
        )
        params = self.log_params
        params['contributors'] = [user._id]
        if log:
            self.add_log(
                message,
                params=params,
                auth=auth,
                save=False,
            )
        if save:
            self.save()
        # enqueue on_node_updated/on_preprint_updated to update DOI metadata when a contributor is hidden/made visible
        if self.get_identifier_value('doi'):
            request, user_id = get_request_and_user_id()
            self.update_or_enqueue_on_resource_updated(user_id, first_save=False, saved_fields=['contributors'])

    def has_permission(self, user, permission, check_parent=True):
        """Check whether user has permission, through contributorship or group membership
        :param User user: User to test
        :param str permission: Required permission
        :returns: User has required permission
        """
        Preprint = apps.get_model('osf.Preprint')
        object_type = 'preprint' if isinstance(self, Preprint) else 'node'

        if not user or user.is_anonymous:
            return False
        perm = '{}_{}'.format(permission, object_type)
        # Using get_group_perms to get permissions that are inferred through
        # group membership - not inherited from superuser status
        has_permission = perm in get_group_perms(user, self)
        if object_type == 'node':
            if not has_permission and permission == READ and check_parent:
                return self.is_admin_parent(user)
        return has_permission

    # TODO: Remove save parameter
    def add_permission(self, user, permission, save=False):
        """Grant permission to a user.

        :param User user: User to grant permission to
        :param str permission: Permission to grant
        :param bool save: Save changes
        :raises: ValueError if user already has permission
        """
        if not self.belongs_to_permission_group(user, permission):
            permission_group = self.get_group(permission)
            permission_group.user_set.add(user)
        else:
            raise ValueError('User already has permission {0}'.format(permission))
        if save:
            self.save()

    def set_permissions(self, user, permissions, validate=True, save=False):
        """Set a user's permissions to a node.

        :param User user: User to grant permission to
        :param str permissions: Highest permission to grant, i.e. 'write'
        :param bool validate: Validate admin contrib constraint
        :param bool save: Save changes
        :raises: StateError if contrib constraint is violated
        """
        # Ensure that user's permissions cannot be lowered if they are the only admin (
        # - admin contributor, not admin group member)
        if isinstance(user, self.contributor_class):
            user = user.user

        if validate and (self.is_admin_contributor(user) and permissions != ADMIN):
            if self.get_group(ADMIN).user_set.filter(is_registered=True).count() <= 1:
                raise self.state_error('Must have at least one registered admin contributor')
        self.clear_permissions(user)
        self.add_permission(user, permissions)
        if save:
            self.save()

    def clear_permissions(self, user):
        for name in self.groups.keys():
            if user.groups.filter(name=self.get_group(name)).exists():
                self.remove_permission(user, name)

    def belongs_to_permission_group(self, user, permission):
        return self.get_group(permission).user_set.filter(id=user.id).exists()

    def remove_permission(self, user, permission, save=False):
        """Revoke permission from a user.

        :param User user: User to revoke permission from
        :param str permission: Permission to revoke
        :param bool save: Save changes
        :raises: ValueError if user does not have permission
        """
        if self.belongs_to_permission_group(user, permission):
            permission_group = self.get_group(permission)
            permission_group.user_set.remove(user)
        else:
            raise ValueError('User does not have permission {0}'.format(permission))
        if save:
            self.save()

    def disconnect_addons(self, user, auth):
        """
        Loop through all the node's addons and remove user's authentication.
        Used when removing users from nodes (either removing a contributor, removing an OSF Group,
        removing an OSF Group from a node, or removing a member from an OSF group)
        """
        if not self.is_contributor_or_group_member(user):
            for addon in self.get_addons():
                # After remove callback
                message = addon.after_remove_contributor(self, user, auth)
                if message:
                    # Because addons can return HTML strings, addons are responsible
                    # for markupsafe-escaping any messages returned
                    status.push_status_message(message, kind='info', trust=True, id='remove_addon', extra={
                        'addon': markupsafe.escape(addon.config.full_name),
                        'category': markupsafe.escape(self.category_display),
                        'title': markupsafe.escape(self.title),
                        'user': markupsafe.escape(user.fullname)
                    })


class SpamOverrideMixin(SpamMixin):
    """
    Contains overrides to SpamMixin that are common to the node and preprint models
    """
    class Meta:
        abstract = True

    # Override on model
    SPAM_CHECK_FIELDS = {}

    @property
    def log_class(self):
        return NotImplementedError()

    @property
    def log_params(self):
        return NotImplementedError()

    def get_spam_fields(self):
        return NotImplementedError()

    def confirm_spam(self, save=False):
        super(SpamOverrideMixin, self).confirm_spam(save=False)
        self.set_privacy('private', auth=None, log=False, save=False)
        log = self.add_log(
            action=self.log_class.MADE_PRIVATE,
            params=self.log_params,
            auth=None,
            save=False
        )
        log.should_hide = True
        log.save()
        if save:
            self.save()

    def _get_spam_content(self, saved_fields):
        """
        This function retrieves retrieves strings of potential spam from various DB fields. Also here we can follow
        django's typical ORM query structure for example we can grab the redirect link of a node by giving a saved
        field of {'addons_forward_node_settings__url'}.

        :param saved_fields: set
        :return: str
        """
        spam_fields = self.get_spam_fields(saved_fields)
        content = []
        for field in spam_fields:
            exclude_null = {field + '__isnull': False}
            values = list(self.__class__.objects.filter(id=self.id, **exclude_null).values_list(field, flat=True))
            if values:
                content.append((' '.join(values) or '').encode('utf-8'))
        if self.all_tags.exists():
            content.extend([name.encode('utf-8') for name in self.all_tags.values_list('name', flat=True)])
        if not content:
            return None
        return ' '.join(content)

    def check_spam(self, user, saved_fields, request_headers):
        if not settings.SPAM_CHECK_ENABLED:
            return False
        if settings.SPAM_CHECK_PUBLIC_ONLY and not self.is_public:
            return False
        if user.spam_status == SpamStatus.HAM:
            return False

        content = self._get_spam_content(saved_fields)
        if not content:
            return
        is_spam = self.do_check_spam(
            user.fullname,
            user.username,
            content,
            request_headers
        )
        logger.info("{} ({}) '{}' smells like {} (tip: {})".format(
            self.__class__.__name__, self._id, self.title.encode('utf-8'), 'SPAM' if is_spam else 'HAM', self.spam_pro_tip
        ))
        if is_spam:
            self._check_spam_user(user)
        return is_spam

    def _check_spam_user(self, user):
        if (
            settings.SPAM_ACCOUNT_SUSPENSION_ENABLED
            and (timezone.now() - user.date_confirmed) <= settings.SPAM_ACCOUNT_SUSPENSION_THRESHOLD
        ):
            self.set_privacy('private', log=False, save=False)

            # Suspend the flagged user for spam.
            user.flag_spam()
            if not user.is_disabled:
                user.disable_account()
                user.is_registered = False
                mails.send_mail(
                    to_addr=user.username,
                    mail=mails.SPAM_USER_BANNED,
                    user=user,
                    osf_support_email=settings.OSF_SUPPORT_EMAIL,
                    can_change_preferences=False,
                )
            user.save()

            # Make public nodes private from this contributor
            for node in user.all_nodes:
                if self._id != node._id and len(node.contributors) == 1 and node.is_public and not node.is_quickfiles:
                    node.set_privacy('private', log=False, save=True)

            # Make preprints private from this contributor
            for preprint in user.preprints.all():
                if self._id != preprint._id and len(preprint.contributors) == 1 and preprint.is_public:
                    preprint.set_privacy('private', log=False, save=True)

    def flag_spam(self):
        """ Overrides SpamMixin#flag_spam.
        """
        super(SpamOverrideMixin, self).flag_spam()
        if settings.SPAM_FLAGGED_MAKE_NODE_PRIVATE:
            self.set_privacy('private', auth=None, log=False, save=False, check_addons=False)
            log = self.add_log(
                action=self.log_class.MADE_PRIVATE,
                params=self.log_params,
                auth=None,
                save=False
            )
            log.should_hide = True
            log.save()
