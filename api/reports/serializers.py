from rest_framework import serializers as ser
from rest_framework.exceptions import ValidationError
from api.base.utils import absolute_reverse
from api.base.serializers import (JSONAPISerializer,
                                  IDField, TypeField, LinksField)


class Report(object):
    def __init__(self, user_id, category, text):
        self._id = user_id
        self.category = category
        self.text = text


class ReportSerializer(JSONAPISerializer):
    id = IDField(source='_id', read_only=True)
    type = TypeField()
    status = ser.ChoiceField(choices=[(0, 'unknown'),
                                      (1, 'flagged',
                                       2, 'spam',
                                       4, 'ham')],
                             required=False, read_only=True)
    category = ser.ChoiceField(choices=[('spam', 'Spam or advertising'),
                                        ('hate', 'Hate speech'),
                                        ('violence', 'Violence or harmful behavior')], required=True)
    message = ser.CharField(source='text', required=False, allow_blank=True)
    links = LinksField({'self': 'get_absolute_url'})

    class Meta:
        type_ = 'reports'

    def get_absolute_url(self, obj):
        object_id = self.context['request'].parser_context['kwargs']['comment_id']
        return absolute_reverse(
            'comments:report-detail',
            kwargs={
                'comment_id': object_id,
                'user_id': obj._id
            }
        )

    def create(self, validated_data):
        user = self.context['request'].user
        item = self.context['view'].get_comment()
        if user._id in item.reports and not item.reports[user._id]['retracted']:
            raise ValidationError('Comment already reported.')
        try:
            item.report_spam(user, save=True, **validated_data)
        except ValueError:
            raise ValidationError('You cannot report your own comment.')
        return Report(user._id, **validated_data)

    def update(self, report, validated_data):
        user = self.context['request'].user
        item = self.context['view'].get_comment()
        if user._id != report._id:
            raise ValidationError('You cannot report a comment on behalf of another user.')
        try:
            item.report_spam(user, save=True, **validated_data)
        except ValueError:
            raise ValidationError('You cannot report your own comment.')
        return Report(user._id, **validated_data)


class ReportDetailSerializer(ReportSerializer):
    """
    Overrides CommentReportSerializer to make id required.
    """
    id = IDField(source='_id', required=True)