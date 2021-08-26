import bleach

from rest_framework import serializers as ser
from osf.exceptions import ValidationError as ModelValidationError
from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from osf.models import Guid, Comment, BaseFileNode, SpamStatus
from rest_framework.exceptions import ValidationError, PermissionDenied
from api.base.exceptions import InvalidModelValueError, Conflict
from api.base.utils import absolute_reverse
from api.base.settings import osf_settings
from api.base.serializers import (
    JSONAPISerializer,
    TargetField,
    RelationshipField,
    IDField, TypeField, LinksField,
    AnonymizedRegexField,
    VersionedDateTimeField,
)
from api.base.versioning import get_kebab_snake_case_field


class CommentReport(object):
    def __init__(self, user_id, category, text):
        self._id = user_id
        self.category = category
        self.text = text


class CommentSerializer(JSONAPISerializer):

    filterable_fields = frozenset([
        'deleted',
        'date_created',
        'date_modified',
        'page',
        'target',
    ])

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    content = AnonymizedRegexField(source='get_content', regex=r'\[@[^\]]*\]\([^\) ]*\)', replace='@A User', required=True)
    page = ser.CharField(read_only=True)

    target = TargetField(link_type='related', meta={'type': 'get_target_type'})
    user = RelationshipField(related_view='users:user-detail', related_view_kwargs={'user_id': '<user._id>'})
    reports = RelationshipField(related_view='comments:comment-reports', related_view_kwargs={'comment_id': '<_id>'})

    date_created = VersionedDateTimeField(source='created', read_only=True)
    date_modified = VersionedDateTimeField(source='modified', read_only=True)
    modified = ser.BooleanField(source='edited', read_only=True, default=False)
    deleted = ser.BooleanField(read_only=True, source='is_deleted', default=False)
    is_abuse = ser.SerializerMethodField(help_text='If the comment has been reported or confirmed.')
    is_ham = ser.SerializerMethodField(help_text='Comment has been confirmed as ham.')
    has_report = ser.SerializerMethodField(help_text='If the user reported this comment.')
    has_children = ser.SerializerMethodField(help_text='Whether this comment has any replies.')
    can_edit = ser.SerializerMethodField(help_text='Whether the current user can edit this comment.')

    # LinksField.to_representation adds link to "self"
    links = LinksField({})

    class Meta:
        type_ = 'comments'

    def get_is_ham(self, obj):
        if obj.spam_status == SpamStatus.HAM:
            return True
        return False

    def get_has_report(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return user._id in obj.reports and not obj.reports[user._id].get('retracted', True)

    def get_is_abuse(self, obj):
        if obj.spam_status == SpamStatus.FLAGGED or obj.spam_status == SpamStatus.SPAM:
            return True
        return False

    def get_can_edit(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return obj.user._id == user._id and obj.node.can_comment(Auth(user))

    def get_has_children(self, obj):
        return Comment.objects.filter(target___id=obj._id).exists()

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'comments:comment-detail', kwargs={
                'comment_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def update(self, comment, validated_data):
        assert isinstance(comment, Comment), 'comment must be a Comment'
        auth = Auth(self.context['request'].user)

        if validated_data:
            if validated_data.get('is_deleted', None) is False and comment.is_deleted:
                try:
                    comment.undelete(auth, save=True)
                except PermissionsError:
                    raise PermissionDenied('Not authorized to undelete this comment.')
            elif validated_data.get('is_deleted', None) is True and not comment.is_deleted:
                try:
                    comment.delete(auth, save=True)
                except PermissionsError:
                    raise PermissionDenied('Not authorized to delete this comment.')
            elif 'get_content' in validated_data:
                content = validated_data.pop('get_content')
                try:
                    comment.edit(content, auth=auth, save=True)
                except PermissionsError:
                    raise PermissionDenied('Not authorized to edit this comment.')
                except ModelValidationError as err:
                    raise ValidationError(err.messages[0])
        return comment

    def get_target_type(self, obj):
        if not getattr(obj.referent, 'target_type', None):
            raise InvalidModelValueError(
                source={'pointer': '/data/relationships/target/links/related/meta/type'},
                detail='Invalid comment target type.',
            )
        return obj.referent.target_type

    def sanitize_data(self):
        ret = super(CommentSerializer, self).sanitize_data()
        content = self.validated_data.get('get_content', None)
        if content:
            ret['get_content'] = bleach.clean(content)
        return ret


class RegistrationCommentSerializer(CommentSerializer):
    replies = RelationshipField(related_view='registrations:registration-comments', related_view_kwargs={'node_id': '<node._id>'}, filter={'target': '<_id>'})
    node = RelationshipField(related_view='registrations:registration-detail', related_view_kwargs={'node_id': '<node._id>'})


class NodeCommentSerializer(CommentSerializer):
    replies = RelationshipField(related_view='nodes:node-comments', related_view_kwargs={'node_id': '<node._id>'}, filter={'target': '<_id>'})
    node = RelationshipField(related_view='nodes:node-detail', related_view_kwargs={'node_id': '<node._id>'})


class CommentCreateSerializer(CommentSerializer):

    target_type = ser.SerializerMethodField(method_name='get_validated_target_type')

    def get_validated_target_type(self, obj):
        target = obj.target
        target_type = self.context['request'].data.get('target_type')
        expected_target_type = self.get_target_type(target)
        if target_type != expected_target_type:
            raise Conflict(detail=('The target resource has a type of "{}", but you set the json body\'s type field to "{}".  You probably need to change the type field to match the target resource\'s type.'.format(expected_target_type, target_type)))
        return target_type

    def get_target(self, node_id, target_id):
        target = Guid.load(target_id)
        if not target or not getattr(target.referent, 'belongs_to_node', None):
            raise ValueError('Invalid comment target.')
        elif not target.referent.belongs_to_node(node_id):
            raise ValueError('Cannot post to comment target on another node.')
        elif isinstance(target.referent, BaseFileNode) and target.referent.provider not in osf_settings.ADDONS_COMMENTABLE:
                raise ValueError('Comments are not supported for this file provider.')
        return target

    def create(self, validated_data):
        user = validated_data['user']
        auth = Auth(user)
        node = validated_data['node']
        target_id = self.context['request'].data.get('id')

        try:
            target = self.get_target(node._id, target_id)
        except ValueError:
            raise InvalidModelValueError(
                source={'pointer': '/data/relationships/target/data/id'},
                detail='Invalid comment target \'{}\'.'.format(target_id),
            )
        validated_data['target'] = target
        validated_data['content'] = validated_data.pop('get_content')
        try:
            comment = Comment.create(auth=auth, **validated_data)
        except PermissionsError:
            raise PermissionDenied('Not authorized to comment on this project.')
        except ModelValidationError as err:
            raise ValidationError(err.messages[0])
        return comment


class CommentDetailSerializer(CommentSerializer):
    """
    Overrides CommentSerializer to make id required.
    """
    id = IDField(source='_id', required=True)
    deleted = ser.BooleanField(source='is_deleted', required=True)


class RegistrationCommentDetailSerializer(RegistrationCommentSerializer):
    id = IDField(source='_id', required=True)
    deleted = ser.BooleanField(source='is_deleted', required=True)


class NodeCommentDetailSerializer(NodeCommentSerializer):
    id = IDField(source='_id', required=True)
    deleted = ser.BooleanField(source='is_deleted', required=True)


class CommentReportSerializer(JSONAPISerializer):
    id = IDField(source='_id', read_only=True)
    type = TypeField()
    category = ser.ChoiceField(
        choices=[
            ('spam', 'Spam or advertising'),
            ('hate', 'Hate speech'),
            ('violence', 'Violence or harmful behavior'),
        ], required=True,
    )
    message = ser.CharField(source='text', required=False, allow_blank=True)
    links = LinksField({'self': 'get_absolute_url'})

    class Meta:
        @staticmethod
        def get_type(request):
            return get_kebab_snake_case_field(request.version, 'comment-reports')

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'comments:report-detail',
            kwargs={
                'user_id': obj._id,
                'comment_id': self.context['request'].parser_context['kwargs']['comment_id'],
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def create(self, validated_data):
        user = self.context['request'].user
        comment = self.context['view'].get_comment()
        if user._id in comment.reports and not comment.reports[user._id].get('retracted', True):
            raise ValidationError('Comment already reported.')
        try:
            comment.report_abuse(user, save=True, **validated_data)
        except ValueError:
            raise ValidationError('You cannot report your own comment.')
        return CommentReport(user._id, **validated_data)

    def update(self, comment_report, validated_data):
        user = self.context['request'].user
        comment = self.context['view'].get_comment()
        if user._id != comment_report._id:
            raise ValidationError('You cannot report a comment on behalf of another user.')
        try:
            comment.report_abuse(user, save=True, **validated_data)
        except ValueError:
            raise ValidationError('You cannot report your own comment.')
        return CommentReport(user._id, **validated_data)


class CommentReportDetailSerializer(CommentReportSerializer):
    """
    Overrides CommentReportSerializer to make id required.
    """
    id = IDField(source='_id', required=True)
