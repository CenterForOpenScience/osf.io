from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer


class CommentSerializer(JSONAPISerializer):
    id = ser.CharField(read_only=True, source='_id')

    class Meta:
        type_ = 'comments'
