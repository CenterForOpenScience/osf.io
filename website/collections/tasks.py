from django.apps import apps
import logging
from framework.celery_tasks import app as celery_app
from website.search import driver


logger = logging.getLogger(__name__)

@celery_app.task(ignore_results=True)
def on_collection_updated(collection_id):
    Collection = apps.get_model('osf.Collection')
    coll = Collection.load(collection_id)

    driver.index_collection_submissions(collection_id=coll)
