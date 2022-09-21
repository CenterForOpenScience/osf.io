from django.apps import apps
from framework.celery_tasks import app as celery_app


@celery_app.task()
def check_resource_for_domains(guid, content):
    Guid = apps.get_model('osf.Guid')
    resource = Guid.load(guid).referent
    resource.moderate_domains(
        content,
        confirm_spam=True,
    )
