"""
Utility functions and classes
"""
from modularodm import Q
from osf.models import Subject, NodeLicense

from django.core.urlresolvers import reverse
from django.utils.http import urlencode


def reverse_qs(view, urlconf=None, args=None, kwargs=None, current_app=None, query_kwargs=None):
    base_url = reverse(view, urlconf=urlconf, args=args, kwargs=kwargs, current_app=current_app)
    if query_kwargs:
        return '{}?{}'.format(base_url, urlencode(query_kwargs))


def osf_staff_check(user):
    return user.is_authenticated and user.is_staff


def rules_to_subjects(rules):
    """
    Take a list of rules, and return the subjects that are included in that rule.

    Code copied from the property `all_subjects` in the PreprintProvider model.

    :param rules: list of properly formatted subject rules
    :return: list of subject ids included in the rules
    """
    q = []
    for rule in rules:
        if rule[1]:
            q.append(Q('parents', 'eq', Subject.load(rule[0][-1])))
            if len(rule[0]) == 1:
                potential_parents = Subject.find(Q('parents', 'eq', Subject.load(rule[0][-1])))
                for parent in potential_parents:
                    q.append(Q('parents', 'eq', parent))
        for sub in rule[0]:
            q.append(Q('_id', 'eq', sub))
    return Subject.find(reduce(lambda x, y: x | y, q)) if len(q) > 1 else (Subject.find(q[0]) if len(q) else Subject.find())


def get_subject_rules(subjects_selected):
    """
    Take a list of subjects, and parse them into rules consistent with preprpint provider
    rules and subjects. A "rule" consists of a hierarchy of Subject _ids, and a boolean value
    describing if the rest of the descendants of the last subject in the list are included or not.

    Example:
    rules = [
        [
            [u'58bdd0bfb081dc0811b9e0ae', u'58bdd099b081dc0811b9de09'],
            True
        ]
    ]

    :param subjects_selected: list of ids of subjects selected from the form
    :return: subject "rules" properly formatted
    """
    new_rules = []
    subjects_done = []
    while len(subjects_done) < len(subjects_selected):
        parents_left = [sub for sub in subjects_selected if sub.parents.count() == 0 and sub not in subjects_done]
        subjects_left = [sub for sub in subjects_selected if sub not in subjects_done and sub.parents.exists()]
        for parent in parents_left:
            parent_has_no_descendants_in_rules = True
            used_children = []
            all_grandchildren = False
            potential_children_rules = []
            for child in parent.children.all():
                child_has_no_descendants_in_rules = True
                if child in subjects_selected:
                    used_children.append(child)
                    used_grandchildren = []
                    potential_grandchildren_rules = []
                    parent_has_no_descendants_in_rules = False

                    if child in subjects_left:
                        for grandchild in child.children.all():
                            if grandchild in subjects_selected:
                                child_has_no_descendants_in_rules = False

                                if grandchild in subjects_left:
                                    potential_grandchildren_rules.append([[parent._id, child._id, grandchild._id], False])
                                used_grandchildren.append(grandchild)

                        if len(used_grandchildren) == child.children.count():
                            all_grandchildren = True
                            subjects_done += used_grandchildren
                            potential_children_rules.append([[parent._id, child._id], True])
                        else:
                            new_rules += potential_grandchildren_rules

                        if child_has_no_descendants_in_rules:
                            potential_children_rules.append([[parent._id, child._id], False])
                subjects_done += used_children

            if parent_has_no_descendants_in_rules:
                new_rules.append([[parent._id], False])

            elif parent.children.count() == len(used_children) and all_grandchildren:
                new_rules.append([[parent._id], True])
            else:
                new_rules += potential_children_rules

            subjects_done.append(parent)

    return new_rules


def get_nodelicense_choices():
    return [(sub.id, sub.text) for sub in NodeLicense.objects.all()]


def get_toplevel_subjects():
    subjects = Subject.objects.filter(parents__isnull=True)
    return [(sub.id, sub.text) for sub in subjects]
