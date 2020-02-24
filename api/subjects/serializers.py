from rest_framework import serializers as ser
from rest_framework import exceptions

from framework.auth.core import Auth
from framework.exceptions import PermissionsError

from api.base.serializers import (
    JSONAPISerializer,
    JSONAPIRelationshipSerializer,
    LinksField,
    RelationshipField,
    BaseAPISerializer,
)
from osf.exceptions import NodeStateError, ValidationValueError


class UpdateSubjectsMixin(object):
    def update_subjects_method(self, resource, subjects, auth):
        # Method to update subjects on resource
        raise NotImplementedError()

    def update_subjects(self, resource, subjects, auth):
        """Updates subjects on resource and handles errors.

        :param object resource: Object for which you want to update subjects
        :param list subjects: Subjects array (or array of arrays)
        :param object Auth object
        """
        try:
            self.update_subjects_method(resource, subjects, auth)
        except PermissionsError as e:
            raise exceptions.PermissionDenied(detail=str(e))
        except ValueError as e:
            raise exceptions.ValidationError(detail=str(e))
        except ValidationValueError as e:
            raise exceptions.ValidationError(detail=list(e)[0])
        except NodeStateError as e:
            raise exceptions.ValidationError(detail=str(e))


class SubjectSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'text',
        'parent',
        'id',
    ])
    id = ser.CharField(source='_id', required=True)
    text = ser.CharField(max_length=200)
    taxonomy_name = ser.CharField(source='provider.share_title', read_only=True)

    parent = RelationshipField(
        related_view='subjects:subject-detail',
        related_view_kwargs={'subject_id': '<parent._id>'},
        always_embed=True,
    )

    children = RelationshipField(
        related_view='subjects:subject-children',
        related_view_kwargs={'subject_id': '<_id>'},
        related_meta={'count': 'get_children_count'},

    )

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_subject_url

    def get_children_count(self, obj):
        return obj.children_count if hasattr(obj, 'children_count') else obj.child_count

    class Meta:
        type_ = 'subjects'


class SubjectRelated(JSONAPIRelationshipSerializer):
    id = ser.CharField(source='_id', required=False, allow_null=True)
    class Meta:
        type_ = 'subjects'


class SubjectsRelationshipSerializer(BaseAPISerializer, UpdateSubjectsMixin):
    data = ser.ListField(child=SubjectRelated())
    links = LinksField({
        'self': 'get_self_url',
        'html': 'get_related_url',
    })

    def get_self_url(self, obj):
        return obj['self'].subjects_relationship_url

    def get_related_url(self, obj):
        return obj['self'].subjects_url

    class Meta:
        type_ = 'subjects'

    def make_instance_obj(self, obj):
        return {
            'data': obj.subjects.all(),
            'self': obj,
        }

    def format_subjects(self, subjects):
        return [subj['_id'] for subj in subjects]

    def update_subjects_method(self, resource, subjects, auth):
        # Overrides UpdateSubjectsMixin
        return resource.set_subjects_from_relationships(subjects, auth)

    def update(self, instance, validated_data):
        resource = instance['self']
        user = self.context['request'].user
        auth = Auth(user if not user.is_anonymous else None)
        self.update_subjects(resource, self.format_subjects(validated_data['data']), auth)
        return self.make_instance_obj(resource)
