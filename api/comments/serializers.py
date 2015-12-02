from rest_framework import serializers as ser
from framework.auth.core import Auth
from website.project.model import Comment, Node
from rest_framework.exceptions import ValidationError, PermissionDenied
from api.base.exceptions import InvalidModelValueError, Conflict
from api.base.utils import absolute_reverse
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
        'date_modified'
    ])

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    content = AuthorizedCharField(source='get_content')

    target = TargetField(link_type='related', meta={'type': 'get_target_type'})
    user = RelationshipField(related_view='users:user-detail', related_view_kwargs={'user_id': '<user._id>'})
    node = RelationshipField(related_view='nodes:node-detail', related_view_kwargs={'node_id': '<node._id>'})
    replies = RelationshipField(self_view='comments:comment-replies', self_view_kwargs={'comment_id': '<pk>'})
    reports = RelationshipField(related_view='comments:comment-reports', related_view_kwargs={'comment_id': '<pk>'})

    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)
    modified = ser.BooleanField(read_only=True, default=False)
    deleted = ser.BooleanField(read_only=True, source='is_deleted', default=False)

    # LinksField.to_representation adds link to "self"
    links = LinksField({})

    class Meta:
        type_ = 'comments'

    def update(self, comment, validated_data):
        assert isinstance(comment, Comment), 'comment must be a Comment'
        auth = Auth(self.context['request'].user)
        if validated_data:
            if 'get_content' in validated_data:
                comment.edit(validated_data['get_content'], auth=auth, save=True)
            if validated_data.get('is_deleted', None) is True:
                comment.delete(auth, save=True)
            elif comment.is_deleted:
                comment.undelete(auth, save=True)
        return comment

    def get_target_type(self, obj):
        if isinstance(obj, Node):
            return 'nodes'
        elif isinstance(obj, Comment):
            return 'comments'
        else:
            raise InvalidModelValueError('Invalid comment target.')


class CommentCreateSerializer(CommentSerializer):

    target_type = ser.SerializerMethodField(method_name='get_validated_target_type')

    def get_validated_target_type(self, obj):
        target = obj.target
        target_type = self.context['request'].data.get('target_type')
        expected_target_type = self.get_target_type(target)
        if target_type != expected_target_type:
            raise Conflict()
        return target_type

    def get_target(self, node_id, target_id):
        node = Node.load(target_id)
        if node and node_id != target_id:
            raise ValueError('Cannot post comment to another node.')
        elif target_id == node_id:
            return Node.load(node_id)
        else:
            comment = Comment.load(target_id)
            if comment:
                return comment
            else:
                raise ValueError

    def create(self, validated_data):
        user = validated_data['user']
        auth = Auth(user)
        node = validated_data['node']

        try:
            target = self.get_target(node._id, self.context['request'].data.get('id'))
        except ValueError:
            raise InvalidModelValueError('Invalid target.')

        validated_data['target'] = target
        validated_data['content'] = validated_data.pop('get_content')
        if node and node.can_comment(auth):
            comment = Comment.create(auth=auth, **validated_data)
        else:
            raise PermissionDenied("Not authorized to comment on this project.")
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
        if user._id in comment.reports:
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
