from django.db.models import (
    BooleanField,
    Case,
    Exists,
    F,
    IntegerField,
    Max,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast

from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import NonNaiveDateTimeField
from osf.models import FileVersion


# Get date modified for OSF and non-OSF providers
DATE_MODIFIED = Case(
    When(
        provider="osfstorage",
        then=Cast(Max("versions__created"), NonNaiveDateTimeField()),
    ),
    default=Cast(
        KeyTextTransform(
            "value",
            Cast(
                KeyTextTransform(
                    "modified",
                    Cast(
                        KeyTextTransform(
                            -1,
                            "_history",
                        ),
                        output_field=DateTimeAwareJSONField(),
                    ),
                ),
                output_field=DateTimeAwareJSONField(),
            ),
        ),
        output_field=NonNaiveDateTimeField(),
    ),
)


def make_show_as_unviewed_annotations(user):
    """Returns the annotations required to set the current_user_has_viewed attribute.

    Usage:
    OsfStorageFile.objects.annotate(**make_show_as_unviewed_annotations(request.user))

    show_as_unviewed is only true if the user has not seen the latest version of a file
    but has looked at it previously. Making this determination requires multiple annotations,
    which is why this returns a dictionary that must be unpacked into kwargs.
    """
    if user.is_anonymous:
        return {"show_as_unviewed": Value(False, output_field=BooleanField())}

    seen_versions = FileVersion.objects.annotate(
        latest_version=Subquery(
            FileVersion.objects.filter(
                basefilenode=OuterRef("basefilenode"),
            )
            .order_by("-created")
            .values("id")[:1],
            output_field=IntegerField(),
        ),
    ).filter(seen_by=user)

    has_seen_latest = Exists(
        seen_versions.filter(basefilenode=OuterRef("id")).filter(
            id=F("latest_version"),
        ),
    )
    has_previously_seen = Exists(
        seen_versions.filter(basefilenode=OuterRef("id")).exclude(
            id=F("latest_version"),
        ),
    )
    show_as_unviewed = Case(
        When(
            Q(has_seen_latest=False) & Q(has_previously_seen=True),
            then=Value(True),
        ),
        default=Value(False),
        output_field=BooleanField(),
    )

    return {
        "has_seen_latest": has_seen_latest,
        "has_previously_seen": has_previously_seen,
        "show_as_unviewed": show_as_unviewed,
    }


def check_show_as_unviewed(user, osf_file):
    """A separate function for assigning the show_as_unviewed value to a single instance.

    Our logic is not conducive to assigning annotations to a single file, so do it manually
    in the DetailView case.
    """
    if user.is_anonymous:
        return False

    latest_version = osf_file.versions.order_by("-created").first()
    return (
        osf_file.versions.filter(seen_by=user).exists()
        and not latest_version.seen_by.filter(id=user.id).exists()
    )
