from elasticsearch_metrics import metrics

from osf.utils.workflows import RegistrationModerationTriggers, RegistrationModerationStates
from .metric_mixin import MetricMixin


class RegistriesModerationMetrics(MetricMixin, metrics.Metric):
    registration_id = metrics.Keyword(index=True, doc_values=True, required=True)
    provider_id = metrics.Keyword(index=True, doc_values=True, required=True)
    trigger = metrics.Keyword(index=True, doc_values=True, required=True)
    from_state = metrics.Keyword(index=True, doc_values=True, required=True)
    to_state = metrics.Keyword(index=True, doc_values=True, required=True)
    user_id = metrics.Keyword(index=True, doc_values=True, required=True)
    comment = metrics.Keyword(index=True)

    class Index:
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 1,
            'refresh_interval': '1s',
        }

    class Meta:
        source = metrics.MetaField(enabled=True)

    @classmethod
    def record_transitions(cls, action):
        return cls.record(
            registration_id=action.target._id,
            provider_id=action.target.provider._id,
            from_state=action.from_state,
            to_state=action.to_state,
            trigger=action.trigger,
            user_id=action.creator._id,
            comment=action.comment,
        )

    @classmethod
    def get_registries_info(cls) -> dict:
        """
        Gets metrics info for each registry
        expected output:
        {
            'doc_count_error_upper_bound': 0,
            'sum_other_doc_count': 0,
            'buckets': [{
                'key': 'osf',
                'doc_count': 6,
                'rejected': {'doc_count': 0},
                'submissions': {'doc_count': 3},
                'not_embargoed_but_accepted': {'doc_count': 0},
                'withdrawn': {'doc_count': 0},
                'transitions_without_comments': {'doc_count': 1},
                'embargoed': {'doc_count': 0},
                'transitions_with_comments': {'doc_count': 5}
            },
            {
                'key': 'provider2',
               'doc_count': 4,
               'rejected': {'doc_count': 1},
               'submissions': {'doc_count': 1},
               'not_embargoed_but_accepted': {'doc_count': 1},
               'withdrawn': {'doc_count': 0},
               'transitions_without_comments': {'doc_count': 0},
               'embargoed': {'doc_count': 0},
               'transitions_with_comments': {'doc_count': 4}
               }]
        }
        :return: dict
        """
        search = cls.search()

        return search.update_from_dict({
            'aggs': {
                'providers': {
                    'terms': {
                        'field': 'provider_id'
                    },
                    'aggs': {
                        'transitions_without_comments': {
                            'missing': {
                                'field': 'comment'
                            }
                        },
                        'transitions_with_comments': {
                            'filter': {
                                'exists': {
                                    'field': 'comment'
                                }
                            }
                        },
                        'submissions': {
                            'filter': {
                                'match': {
                                    'trigger': {
                                        'query': RegistrationModerationTriggers.SUBMIT.db_name
                                    }
                                }
                            }
                        },
                        'accepted_with_embargo': {
                            'filter': {
                                'bool': {
                                    'must': [
                                        {
                                            'match': {
                                                'to_state': RegistrationModerationStates.EMBARGO.db_name
                                            }
                                        },
                                        {
                                            'match': {
                                                'trigger': RegistrationModerationTriggers.SUBMIT.db_name
                                            }
                                        }
                                    ]
                                }
                            }
                        },
                        'accepted_without_embargo': {
                            'filter': {
                                'bool': {
                                    'must': [
                                        {
                                            'match': {
                                                'to_state': RegistrationModerationStates.ACCEPTED.db_name
                                            }
                                        },
                                        {
                                            'match': {
                                                'trigger': RegistrationModerationTriggers.SUBMIT.db_name
                                            }
                                        }
                                    ]
                                }
                            }
                        },
                        'rejected': {
                            'filter': {
                                'bool': {
                                    'must': [
                                        {
                                            'match': {
                                                'to_state': RegistrationModerationStates.REJECTED.db_name
                                            }
                                        },
                                        {
                                            'match': {
                                                'trigger': RegistrationModerationTriggers.REJECT_SUBMISSION.db_name
                                            }
                                        }
                                    ]
                                }
                            }
                        },
                        'withdrawn': {
                            'filter': {
                                'bool': {
                                    'must': [
                                        {
                                            'match': {
                                                'to_state': RegistrationModerationStates.WITHDRAWN.db_name
                                            }
                                        },
                                        {
                                            'match': {
                                                'trigger': RegistrationModerationTriggers.ACCEPT_WITHDRAWAL.db_name
                                            }
                                        }
                                    ]
                                }
                            }
                        },
                    }
                }
            }
        }).execute().aggregations['providers'].to_dict()
