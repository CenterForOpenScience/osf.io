from rest_framework import serializers as ser
from api.base.serializers import JSONAPISerializer, JSONAPIHyperlinkedRelatedField


class CommentSerializer(JSONAPISerializer):
    id = ser.CharField(read_only=True, source='_id')
    content = ser.CharField()
    user = JSONAPIHyperlinkedRelatedField(view_name='users:user-detail', lookup_field='pk', lookup_url_kwarg='user_id', link_type='related', read_only=True)
    node = JSONAPIHyperlinkedRelatedField(view_name='nodes:node-detail', lookup_field='pk', lookup_url_kwarg='node_id', link_type='related', read_only=True)
    # target hyperlink (either node or comment)

    date_created = ser.DateTimeField(read_only=True)  # auto_now_add=datetime.utcnow
    date_modified = ser.DateTimeField(read_only=True)  # auto_now_add=datetime.utcnow
    modified = ser.BooleanField(read_only=True)
    deleted = ser.BooleanField(source='is_deleted', default=False)

    # add reports as a hyperlinked field instead of a dictionary

    class Meta:
        type_ = 'comments'
