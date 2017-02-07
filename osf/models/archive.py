from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from django.db import models
from website import settings
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField

from addons.base.models import BaseStorageAddon
from website.archiver import (
    ARCHIVER_INITIATED,
    ARCHIVER_SUCCESS,
    ARCHIVER_FAILURE,
    ARCHIVER_FAILURE_STATUSES
)


class ArchiveTarget(ObjectIDMixin, BaseModel):
    """Stores the results of archiving a single addon
    """

    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.archiver.model.ArchiveTarget'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION

    # addon_short_name of target addon
    name = models.CharField(max_length=2048)

    status = models.CharField(max_length=40, default=ARCHIVER_INITIATED)
    # <dict> representation of a website.archiver.AggregateStatResult
    # Format: {
    #     'target_id': <str>,
    #     'target_name': <str>,
    #     'targets': <list>(StatResult | AggregateStatResult),
    #     'num_files': <int>,
    #     'disk_usage': <float>,
    # }
    stat_result = DateTimeAwareJSONField(default=dict, blank=True)
    errors = ArrayField(models.TextField(), default=list, blank=True)

    def __repr__(self):
        return '<{0}(_id={1}, name={2}, status={3})>'.format(
            self.__class__.__name__,
            self._id,
            self.name,
            self.status
        )


class ArchiveJob(ObjectIDMixin, BaseModel):

    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.archiver.model.ArchiveJob'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION

    # whether or not the ArchiveJob is complete (success or fail)
    done = models.BooleanField(default=False, verbose_name='completed')
    # whether or not emails have been sent for this ArchiveJob
    sent = models.BooleanField(default=False, verbose_name='emails sent')
    status = models.CharField(max_length=40, default=ARCHIVER_INITIATED)
    datetime_initiated = models.DateTimeField(default=timezone.now, verbose_name='initiated at')

    dst_node = models.ForeignKey('Registration', related_name='archive_jobs',
                                 verbose_name='destination node', null=True, blank=True)
    src_node = models.ForeignKey('Node', verbose_name='source node', null=True, blank=True)
    initiator = models.ForeignKey('OSFUser', null=True)

    target_addons = models.ManyToManyField('ArchiveTarget')

    def __repr__(self):
        return (
            '<{ClassName}(_id={self._id}, done={self.done}, '
            ' status={self.status}, src_node={self.src_node}, dst_node={self.dst_node})>'
        ).format(ClassName=self.__class__.__name__, self=self)

    @property
    def children(self):
        return [node.archive_job for node in self.dst_node.nodes_primary]

    @property
    def parent(self):
        parent_node = self.dst_node.parent_node
        return parent_node.archive_job if parent_node else None

    @property
    def success(self):
        return self.status == ARCHIVER_SUCCESS

    @property
    def pending(self):
        return any([
            target for target in self.target_addons.all()
            if target.status not in (ARCHIVER_SUCCESS, ARCHIVER_FAILURE)
        ])

    def info(self):
        return self.src_node, self.dst_node, self.initiator

    def target_info(self):
        return [
            {
                'name': target.name,
                'status': target.status,
                'stat_result': target.stat_result,
                'errors': target.errors
            }
            for target in self.target_addons.all()
        ]

    def archive_tree_finished(self):
        if not self.pending:
            return len(
                [
                    ret for ret in [
                        child.archive_tree_finished()
                        for child in self.children
                    ] if ret]
            ) if len(self.children) else True
        return False

    def _fail_above(self):
        """Marks all ArchiveJob instances attached to Nodes above this as failed
        """
        parent = self.parent
        if parent:
            parent.status = ARCHIVER_FAILURE
            parent.save()

    def _post_update_target(self):
        """Checks for success or failure if the ArchiveJob on self.dst_node
        is finished
        """
        if self.status == ARCHIVER_FAILURE:
            return
        if not self.pending:
            self.done = True
            if self.target_addons.filter(status__in=ARCHIVER_FAILURE_STATUSES).exists():
                self.status = ARCHIVER_FAILURE
                self._fail_above()
            else:
                self.status = ARCHIVER_SUCCESS
            self.save()

    def get_target(self, addon_short_name):
        return self.target_addons.filter(name=addon_short_name).first()

    def _set_target(self, addon_short_name):
        if self.get_target(addon_short_name):
            return
        target = ArchiveTarget(name=addon_short_name)
        target.save()
        self.target_addons.add(target)

    def set_targets(self):
        addons = []
        for addon in [self.src_node.get_addon(name)
                      for name in settings.ADDONS_ARCHIVABLE
                      if settings.ADDONS_ARCHIVABLE[name] != 'none']:
            if not addon or not isinstance(addon, BaseStorageAddon) or not addon.complete:
                continue
            archive_errors = getattr(addon, 'archive_errors', None)
            if not archive_errors or (archive_errors and not archive_errors()):
                if addon.config.short_name == 'dataverse':
                    addons.append(addon.config.short_name + '-draft')
                    addons.append(addon.config.short_name + '-published')
                else:
                    addons.append(addon.config.short_name)
        for addon in addons:
            self._set_target(addon)
        self.save()

    def update_target(self, addon_short_name, status, stat_result=None, errors=None):
        stat_result = stat_result or {}
        errors = errors or []

        target = self.get_target(addon_short_name)
        target.status = status
        target.errors = errors
        target.stat_result = stat_result
        target.save()
        self._post_update_target()
