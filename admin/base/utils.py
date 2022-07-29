"""
Utility functions and classes
"""
from osf.models import Subject, NodeLicense, Brand

from django.core.exceptions import ValidationError, PermissionDenied
from django.urls import reverse
from django.core.validators import RegexValidator, _lazy_re_compile
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from osf.models.admin_log_entry import (
    update_admin_log,
    EMBARGO_UPDATED
)

from website import settings

validate_slug = RegexValidator(
    _lazy_re_compile(r'^[a-z]+\Z'),
    _("Enter a valid 'slug' consisting only of lowercase letters."),
    'invalid'
)

def reverse_qs(view, urlconf=None, args=None, kwargs=None, current_app=None, query_kwargs=None):
    base_url = reverse(view, urlconf=urlconf, args=args, kwargs=kwargs, current_app=current_app)
    if query_kwargs:
        return '{}?{}'.format(base_url, urlencode(query_kwargs))


def osf_staff_check(user):
    return user.is_authenticated and user.is_staff


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
        parents_left = [sub for sub in subjects_selected if not sub.parent and sub not in subjects_done]
        subjects_left = [sub for sub in subjects_selected if sub not in subjects_done and sub.parent]
        if subjects_left and not parents_left:
            raise AttributeError('Error parsing  rules - should not be children with no parents to process')
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
                            potential_children_rules.append([[parent._id, child._id], True])
                        else:
                            new_rules += potential_grandchildren_rules

                        if child_has_no_descendants_in_rules:
                            potential_children_rules.append([[parent._id, child._id], False])
                        subjects_done += used_grandchildren
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
    return NodeLicense.objects.exclude(license_id='OTHER').values_list('id', 'name')

def get_defaultlicense_choices():
    no_default = ('', '---------')
    licenses = NodeLicense.objects.exclude(license_id='OTHER')
    return [no_default] + [(lic.id, lic.__str__) for lic in licenses]

def get_brand_choices():
    no_default = ('', '---------')
    brands = Brand.objects.all()
    return [no_default] + [(brand.id, brand.name) for brand in brands]

def get_toplevel_subjects():
    return Subject.objects.filter(parent__isnull=True, provider___id='osf').values_list('id', 'text')


def validate_embargo_date(registration, user, end_date):
    if not user.has_perm('osf.change_node'):
        raise PermissionDenied('Only osf_admins may update a registration embargo.')
    if end_date - registration.registered_date >= settings.EMBARGO_END_DATE_MAX:
        raise ValidationError('Registrations can only be embargoed for up to four years.')
    elif end_date < timezone.now():
        raise ValidationError('Embargo end date must be in the future.')


def change_embargo_date(registration, user, end_date):
    """Update the embargo period of a registration
    :param registration: Registration that is being updated
    :param user: osf_admin that is updating a registration
    :param end_date: Date when the registration should be made public
    """

    validate_embargo_date(registration, user, end_date)

    if registration.embargo:
        registration.embargo.end_date = end_date
    else:
        registration._initiate_embargo(
            user,
            end_date,
            for_existing_registration=True,
            notify_initiator_on_complete=False
        )

    registration.is_public = False

    registration.embargo.save()
    registration.save()

    update_admin_log(
        user_id=user.id,
        object_id=registration.id,
        object_repr='Registration',
        message='User {} changed the embargo end date of {} to {}.'.format(
            user.pk, registration.pk, end_date
        ),
        action_flag=EMBARGO_UPDATED
    )
