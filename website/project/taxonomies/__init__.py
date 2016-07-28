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
    parent = fields.ForeignField('subject', index=True)


def ensure_taxonomies():
    with open(
        os.path.join(
            settings.APP_PATH,
            'website', 'static', 'plos_taxonomy.json'
        )
    ) as fp:
        taxonomy = json.load(fp)
        # For now, only PLOS taxonomies are loaded, other types possibly considered in the future
        type = 'plos'
        for subject_path in taxonomy.get('data'):
            subjects = subject_path.split('_')
            text = subjects[-1]
            parent = None
            if len(subjects) > 1:
                parent = subjects[-2]

            try:
                subject = Subject.find_one(
                    Q('text', 'eq', text) &
                    Q('type', 'eq', type)
                )
            except NoResultsFound:
                subject = Subject(
                    type = type,
                    text = text,
                    parent = parent
                )
            else:
                subject.type = type
                subject.text = text
                subject.parent = parent
            subject.save()