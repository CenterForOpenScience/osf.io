import datetime

from modularodm import (
    fields,
    Q,
)

from framework.mongo import ObjectId
from framework.mongo import StoredObject

from website.archiver import (
    ARCHIVER_INITIATED,
    ARCHIVER_SUCCESS,
    ARCHIVER_FAILURE,
    ARCHIVER_FAILURE_STATUSES
)

from website.addons.base import StorageAddonBase
from website import settings

class ArchiveTarget(StoredObject):

    _id = fields.StringField(
        primary=True,
        default=lambda: str(ObjectId())
    )

    name = fields.StringField()

    status = fields.StringField(default=ARCHIVER_INITIATED)
    stat_result = fields.DictionaryField()
    errors = fields.StringField(list=True)

    def __repr__(self):
        return "{0}: {1}".format(self.name, self.status)

class ArchiveJob(StoredObject):

    _id = fields.StringField(
        primary=True,
        default=lambda: str(ObjectId())
    )

    done = fields.BooleanField(default=False)
    sent = fields.BooleanField(default=False)
    status = fields.StringField()
    datetime_initiated = fields.DateTimeField(default=datetime.datetime.utcnow)

    dst_node = fields.ForeignField('node', backref='active')
    src_node = fields.ForeignField('node')
    initiator = fields.ForeignField('user')

    target_addons = fields.ForeignField('archivetarget', list=True)

    # This field is used for stashing embargo URLs while still in the app context
    meta = fields.DictionaryField()

    @property
    def children(self):
        return [node.archive_job for node in self.dst_node.nodes if node.primary]

    @property
    def parent(self):
        parent_node = self.dst_node.parent_node
        return parent_node.archive_job if parent_node else None

    @property
    def success(self):
        return self.status == ARCHIVER_SUCCESS

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
            for target in self.target_addons
        ]

    def _archive_node_finished(self):
        return not any([
            target for target in self.target_addons
            if target.status not in (ARCHIVER_SUCCESS, ARCHIVER_FAILURE)
        ])

    def archive_tree_finished(self):
        if self._archive_node_finished():
            return len(
                [
                    ret for ret in [
                        child.archive_tree_finished()
                        for child in self.children
                    ] if ret]
            ) if len(self.children) else True
        return False

    def _fail_above(self):
        parent = self.parent
        if parent:
            parent.status = ARCHIVER_FAILURE
            parent.save()

    def _post_update_target(self):
        if self._archive_node_finished():
            self.done = True
        if self.archive_tree_finished():
            if not ARCHIVER_FAILURE_STATUSES.isdisjoint(
                [target.status for target in self.target_addons]
            ):
                self.status = ARCHIVER_FAILURE
                self._fail_above()
            else:
                self.status = ARCHIVER_SUCCESS
        self.save()

    def get_target(self, addon_short_name):
        try:
            return self.target_addons.find(Q('name', 'eq', addon_short_name))[0]
        except IndexError:
            return None

    def _set_target(self, addon_short_name):
        if self.get_target(addon_short_name):
            return
        target = ArchiveTarget(name=addon_short_name)
        target.save()
        self.target_addons.append(target)

    def set_targets(self):
        self.status = ARCHIVER_INITIATED
        addons = [
            addon.config.short_name for addon in
            [self.src_node.get_addon(name) for name in settings.ADDONS_ARCHIVABLE]
            if (addon and addon.complete and isinstance(addon, StorageAddonBase))
        ]
        for addon in addons:
            self._set_target(addon)
        self.save()

    def update_target(self, addon_short_name, status, stat_result=None, errors=None):
        stat_result = stat_result._to_dict() if stat_result else {}
        errors = errors or []

        target = self.get_target(addon_short_name)
        target.status = status
        target.errors = errors
        target.stat_result = stat_result
        target.save()
        self._post_update_target()
