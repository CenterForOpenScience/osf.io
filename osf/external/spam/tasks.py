from django.apps import apps
from framework.celery_tasks import app as celery_app


@celery_app.task()
def check_resource_for_domains(guid):
    Guid = apps.get_model('osf.Guid')
    NotableDomain = apps.get_model('osf.NotableDomain')
    resource = Guid.load(guid).referent
    NotableDomain.check_resource_for_domains(
        resource,
        confirm_spam=True,
        send_to_moderation=True
    )
