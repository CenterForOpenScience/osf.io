from django.apps import apps
import logging
from framework.celery_tasks import app as celery_app
from osf.utils.workflows import CollectionSubmissionStates


logger = logging.getLogger(__name__)

@celery_app.task(ignore_results=True)
def on_collection_updated(collection_id):
    from api.share.utils import update_share

    Collection = apps.get_model('osf.Collection')
    coll = Collection.load(collection_id)

    collection_submissions = coll.collectionsubmission_set.all()

    if coll.is_public:
        # Add all collection submissions back to ES index
        coll.bulk_update_search(collection_submissions)
        # Notify SHARE for every accepted submission so collection membership is indexed
        for submission in collection_submissions.filter(
            machine_state=CollectionSubmissionStates.ACCEPTED
        ):
            update_share(submission.guid.referent)
    else:
        # Remove all collection submissions from ES index
        coll.bulk_update_search(collection_submissions, op='delete')
