import pytz
from django.db import models
from django.apps import apps

from osf_models.models.tag import Tag
from osf_models.models.nodelog import NodeLog

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
