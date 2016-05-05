# -*- coding: utf-8 -*-


def get_entry_point(system_tags):
    """
    Given the user system_tags, return the user entry point (osf, osf4m, prereg, institution)
    In case of multiple entry_points existing in the system_tags, return only the first one.
    """
    entry_points = ['osf4m', 'prereg_challenge_campaign', 'institution_campaign']
    for i in system_tags:
        if i in entry_points:
            return i
    else:
        return 'osf'


def get_sorted_index(l, reverse=True):
    """
    Get the sorted index of the original list.
    """
    return sorted(range(len(l)), key=lambda k: l[k], reverse=reverse)
