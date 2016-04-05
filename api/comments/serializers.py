import bleach

from rest_framework import serializers as ser
from modularodm import Q
from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from framework.guid.model import Guid
from website.models import User  # for getting contributors
from website.files.models import StoredFileNode
from website.project.model import Comment, Node
from rest_framework.exceptions import ValidationError, PermissionDenied
from api.base.exceptions import InvalidModelValueError, Conflict
from api.base.utils import absolute_reverse, get_object_or_error
from api.base.settings import osf_settings
from api.base.serializers import (JSONAPISerializer,
                                  TargetField,
                                  RelationshipField,
                                  IDField, TypeField, LinksField,
                                  AuthorizedCharField)


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
        'target'
    ])

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    content = AuthorizedCharField(source='get_content', required=True, max_length=osf_settings.COMMENT_MAXLENGTH)
    page = ser.CharField(read_only=True)
    new_mentions = ser.ListField(required=True, child=AuthorizedCharField(source='get_mentions'))
    old_mentions = ser.ListField(ser.CharField())

    target = TargetField(link_type='related', meta={'type': 'get_target_type'})
    user = RelationshipField(related_view='users:user-detail', related_view_kwargs={'user_id': '<user._id>'})
    node = RelationshipField(related_view='nodes:node-detail', related_view_kwargs={'node_id': '<node._id>'})
    replies = RelationshipField(self_view='nodes:node-comments', self_view_kwargs={'node_id': '<node._id>'}, filter={'target': '<pk>'})
    reports = RelationshipField(related_view='comments:comment-reports', related_view_kwargs={'comment_id': '<pk>'})

    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)
    modified = ser.BooleanField(read_only=True, default=False)
    deleted = ser.BooleanField(read_only=True, source='is_deleted', default=False)
    is_abuse = ser.SerializerMethodField(help_text='Whether the current user reported this comment.')
    has_children = ser.SerializerMethodField(help_text='Whether this comment has any replies.')
    can_edit = ser.SerializerMethodField(help_text='Whether the current user can edit this comment.')

    # LinksField.to_representation adds link to "self"
    links = LinksField({})

    class Meta:
        type_ = 'comments'

    def get_is_abuse(self, obj):
        user = self.context['request'].user
        if user.is_anonymous():
            return False
        return user._id in obj.reports and not obj.reports[user._id].get('retracted', True)

    def get_can_edit(self, obj):
        user = self.context['request'].user
        if user.is_anonymous():
            return False
        return obj.user._id == user._id and obj.node.can_comment(Auth(user))

    def get_has_children(self, obj):
        return Comment.find(Q('target', 'eq', Guid.load(obj._id))).count() > 0

    def get_absolute_url(self, obj):
        return absolute_reverse('comments:comment-detail', kwargs={'comment_id': obj._id})
        # return self.data.get_absolute_url()

    def update(self, comment, validated_data):
        assert isinstance(comment, Comment), 'comment must be a Comment'
        auth = Auth(self.context['request'].user)
        if validated_data:
            if validated_data.get('is_deleted', None) is False and comment.is_deleted:
                try:
                    comment.undelete(auth, save=True)
                except PermissionsError:
                    raise PermissionDenied('Not authorized to undelete this comment.')
            elif 'get_content' in validated_data:
                content = validated_data.pop('get_content')
                try:
                    comment.edit(content, auth=auth, save=True)
                except PermissionsError:
                    raise PermissionDenied('Not authorized to edit this comment.')
        return comment

    def get_target_type(self, obj):
        if isinstance(obj.referent, Node):
            return 'nodes'
        elif isinstance(obj.referent, Comment):
            return 'comments'
        elif isinstance(obj.referent, StoredFileNode):
            return 'files'
        else:
            raise InvalidModelValueError(
                source={'pointer': '/data/relationships/target/links/related/meta/type'},
                detail='Invalid comment target type.'
            )

    def sanitize_data(self):
        ret = super(CommentSerializer, self).sanitize_data()
        content = self.validated_data.get('get_content', None)
        if content:
            ret['get_content'] = bleach.clean(content)
        return ret


class CommentCreateSerializer(CommentSerializer):

    target_type = ser.SerializerMethodField(method_name='get_validated_target_type')

    def get_validated_target_type(self, obj):
        target = obj.target
        target_type = self.context['request'].data.get('target_type')
        expected_target_type = self.get_target_type(target)
        if target_type != expected_target_type:
            raise Conflict('Invalid target type. Expected "{0}", got "{1}."'.format(expected_target_type, target_type))
        return target_type

    def get_target(self, node_id, target_id):
        target = Guid.load(target_id)
        if not target:
            raise ValueError('Invalid comment target.')

        referent = target.referent

        if isinstance(referent, Node):
            if node_id != target_id:
                raise ValueError('Cannot post comment to another node.')
        elif isinstance(referent, Comment):
            if referent.node._id != node_id:
                raise ValueError('Cannot post reply to comment on another node.')
        elif isinstance(referent, StoredFileNode):
            if referent.provider not in osf_settings.ADDONS_COMMENTABLE:
                raise ValueError('Comments are not supported for this file provider.')
            elif referent.node._id != node_id:
                raise ValueError('Cannot post comment to file on another node.')
        else:
            raise ValueError('Invalid comment target.')

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
                detail='Invalid comment target \'{}\'.'.format(target_id)
            )
        validated_data['target'] = target
        validated_data['content'] = validated_data.pop('get_content')

        try:
            comment = Comment.create(auth=auth, **validated_data)
        except PermissionsError:
            raise PermissionDenied('Not authorized to comment on this project.')
        return comment


class CommentDetailSerializer(CommentSerializer):
    """
    Overrides CommentSerializer to make id required.
    """
    id = IDField(source='_id', required=True)
    deleted = ser.BooleanField(source='is_deleted', required=True)


class CommentReportSerializer(JSONAPISerializer):
    id = IDField(source='_id', read_only=True)
    type = TypeField()
    category = ser.ChoiceField(choices=[('spam', 'Spam or advertising'),
                                        ('hate', 'Hate speech'),
                                        ('violence', 'Violence or harmful behavior')], required=True)
    message = ser.CharField(source='text', required=False, allow_blank=True)
    links = LinksField({'self': 'get_absolute_url'})

    class Meta:
        type_ = 'comment_reports'

    def get_absolute_url(self, obj):
        comment_id = self.context['request'].parser_context['kwargs']['comment_id']
        return absolute_reverse(
            'comments:report-detail',
            kwargs={
                'comment_id': comment_id,
                'user_id': obj._id
            }
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
