from datetime import datetime
from rest_framework import serializers as ser
from framework.guid.model import Guid
from framework.auth.core import Auth
from website.project.model import Node, Comment
from rest_framework.exceptions import ValidationError, PermissionDenied
from api.base.utils import absolute_reverse
from api.base.serializers import (JSONAPISerializer,
                                  JSONAPIHyperlinkedRelatedField,
                                  JSONAPIHyperlinkedGuidRelatedField,
                                  JSONAPIHyperlinkedIdentityField,
                                  IDField, TypeField, LinksField)


class CommentReport():
    def __init__(self, user_id, category, text):
        self._id = user_id
        self.category = category
        self.text = text


class CommentSerializer(JSONAPISerializer):

    filterable_fields = frozenset([
        'deleted'
    ])

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    content = ser.CharField()

    user = JSONAPIHyperlinkedRelatedField(view_name='users:user-detail', lookup_field='pk', lookup_url_kwarg='user_id', link_type='related', read_only=True)
    node = JSONAPIHyperlinkedRelatedField(view_name='nodes:node-detail', lookup_field='pk', lookup_url_kwarg='node_id', link_type='related', read_only=True)
    target = JSONAPIHyperlinkedGuidRelatedField(link_type='related', meta={'type': 'get_target_type'})
    replies = JSONAPIHyperlinkedIdentityField(view_name='comments:comment-replies', lookup_field='pk', link_type='self', lookup_url_kwarg='comment_id')
    reports = JSONAPIHyperlinkedIdentityField(view_name='comments:comment-reports', lookup_field='pk', lookup_url_kwarg='comment_id', link_type='related', read_only=True)

    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)
    modified = ser.BooleanField(read_only=True, default=False)
    deleted = ser.BooleanField(read_only=True, source='is_deleted', default=False)

    # LinksField.to_representation adds link to "self"
    links = LinksField({})

    class Meta:
        type_ = 'comments'

    def create(self, validated_data):
        user = self.context['request'].user
        node_id = self.context['view'].kwargs.get('node_id', None)
        target_id = self.context['view'].kwargs.get('comment_id', None)

        if node_id:
            node = self.context['view'].get_node()
            target = node
        elif target_id:
            target = Comment.load(target_id)
            node = target.node

        validated_data['user'] = user
        validated_data['node'] = node
        validated_data['target'] = target
        now = datetime.utcnow()
        validated_data['date_created'] = now
        validated_data['date_modified'] = now

        if node.can_comment(Auth(user)):
            comment = Comment(**validated_data)
            comment.save()
        else:
            raise PermissionDenied("Not authorized to comment on this project.")

        return comment

    def update(self, comment, validated_data):
        assert isinstance(comment, Comment), 'comment must be a Comment'
        auth = Auth(self.context['request'].user)
        if validated_data:
            if validated_data.get('content', None):
                comment.edit(validated_data['content'], auth=auth, save=True)
            is_deleted = validated_data.get('is_deleted', None)
            if is_deleted:
                comment.delete(auth, save=True)
            elif comment.is_deleted:
                comment.undelete(auth, save=True)
        return comment

    def get_target_type(self, obj):
        target_id = obj._id
        target = Guid.load(target_id).referent
        if isinstance(target, Node):
            return 'node'
        elif isinstance(target, Comment):
            return 'comment'


class CommentDetailSerializer(CommentSerializer):
    """
    Overrides CommentSerializer to make id required.
    """
    id = IDField(source='_id', required=True)
    deleted = ser.BooleanField(source='is_deleted', required=True)


class CommentReportsSerializer(JSONAPISerializer):
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


class CommentReportDetailSerializer(CommentReportsSerializer):
    """
    Overrides CommentReportSerializer to make id required.
    """
    id = IDField(source='_id', required=True)
