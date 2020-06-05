import datetime as dt

from django.core.management.base import BaseCommand

from framework.celery_tasks import app as celery_app
from osf.metrics import InstitutionProjectCounts, UserInstitutionProjectCounts
from osf.models import Institution, Node


@celery_app.task(name='management.commands.update_institution_project_counts')
def update_institution_project_counts():
    now = dt.datetime.now()

    for institution in Institution.objects.all():

        institution_public_projects_qs = institution.nodes.filter(type='osf.node', parent_nodes=None, is_public=True, is_deleted=False)
        institution_private_projects_qs = institution.nodes.filter(type='osf.node', parent_nodes=None, is_public=False, is_deleted=False)

        institution_public_projects_count = institution_public_projects_qs.count()
        institution_private_projects_count = institution_private_projects_qs.count()

        InstitutionProjectCounts.record_institution_project_counts(
            institution=institution,
            public_project_count=institution_public_projects_count,
            private_project_count=institution_private_projects_count,
            timestamp=now
        )

        for user in institution.osfuser_set.all():
            user_public_project_count = Node.objects.get_nodes_for_user(
                user=user,
                base_queryset=institution_public_projects_qs
            ).count()

            user_private_project_count = Node.objects.get_nodes_for_user(
                user=user,
                base_queryset=institution_private_projects_qs
            ).count()

            UserInstitutionProjectCounts.record_user_institution_project_counts(
                user=user,
                institution=institution,
                public_project_count=user_public_project_count,
                private_project_count=user_private_project_count,
                timestamp=now
            )


class Command(BaseCommand):

    def handle(self, *args, **options):
        update_institution_project_counts()
