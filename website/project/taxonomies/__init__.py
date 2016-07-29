import json
import os

from website import settings

from modularodm import fields, Q
from modularodm.exceptions import NoResultsFound

from framework.mongo import (
    ObjectId,
    StoredObject,
    utils as mongo_utils
)


@mongo_utils.unique_on(['id', '_id'])
class Subject(StoredObject):
    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    type = fields.StringField(required=True)
    text = fields.StringField(required=True)
    parent_id = fields.StringField()


def ensure_taxonomies():
    with open(
        os.path.join(
            settings.APP_PATH,
            'website', 'static', 'plos_taxonomy.json'
        )
    ) as fp:
        taxonomy = json.load(fp)
        # For now, only PLOS taxonomy is loaded, other types possibly considered in the future
        type = 'plos'
        for subject_path in taxonomy.get('data'):
            subjects = subject_path.split('_')
            text = subjects[-1]
            _parent = None
            if len(subjects) > 1:
                try:
                    _parent = Subject.find_one(
                        Q('text', 'eq', subjects[-2]) &
                        Q('type', 'eq', type)
                    )
                except:
                    _parent = None

            parent_id = None
            if _parent:
                parent_id = _parent._id

            try:
                subject = Subject.find_one(
                    Q('text', 'eq', text) &
                    Q('type', 'eq', type)
                )
            except NoResultsFound:
                subject = Subject(
                    type = type,
                    text = text,
                    parent_id = parent_id
                )
            else:
                subject.type = type
                subject.text = text
                subject.parent_id = parent_id

            subject.save()