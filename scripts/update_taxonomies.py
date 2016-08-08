import os
import json
from framework.mongo import set_up_storage

from website import settings
from website.project.taxonomies import Subject

from modularodm import Q, storage
from modularodm.exceptions import NoResultsFound, MultipleResultsFound


def update_taxonomies():
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
                parent_id = _parent._id

            try:
                subject = Subject.find_one(
                    Q('text', 'eq', text) &
                    Q('type', 'eq', type)
                )
            except (NoResultsFound, MultipleResultsFound):
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
                if parent_id not in subject.parent_ids:
                    subject.parent_ids.append(parent_id)

            subject.save()


if __name__ == '__main__':
    set_up_storage([Subject], storage.MongoStorage)
    update_taxonomies()
