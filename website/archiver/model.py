from copy import deepcopy
import datetime

from modularodm import (
    fields,
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

    # Dictonary mapping addon short name to archive status
    # {
    #   [addon_short_name]: {
    #     'status': [STATUS_CONSTANT],
    #     'errrors': []
    #   }
    # }
    target_addons = fields.DictionaryField(default={})

    @property
    def children(self):
        return [node.archive_job for node in self.dst_node.nodes]

    @property
    def parent(self):
        parent_node = self.dst_node.parent_node
        return parent_node.archive_job if parent_node else None

    @property
    def success(self):
        return self.status == ARCHIVER_SUCCESS

    def info(self):
        return self.src_node, self.dst_node, self.initiator

    def _archive_node_finished(self):
        return not any([
            value for value in self.target_addons.values()
            if value['status'] not in (ARCHIVER_SUCCESS, ARCHIVER_FAILURE)
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

    def _post_update_target(self):
        if self._archive_node_finished():
            self.done = True
        if self.archive_tree_finished():
            if not ARCHIVER_FAILURE_STATUSES.isdisjoint(
                    [value['status'] for value in self.target_addons.values()]
            ):
                self.status = ARCHIVER_FAILURE
            else:
                self.status = ARCHIVER_SUCCESS
        self.save()

    def set_targets(self):
        self.status = ARCHIVER_INITIATED
        addons = [
            addon.config.short_name for addon in
            [self.dst_node.get_addon(name) for name in settings.ADDONS_ARCHIVABLE]
            if (addon and addon.complete and isinstance(addon, StorageAddonBase))
        ]
        for addon in addons:
            self.target_addons[addon] = {
                'status': ARCHIVER_INITIATED,
            }
        self.save()

    def update_target(self, addon_short_name, status, meta={}):
        copy = deepcopy(self.target_addons[addon_short_name])
        copy['status'] = status
        copy.update(meta)
        self.target_addons.update({
            addon_short_name: copy
        })
        self.save()
        self._post_update_target()
