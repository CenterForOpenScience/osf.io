from django.apps import apps
import logging
from framework.celery_tasks import app as celery_app


logger = logging.getLogger(__name__)

@celery_app.task(ignore_results=True)
def on_collection_updated(collection_id):
    Collection = apps.get_model('osf.Collection')
    coll = Collection.load(collection_id)

    cgms = coll.collectionsubmission_set.all()

    if coll.is_public:
        # Add all collection submissions back to ES index
        coll.bulk_update_search(cgms)
    else:
        # Remove all collection submissions from ES index
        coll.bulk_update_search(cgms, op='delete')
