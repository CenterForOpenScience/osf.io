# -*- coding: utf-8 -*-


class TokuTransaction(object):
    """DEPRECATED. Transaction context manager. Begin transaction on enter; rollback or
    commit on exit. This behaves like `django.db.transaction.atomic` and exists only to
    support legacy code.

    This class is deprecated: use `django.db.transaction.atomic` instead.
    """
    def __init__(self, database=None):
        raise Exception('This functionality is deprecated, use `django.db.transaction.atomic`')
