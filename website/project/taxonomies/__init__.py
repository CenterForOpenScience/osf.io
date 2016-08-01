import json
import os

from website import settings

from modularodm import fields, Q
from modularodm.exceptions import NoResultsFound, MultipleResultsFound

from framework.mongo import (
    ObjectId,
    StoredObject,
    utils as mongo_utils
)


@mongo_utils.unique_on(['id', '_id'])
class Subject(StoredObject):
    id = fields.StringField(primary=True, default=lambda: str(ObjectId()))
    type = fields.StringField(required=True)
    text = fields.StringField(required=True)
    parent_ids = fields.ListField(fields.StringField())

def ensure_taxonomies():
    # Flat taxonomy is stored locally, read in here
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

            # Search for parent subject, get id if it exists
            _parent = None
            if len(subjects) > 1:
                try:
                    _parent = Subject.find_one(
                        Q('text', 'eq', subjects[-2]) &
                        Q('type', 'eq', type)
                    )
                except Exception:
                    _parent = None

            parent_id = None
            if _parent:
                parent_id = _parent.id

            try:
                subject = Subject.find_one(
                    Q('text', 'eq', text) &
                    Q('type', 'eq', type)
                )
            except NoResultsFound:
                # If subject does not yet exist, create it
                if parent_id:
                    subject = Subject(
                        type=type,
                        text=text,
                        parent_ids=[parent_id],
                    )
                else:
                    subject = Subject(
                        type=type,
                        text=text,
                        parent_ids=[],
                    )
            else:
                # If subject does exist, append parent_id if not already added
                subject.text = text
                subject.type = type
                if not parent_id in subject.parent_ids:
                    subject.parent_ids.append(parent_id)

            subject.save()