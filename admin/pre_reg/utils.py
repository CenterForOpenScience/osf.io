
SORT_BY = {
    'initiator': 'initiator',
    'n_initiator': '-initiator',
    'title': 'title',
    'n_title': '-title',
    'date': 'date',
    'n_date': '-date',
    'state': 'state',
    'n_state': '-state',
}


def sort_drafts(query_set, order_by):
    if order_by == SORT_BY['date']:
        return sorted(
            query_set,
            key=lambda d: d.approval.initiation_date
        )
    elif order_by == SORT_BY['state']:
        return sorted(
            query_set,
            key=lambda d: d.approval.state,
        )
    elif order_by == SORT_BY['n_state']:
        return sorted(
            query_set,
            key=lambda d: d.approval.state,
            reverse=True
        )
    else:
        return sorted(
            query_set,
            key=lambda d: d.approval.initiation_date,
            reverse=True
        )
