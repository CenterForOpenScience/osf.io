import pytz

from django.apps import apps
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.db import models, transaction
from guardian.shortcuts import assign_perm
from guardian.shortcuts import get_perms
from guardian.shortcuts import remove_perm
from include import IncludeQuerySet

from api.preprint_providers.workflows import Workflows, PUBLIC_STATES
from framework.analytics import increment_user_activity_counters
from osf.exceptions import InvalidTriggerError
from osf.models.node_relation import NodeRelation
from osf.models.nodelog import NodeLog
from osf.models.tag import Tag
from osf.utils.fields import NonNaiveDateTimeField
from osf.utils.machines import ReviewsMachine, RequestMachine
from osf.utils.workflows import DefaultStates, DefaultTriggers
from website.exceptions import NodeStateError
from website import settings


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

        if self.logs.count() == 1:
            self.last_logged = log.date.replace(tzinfo=pytz.utc)
        else:
            self.last_logged = self.logs.first().date

        if save:
            self.save()
        if user and not self.is_collection:
            increment_user_activity_counters(user._primary_key, action, log.date.isoformat())

        return log

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
        config.label != 'base'])

    class Meta:
        abstract = True

    @classmethod
    def get_addon_key(cls, config):
        return 2 << cls.ADDONS_AVAILABLE.index(config)

    @property
    def addons(self):
        return self.get_addons()

    def get_addons(self):
        return filter(None, [
            self.get_addon(config.short_name)
            for config in self.ADDONS_AVAILABLE
        ])

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
        ret.save()  # TODO This doesn't feel right
        return ret

    def config_addons(self, config, auth=None, save=True):
        """Enable or disable a set of add-ons.

        :param dict config: Mapping between add-on names and enabled / disabled
            statuses
        """
        for addon_name, enabled in config.iteritems():
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
        # Fail if node already in nodes / pointers. Note: cast node and node
        # to primary keys to test for conflicts with both nodes and pointers
        # contained in `self.nodes`.
        if NodeRelation.objects.filter(parent=self, child=node, is_node_link=True).exists():
            raise ValueError(
                'Link to node {0} already exists'.format(node._id)
            )

        if self.is_registration:
            raise NodeStateError('Cannot add a node link to a registration')

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
        E.g. For a NodeWikiPage, the page name is 'wiki'."""
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
        return self.__run_transition(DefaultTriggers.SUBMIT.value, user=user)

    def run_accept(self, user, comment):
        """Run the 'accept' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
            comment: Text describing why.
        """
        return self.__run_transition(DefaultTriggers.ACCEPT.value, user=user, comment=comment)

    def run_reject(self, user, comment):
        """Run the 'reject' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
            comment: Text describing why.
        """
        return self.__run_transition(DefaultTriggers.REJECT.value, user=user, comment=comment)

    def run_edit_comment(self, user, comment):
        """Run the 'edit_comment' state transition and create a corresponding Action.

        Params:
            user: The user triggering this transition.
            comment: New comment text.
        """
        return self.__run_transition(DefaultTriggers.EDIT_COMMENT.value, user=user, comment=comment)

    def __run_transition(self, trigger, **kwargs):
        machine = self.MachineClass(self, 'machine_state')
        trigger_fn = getattr(machine, trigger)
        with transaction.atomic():
            result = trigger_fn(**kwargs)
            action = machine.action
            if not result or action is None:
                valid_triggers = machine.get_triggers(self.machine_state)
                raise InvalidTriggerError(trigger, self.machine_state, valid_triggers)
            return action

class RequestableMixin(MachineableMixin):
    """Something that users may request access or changes to.
    """

    class Meta:
        abstract = True

    MachineClass = RequestMachine


class ReviewableMixin(MachineableMixin):
    """Something that may be included in a reviewed collection and is subject to a reviews workflow.
    """

    class Meta:
        abstract = True

    MachineClass = ReviewsMachine

    @property
    def in_public_reviews_state(self):
        public_states = PUBLIC_STATES.get(self.provider.reviews_workflow)
        if not public_states:
            return False
        return self.machine_state in public_states


class ReviewProviderMixin(models.Model):
    """A reviewed/moderated collection of objects.
    """

    REVIEWABLE_RELATION_NAME = None

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
        qs = qs.filter(node__isnull=False, node__is_deleted=False, node__is_public=True).values('machine_state').annotate(count=models.Count('*'))
        counts = {state.value: 0 for state in DefaultStates}
        counts.update({row['machine_state']: row['count'] for row in qs if row['machine_state'] in counts})
        return counts

    def add_to_group(self, user, group):
        from api.preprint_providers.permissions import GroupHelper
        # TODO: Add default notification subscription
        return GroupHelper(self).get_group(group).user_set.add(user)

    def remove_from_group(self, user, group, unsubscribe=True):
        from api.preprint_providers.permissions import GroupHelper
        _group = GroupHelper(self).get_group(group)
        if group == 'admin':
            if _group.user_set.filter(id=user.id).exists() and not _group.user_set.exclude(id=user.id).exists():
                raise ValueError('Cannot remove last admin.')
        if unsubscribe:
            # TODO: remove notification subscription
            pass
        return _group.user_set.remove(user)


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
        return [self.format_group(name) for name in self.groups_dict]

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
