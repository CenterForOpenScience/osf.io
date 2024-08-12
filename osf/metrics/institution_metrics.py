from datetime import datetime, timedelta

from elasticsearch_metrics import metrics

from api.base.settings import MAX_SIZE_OF_ES_QUERY, DEFAULT_ES_NULL_VALUE
from .metric_mixin import MetricMixin


class UserInstitutionProjectCounts(MetricMixin, metrics.Metric):
    user_id = metrics.Keyword(index=True, doc_values=True, required=True)
    institution_id = metrics.Keyword(
        index=True, doc_values=True, required=True
    )
    department = metrics.Keyword(index=True, doc_values=True, required=False)
    public_project_count = metrics.Integer(
        index=True, doc_values=True, required=True
    )
    private_project_count = metrics.Integer(
        index=True, doc_values=True, required=True
    )

    class Index:
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "refresh_interval": "1s",
        }

    class Meta:
        source = metrics.MetaField(enabled=True)

    @classmethod
    def filter_institution(cls, institution):
        return cls.search().filter("match", institution_id=institution._id)

    @classmethod
    def get_recent_datetime(cls, institution):
        search = cls.filter_institution(institution).sort("-timestamp")

        # Rounding to the nearest minute
        results = search.execute()
        if results:
            return search.execute()[0].timestamp.replace(
                microsecond=0, second=0
            )
        # If there are no results, assume yesterday.
        return datetime.now() - timedelta(days=1)

    @classmethod
    def get_department_counts(cls, institution) -> list:
        """
        Gets the most recent document for every unique user.
        :param institution: Institution
        :return: list
        """
        search = cls.filter_institution(institution).sort("timestamp")
        last_record_time = cls.get_recent_datetime(institution)

        return search.update_from_dict(
            {
                "aggs": {
                    "date_range": {
                        "filter": {
                            "range": {
                                "timestamp": {
                                    "gte": last_record_time,
                                }
                            }
                        },
                        "aggs": {
                            "departments": {
                                "terms": {
                                    "field": "department",
                                    "missing": DEFAULT_ES_NULL_VALUE,
                                    "size": 250,
                                },
                                "aggs": {
                                    "users": {"terms": {"field": "user_id"}}
                                },
                            }
                        },
                    }
                }
            }
        )

    @classmethod
    def record_user_institution_project_counts(
        cls,
        user,
        institution,
        public_project_count,
        private_project_count,
        **kwargs,
    ):
        affiliation = user.get_institution_affiliation(institution._id)
        return cls.record(
            user_id=user._id,
            institution_id=institution._id,
            department=getattr(
                affiliation, "sso_department", DEFAULT_ES_NULL_VALUE
            ),
            public_project_count=public_project_count,
            private_project_count=private_project_count,
            **kwargs,
        )

    @classmethod
    def get_current_user_metrics(cls, institution) -> list:
        """
        Gets the most recent document for every unique user.
        :param institution: Institution
        :return: list
        """
        last_record_time = cls.get_recent_datetime(institution)

        search = (
            cls.filter_institution(institution)
            .filter("range", timestamp={"gte": last_record_time})
            .sort("user_id")
        )
        search.update_from_dict({"size": MAX_SIZE_OF_ES_QUERY})

        return search


class InstitutionProjectCounts(MetricMixin, metrics.Metric):
    institution_id = metrics.Keyword(
        index=True, doc_values=True, required=True
    )
    user_count = metrics.Integer(index=True, doc_values=True, required=True)
    public_project_count = metrics.Integer(
        index=True, doc_values=True, required=True
    )
    private_project_count = metrics.Integer(
        index=True, doc_values=True, required=True
    )

    class Index:
        settings = {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "refresh_interval": "1s",
        }

    class Meta:
        source = metrics.MetaField(enabled=True)

    @classmethod
    def record_institution_project_counts(
        cls, institution, public_project_count, private_project_count, **kwargs
    ):
        return cls.record(
            institution_id=institution._id,
            user_count=institution.get_institution_users().count(),
            public_project_count=public_project_count,
            private_project_count=private_project_count,
            **kwargs,
        )

    @classmethod
    def get_latest_institution_project_document(cls, institution):
        search = (
            cls.search()
            .filter("match", institution_id=institution._id)
            .sort("-timestamp")[:1]
        )
        response = search.execute()
        if response:
            return response[0]
