import dataclasses

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, F, Sum

from osf import models as osfdb
from osf.models.spam import SpamStatus
from addons.osfstorage.models import OsfStorageFile
from osf.metrics.reports import InstitutionalUserReport
from osf.metrics.utils import YearMonth
from ._base import MonthlyReporter


_CHUNK_SIZE = 500


class InstitutionalUsersReporter(MonthlyReporter):
    '''build an InstitutionalUserReport for each institution-user affiliation

    built for the institution dashboard at ://osf.example/institutions/<id>/dashboard/,
    which offers institutional admins insight into how people at their institution are
    using osf, based on their explicitly-affiliated osf objects
    '''
    def iter_report_kwargs(self, continue_after: dict | None = None):
        _before_datetime = self.yearmonth.month_end()
        _inst_qs = (
            osfdb.Institution.objects
            .filter(created__lt=_before_datetime)
            .order_by('pk')
        )
        if continue_after:
            _inst_qs = _inst_qs.filter(pk__gte=continue_after['institution_pk'])
        for _institution in _inst_qs:
            _user_qs = _institution.get_institution_users().filter(created__lt=_before_datetime)
            if continue_after and (_institution.pk == continue_after['institution_pk']):
                _user_qs = _user_qs.filter(pk__gt=continue_after['user_pk'])
            for _user_pk in _user_qs.values_list('pk', flat=True).iterator(chunk_size=_CHUNK_SIZE):
                yield {'institution_pk': _institution.pk, 'user_pk': _user_pk}

    def report(self, **report_kwargs):
        _institution = osfdb.Institution.objects.get(pk=report_kwargs['institution_pk'])
        _user = osfdb.OSFUser.objects.get(pk=report_kwargs['user_pk'])
        _helper = _InstiUserReportHelper(_institution, _user, self.yearmonth)
        return _helper.report


# helper
@dataclasses.dataclass
class _InstiUserReportHelper:
    institution: osfdb.Institution
    user: osfdb.OSFUser
    yearmonth: YearMonth
    report: InstitutionalUserReport = dataclasses.field(init=False)

    def __post_init__(self):
        _affiliation = self.user.get_institution_affiliation(self.institution._id)
        self.report = InstitutionalUserReport(
            institution_id=self.institution._id,
            user_id=self.user._id,
            user_name=self.user.fullname,
            department_name=(_affiliation.sso_department or None),
            month_last_login=(
                YearMonth.from_date(self.user.date_last_login)
                if self.user.date_last_login is not None
                else None
            ),
            month_last_active=self._get_last_active(),
            account_creation_date=YearMonth.from_date(self.user.created),
            orcid_id=self.user.get_verified_external_id('ORCID', verified_only=True),
            public_project_count=self._public_project_queryset().count(),
            private_project_count=self._private_project_queryset().count(),
            public_registration_count=self._public_registration_queryset().count(),
            embargoed_registration_count=self._embargoed_registration_queryset().count(),
            public_file_count=self._public_osfstorage_file_queryset().count(),
            published_preprint_count=self._published_preprint_queryset().count(),
            storage_byte_count=self._storage_byte_count(),
        )

    @property
    def before_datetime(self):
        return self.yearmonth.month_end()

    def _node_queryset(self):
        _institution_node_qs = self.institution.nodes.filter(
            created__lt=self.before_datetime,
            is_deleted=False,
        ).exclude(spam_status=SpamStatus.SPAM)
        return osfdb.Node.objects.get_nodes_for_user(
            user=self.user,
            base_queryset=_institution_node_qs,
        )

    def _public_project_queryset(self):
        return self._node_queryset().filter(
            type='osf.node',  # `type` field from TypedModel
            is_public=True,
            root_id=F('pk'),  # only root nodes
        )

    def _private_project_queryset(self):
        return self._node_queryset().filter(
            type='osf.node',  # `type` field from TypedModel
            is_public=False,
            root_id=F('pk'),  # only root nodes
        )

    def _public_registration_queryset(self):
        return self._node_queryset().filter(
            type='osf.registration',  # `type` field from TypedModel
            is_public=True,
            root_id=F('pk'),  # only root nodes
        )

    def _embargoed_registration_queryset(self):
        return self._node_queryset().filter(
            type='osf.registration',  # `type` field from TypedModel
            is_public=False,
            root_id=F('pk'),  # only root nodes
            embargo__end_date__gte=self.before_datetime,
        )

    def _published_preprint_queryset(self):
        return (
            osfdb.Preprint.objects.can_view()  # published/publicly-viewable
            .filter(
                affiliated_institutions=self.institution,
                _contributors=self.user,
                date_published__lt=self.before_datetime,
            )
            .exclude(spam_status=SpamStatus.SPAM)
        )

    def _public_osfstorage_file_queryset(self):
        _target_node_q = Q(
            # any public project, registration, project component, or registration component
            target_object_id__in=self._node_queryset().filter(is_public=True).values('pk'),
            target_content_type=ContentType.objects.get_for_model(osfdb.AbstractNode),
        )
        _target_preprint_q = Q(
            target_object_id__in=self._published_preprint_queryset().values('pk'),
            target_content_type=ContentType.objects.get_for_model(osfdb.Preprint),
        )
        return (
            OsfStorageFile.objects
            .filter(
                created__lt=self.before_datetime,
                deleted__isnull=True,
                purged__isnull=True,
            )
            .filter(_target_node_q | _target_preprint_q)
        )

    def _storage_byte_count(self):
        return osfdb.FileVersion.objects.filter(
            size__gt=0,
            created__lt=self.before_datetime,
            purged__isnull=True,
            basefilenode__in=self._public_osfstorage_file_queryset(),
        ).aggregate(storage_bytes=Sum('size', default=0))['storage_bytes']

    def _get_last_active(self):
        end_date = self.yearmonth.month_end()

        node_logs = self.user.logs.filter(created__lt=end_date).order_by('-created')
        preprint_logs = self.user.preprint_logs.filter(created__lt=end_date).order_by('-created')

        dates = filter(bool, [
            node_logs.values_list('created', flat=True).first(),
            preprint_logs.values_list('created', flat=True).first(),
        ])

        latest_activity_date = max(dates, default=None)

        if latest_activity_date:
            return YearMonth.from_date(latest_activity_date)
        else:
            return None
