from rest_framework import exceptions
from rest_framework import serializers as ser

from osf.exceptions import ValidationError, NodeStateError
from api.base.serializers import RelationshipField
from api.base.serializers import JSONAPISerializer, IDField, TypeField
from api.base.exceptions import InvalidModelValueError
from api.base.utils import absolute_reverse, get_user_auth
from api.taxonomies.serializers import TaxonomizableSerializerMixin
from framework.exceptions import PermissionsError
from osf.utils.permissions import WRITE
from osf.models import Guid


class GuidRelationshipField(RelationshipField):
    def get_object(self, _id):
        return Guid.load(_id)

    def to_internal_value(self, data):
        guid = self.get_object(data)
        return {'guid': guid}


class CollectionSubmissionSerializer(TaxonomizableSerializerMixin, JSONAPISerializer):

    class Meta:
        type_ = 'collection-submission'

    filterable_fields = frozenset([
        'id',
        'collected_type',
        'date_created',
        'date_modified',
        'subjects',
        'status',
    ])
    id = IDField(source='_id', read_only=True)
    type = TypeField()

    creator = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<creator._id>'},
    )
    collection = RelationshipField(
        related_view='collections:collection-detail',
        related_view_kwargs={'collection_id': '<collection._id>'},
    )
    guid = RelationshipField(
        related_view='guids:guid-detail',
        related_view_kwargs={'guids': '<guid._id>'},
        always_embed=True,
    )

    @property
    def subjects_related_view(self):
        # Overrides TaxonomizableSerializerMixin
        return 'collections:collection-submissions-subjects-list'

    @property
    def subjects_self_view(self):
        # Overrides TaxonomizableSerializerMixin
        return 'collections:collection-submissions-subjects-relationship-list'

    @property
    def subjects_view_kwargs(self):
        # Overrides TaxonomizableSerializerMixin
        return {'collection_id': '<collection._id>', 'cgm_id': '<guid._id>'}

    collected_type = ser.CharField(required=False)
    status = ser.CharField(required=False)
    volume = ser.CharField(required=False)
    issue = ser.CharField(required=False)
    program_area = ser.CharField(required=False)
    school_type = ser.CharField(required=False)
    study_design = ser.CharField(required=False)

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'collection_submissions:collection-submissions-detail',
            kwargs={
                'collection_id': obj.collection._id,
                'cgm_id': obj.guid._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def update(self, obj, validated_data):
        if validated_data and 'subjects' in validated_data:
            auth = get_user_auth(self.context['request'])
            subjects = validated_data.pop('subjects', None)
            self.update_subjects(obj, subjects, auth)

        if 'status' in validated_data:
            obj.status = validated_data.pop('status')
        if 'collected_type' in validated_data:
            obj.collected_type = validated_data.pop('collected_type')
        if 'volume' in validated_data:
            obj.volume = validated_data.pop('volume')
        if 'issue' in validated_data:
            obj.issue = validated_data.pop('issue')
        if 'program_area' in validated_data:
            obj.program_area = validated_data.pop('program_area')
        if 'school_type' in validated_data:
            obj.school_Type = validated_data.pop('school_type')
        if 'study_design' in validated_data:
            obj.study_design = validated_data.pop('study_design')

        obj.save()
        return obj


class CollectionSubmissionCreateSerializer(CollectionSubmissionSerializer):
    # Makes guid writeable only on create
    guid = GuidRelationshipField(
        related_view='guids:guid-detail',
        related_view_kwargs={'guids': '<guid._id>'},
        always_embed=True,
        read_only=False,
        required=True,
    )

    def create(self, validated_data):
        subjects = validated_data.pop('subjects', None)
        collection = validated_data.pop('collection', None)
        creator = validated_data.pop('creator', None)
        guid = validated_data.pop('guid')
        if not collection:
            raise exceptions.ValidationError('"collection" must be specified.')
        if not creator:
            raise exceptions.ValidationError('"creator" must be specified.')
        if not (creator.has_perm('write_collection', collection) or (hasattr(guid.referent, 'has_permission') and guid.referent.has_permission(creator, WRITE))):
            raise exceptions.PermissionDenied('Must have write permission on either collection or collected object to collect.')
        try:
            obj = collection.collect_object(guid.referent, creator, **validated_data)
        except ValidationError as e:
            raise InvalidModelValueError(e.message)
        if subjects:
            auth = get_user_auth(self.context['request'])
            try:
                obj.set_subjects(subjects, auth)
            except PermissionsError as e:
                raise exceptions.PermissionDenied(detail=str(e))
            except (ValueError, NodeStateError) as e:
                raise exceptions.ValidationError(detail=str(e))
        return obj
