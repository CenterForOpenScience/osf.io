from django.db.models.functions import Concat
from django.db.models import Value
from modularodm import Q

from website.models import MetaSchema
from website.project.model import Sanction

from admin.common_auth.models import MyUser


SORT_BY = {
    'initiator': 'initiator',
    'n_initiator': '-initiator',
    'title': 'title',
    'n_title': '-title',
    'date': 'date',
    'n_date': '-date',
}

VIEW_STATUS = {
    'all': 'all',
    'pending': 'pending',
    'approved': 'approved',
    'rejected': 'rejected',
}


def get_prereg_reviewers():
    return MyUser.objects.filter(
        groups__name='prereg_group'
    ).annotate(
        fuller_name=Concat('first_name', Value(' '), 'last_name')
    ).values_list(
        'email', 'fuller_name'
    )


def sort_drafts(query_set, order_by):
    if order_by == SORT_BY['title']:
        return sorted(
            query_set,
            key=lambda d: d.registration_metadata['q1']['value']
        )
    elif order_by == SORT_BY['n_title']:
        return sorted(
            query_set,
            key=lambda d: d.registration_metadata['q1']['value'],
            reverse=True
        )
    elif order_by == SORT_BY['date']:
        return sorted(
            query_set,
            key=lambda d: d.approval.initiation_date
        )
    elif order_by == SORT_BY['n_date']:
        return sorted(
            query_set,
            key=lambda d: d.approval.initiation_date,
            reverse=True
        )


def build_query(status):
    prereg_schema = MetaSchema.find_one(
        Q('name', 'eq', 'Prereg Challenge') &
        Q('schema_version', 'eq', 2)
    )
    query = (
            Q('registration_schema', 'eq', prereg_schema)
        )
    if status == VIEW_STATUS['pending']:
        query &= Q('approval.state', 'eq', Sanction.UNAPPROVED)
    elif status == VIEW_STATUS['approved']:
        query &= Q('approval.state', 'eq', Sanction.APPROVED)
    elif status == VIEW_STATUS['rejected']:
        query &= Q('approval.state', 'eq', Sanction.REJECTED)
    else:
        query &= Q('approval', 'ne', None)
    return query
