import pytz
from django.db import models

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
        from osf_models.models import NodeLog
        user = None
        if auth:
            user = auth.user
        elif request:
            user = request.user

        params['node'] = params.get('node') or params.get('project') or self._id
        log = NodeLog(
            action=action, user=user, foreign_user=foreign_user,
            params=params, node=self, original_node=params.get('node')
        )

        if log_date:
            log.date = log_date
        log.save()

        if len(self.logs) == 1:
            self.date_modified = log.date.replace(tzinfo=pytz.utc)
        else:
            self.date_modified = self.logs[-1].date.replace(tzinfo=pytz.utc)

        if save:
            self.save()
        if user:
            increment_user_activity_counters(user._primary_key, action, log.date.isoformat())

        return log

    class Meta:
        abstract = True


