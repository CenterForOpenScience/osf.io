from copy import deepcopy

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

class ArchiveLog(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))

    done = fields.BooleanField(default=False)
    status = fields.StringField()
    datetime_initiated = fields.DateTimeField(auto_add_now=True)

    src_node = fields.ForeignField('node', backref='archived_from')
    dst_node = fields.ForeignField('node', backref='archived_to')
    initator = fields.ForeignField('user', backref='archive_initiator')

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
        return [node.archive_log for node in self.dst_node.nodes]

    @property
    def parent(self):
        parent_node = self.dst_node.parent
        return parent_node.archive_log if parent_node else None

    @property
    def success(self):
        return self.status == ARCHIVER_SUCCESS
    
    def __init__(self, src, dst, user, *args, **kwargs):
        super(ArchiveLog, self).__init__(*args, **kwargs)
        self.src_node = src
        self.dst_node = dst
        self.initator = user
        self.status = ARCHIVER_INITIATED
        self.save()

    def _archive_node_finished(self):
        return not any([
            value for value in self.target_addons.values()
            if value['status'] not in (ARCHIVER_SUCCESS, ARCHIVER_FAILURE)
        ])

    def _archive_tree_finished(self, dir=None):
        if not self._archive_node_finished():
            return
        if not dir:
            up_finished = self.parent.archive_tree_finished(
                dir='up'
            ) if self.parent else True
            down_finished = len(
                [
                    ret for ret in [
                        child.archive_tree_finished(
                            dir='down'
                        ) for child in self.children
                    ] if ret]
            ) if len(self.children) else True
            return up_finished and down_finished
        if dir == 'up':
            return self.parent.archive_tree_finished(dir='up') if self.parent else True
        elif dir == 'down':
            return len(
                [
                    ret for ret in [
                        child.archive_tree_finished(dir='down')
                        for child in self.children
                    ]
                ]
            ) if len(self.children) else True
        return False

    def _post_update_target(self):
        if self.archive_tree_finished():
            self.done = True
            if not ARCHIVER_FAILURE_STATUSES.isdisjoint(
                    [value['status'] for value in self.target_addons.values()]
            ):
                self.status = ARCHIVER_FAILURE
            self.save()


    def set_targets(self, addons):
        for addon in addons:
            self.target_addons[addon.config.short_name] = {
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
