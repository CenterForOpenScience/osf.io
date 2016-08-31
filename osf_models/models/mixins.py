import pytz
from django.db import models
from django.apps import apps

from osf_models.models.tag import Tag
from osf_models.models.nodelog import NodeLog
from website.exceptions import NodeStateError

from framework.analytics import increment_user_activity_counters


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
    # TODO: This should be in the NodeLog model

    def add_log(self, action, params, auth, foreign_user=None, log_date=None, save=True, request=None):
        AbstractNode = apps.get_model('osf_models.AbstractNode')
        user = None
        if auth:
            user = auth.user
        elif request:
            user = request.user

        params['node'] = params.get('node') or params.get('project') or self._id
        original_node = AbstractNode.load(params.get('node'))
        log = NodeLog(
            action=action, user=user, foreign_user=foreign_user,
            params=params, node=self, original_node=original_node
        )

        if log_date:
            log.date = log_date
        log.save()

        if self.logs.count() == 1:
            self.date_modified = log.date.replace(tzinfo=pytz.utc)
        else:
            self.date_modified = self.logs.first().date

        if save:
            self.save()
        if user:
            increment_user_activity_counters(user._primary_key, action, log.date.isoformat())

        return log

    class Meta:
        abstract = True

class Taggable(models.Model):

    tags = models.ManyToManyField('Tag', related_name='tagged')

    def add_tag(self, tag, auth=None, save=True, log=True, system=False):
        if not system and not auth:
            raise ValueError('Must provide auth if adding a non-system tag')

        if not isinstance(tag, Tag):
            tag_instance, created = Tag.objects.get_or_create(name=tag, system=system)
        else:
            tag_instance = tag

        if not self.tags.filter(id=tag_instance.id).exists():
            self.tags.add(tag_instance)
            if log:
                self.add_tag_log(tag_instance, auth)
            if save:
                self.save()
        return tag_instance

    def add_system_tag(self, tag, save=True):
        return self.add_tag(tag=tag, auth=None, save=save, log=False, system=True)

    def add_tag_log(self, *args, **kwargs):
        raise NotImplementedError('Logging requires that add_tag_log method is implemented')

    class Meta:
        abstract = True


# TODO: Implement me
class AddonModelMixin(models.Model):

    def get_addons(self):
        return []

    def get_or_add_addon(self, *args, **kwargs):
        return None

    def get_addon(self, *args, **kwargs):
        return None

    class Meta:
        abstract = True


class NodeLinkMixin(models.Model):
    linked_nodes = models.ManyToManyField('AbstractNode')

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
        if self.linked_nodes.filter(id=node.id).exists():
            raise ValueError(
                'Link to node {0} already exists'.format(node._id)
            )

        if self.is_registration:
            raise NodeStateError('Cannot add a pointer to a registration')

        # If a folder, prevent more than one pointer to that folder.
        # This will prevent infinite loops on the project organizer.
        if node.is_collection and node.linked_from.exists():
            raise ValueError(
                'Node link to folder {0} already exists. '
                'Only one node link to any given folder allowed'.format(node._id)
            )
        if node.is_collection and node.is_bookmark_collection:
            raise ValueError(
                'Node link to bookmark collection ({0}) not allowed.'.format(node._id)
            )

        # Append node link
        self.linked_nodes.add(node)

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

        return node

    add_pointer = add_node_link  # For v1 compat

    def rm_node_link(self, node, auth):
        """Remove a pointer.

        :param Pointer pointer: Pointer to remove
        :param Auth auth: Consolidated authorization
        """
        if not self.linked_nodes.filter(id=node.id).exists():
            raise ValueError('Node link does not belong to the requested node.')

        self.linked_nodes.remove(node)

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
    def linked_from(self):
        """Return the nodes that have linked to this node."""
        Node = apps.get_model('osf_models.Node')
        return Node.objects.filter(linked_nodes=self)

    @property
    def linked_from_collections(self):
        """Return the nodes that have linked to this node."""
        Collection = apps.get_model('osf_models.Collection')
        return Collection.objects.filter(linked_nodes=self)

    @property
    def nodes_pointer(self):
        """For v1 compat"""
        return self.linked_nodes

    def get_points(self, folders=False, deleted=False):
        if deleted:
            query = self.linked_from.all()
        else:
            query = self.linked_from.filter(is_deleted=False).all()
        ret = list(query)
        if folders:
            if deleted:
                collection_query = self.linked_from_collections.all()
            else:
                collection_query = self.linked_from_collections.filter(is_deleted=False).all()
            ret.extend(list(collection_query))
        return ret

    def fork_node_link(self, node, auth, save=True):
        """Replace a linked node with a fork.

        :param Node node:
        :param Auth auth:
        :param bool save:
        :return: Forked node
        """
        # Fail if pointer not contained in `nodes`
        if not self.linked_nodes.filter(id=node.id).exists():
            raise ValueError('Node link {0} not in list'.format(node._id))

        # Fork into current node and replace pointer with forked component
        forked = node.fork_node(auth)
        if forked is None:
            raise ValueError('Could not fork node')

        self.nodes.add(forked)

        if hasattr(self, 'add_log'):
            # Add log
            self.add_log(
                NodeLog.NODE_LINK_FORKED,
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

        # Optionally save changes
        if save:
            self.save()

        # Return forked content
        return forked

    fork_pointer = fork_node_link  # For v1 compat
