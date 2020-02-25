import datetime as dt

from django.core.management.base import BaseCommand

from osf.metrics import InstitutionProjectCounts, UserInstitutionProjectCounts
from osf.models import Institution, Node
from osf.utils.permissions import WRITE_NODE

def update_institution_project_counts():
    now = dt.datetime.now()

    for institution in Institution.objects.all():

        if institution.osfuser_set.exists() and institution.nodes.exists():
            base_institution_project_qs = institution.nodes.filter(type='osf.node').filter(parent_nodes=None)
            institution_public_projects_qs = base_institution_project_qs.filter(is_public=True)
            institution_private_projects_qs = base_institution_project_qs.filter(is_public=False)

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
                    permission=WRITE_NODE,
                    base_queryset=institution_public_projects_qs,
                    include_public=True
                ).count()

                user_private_project_count = Node.objects.get_nodes_for_user(
                    user=user,
                    permission=WRITE_NODE,
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
