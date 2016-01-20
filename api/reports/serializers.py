from rest_framework import serializers as ser
from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from website.project.model import Comment, Node
from rest_framework.exceptions import ValidationError, PermissionDenied
from api.base.exceptions import InvalidModelValueError, Conflict
from api.base.utils import absolute_reverse
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
        if user._id in comment.reports and not comment.reports[user._id]['retracted']:
            raise ValidationError('Comment already reported.')
        try:
            comment.report_spam(user, save=True, **validated_data)
        except ValueError:
            raise ValidationError('You cannot report your own comment.')
        return CommentReport(user._id, **validated_data)

    def update(self, comment_report, validated_data):
        user = self.context['request'].user
        comment = self.context['view'].get_comment()
        if user._id != comment_report._id:
            raise ValidationError('You cannot report a comment on behalf of another user.')
        try:
            comment.report_spam(user, save=True, **validated_data)
        except ValueError:
            raise ValidationError('You cannot report your own comment.')
        return CommentReport(user._id, **validated_data)


class CommentReportDetailSerializer(CommentReportSerializer):
    """
    Overrides CommentReportSerializer to make id required.
    """
    id = IDField(source='_id', required=True)