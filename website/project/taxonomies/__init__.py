from modularodm import fields
from modularodm.exceptions import ValidationValueError

from framework.mongo import (
    ObjectId,
    StoredObject,
    utils as mongo_utils
)

from website.util import api_v2_url


@mongo_utils.unique_on(['text'])
class Subject(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    text = fields.StringField(required=True)
    parents = fields.ForeignField('subject', list=True)
    children = fields.ForeignField('subject', list=True)

    @property
    def absolute_api_v2_url(self):
        return api_v2_url('taxonomies/{}/'.format(self._id))

    @property
    def child_count(self):
        return len(self.children)

    def get_absolute_url(self):
        return self.absolute_api_v2_url


def validate_subject_hierarchy(subject_hierarchy):
    grandparent = None
    parent = None
    child = None
    for subject_id in subject_hierarchy:
        subject = Subject.load(subject_id)
        if not subject:
            raise ValidationValueError('Subject with id <{}> could not be found.'.format(subject_id))
        if not subject.parents:
            grandparent = subject
        elif not subject.children:
            child = subject
        else:
            parent = subject
    if not grandparent:
        raise ValidationValueError('Unable to find root subject in {}'.format(subject_hierarchy))
    if (parent and parent not in grandparent.children) or (child and (not parent or child not in parent.children)):
        raise ValidationValueError('Invalid subject hierarchy: {}'.format(subject_hierarchy))
