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

    @property
    def hierarchy(self):
        if self.parents:
            return self.parents[0].hierarchy + [self._id]
        return [self._id]

def validate_subject_hierarchy(subject_hierarchy):
    validated_hierarchy, raw_hierarchy = [], set(subject_hierarchy)
    for subject_id in subject_hierarchy:
        subject = Subject.load(subject_id)
        if not subject:
            raise ValidationValueError('Subject with id <{}> could not be found.'.format(subject_id))

        if subject.parents.exists():
            continue

        raw_hierarchy.remove(subject_id)
        validated_hierarchy.append(subject._id)

        while raw_hierarchy:
            if not set(subject.children.values_list('_id', flat=True)) & raw_hierarchy:
                raise ValidationValueError('Invalid subject hierarchy: {}'.format(subject_hierarchy))
            else:
                for child in subject.children.filter(_id__in=raw_hierarchy):
                    subject = child
                    validated_hierarchy.append(child._id)
                    raw_hierarchy.remove(child._id)
                    break
        if set(validated_hierarchy) == set(subject_hierarchy):
            return
        else:
            raise ValidationValueError('Invalid subject hierarchy: {}'.format(subject_hierarchy))
    raise ValidationValueError('Unable to find root subject in {}'.format(subject_hierarchy))
