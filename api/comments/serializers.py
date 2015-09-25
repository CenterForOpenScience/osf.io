from datetime import datetime
from rest_framework import serializers as ser
from website.project.model import Node, Comment
from api.base.serializers import JSONAPISerializer, JSONAPIHyperlinkedRelatedField, JSONAPIHyperlinkedIdentityField, IDField, TypeField


class CommentSerializer(JSONAPISerializer):
    id = IDField(source='_id', read_only=True)
    target_id = ser.SerializerMethodField()
    type = TypeField()
    content = ser.CharField()
    user = JSONAPIHyperlinkedRelatedField(view_name='users:user-detail', lookup_field='pk', lookup_url_kwarg='user_id', link_type='related', read_only=True)
    node = JSONAPIHyperlinkedRelatedField(view_name='nodes:node-detail', lookup_field='pk', lookup_url_kwarg='node_id', link_type='related', read_only=True)
    # target = JSONAPIHyperlinkedRelatedField()

    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)
    modified = ser.BooleanField(read_only=True, default=False)
    deleted = ser.BooleanField(read_only=True, source='is_deleted', default=False)

    # add reports as a hyperlinked field instead of a dictionary

    class Meta:
        type_ = 'comments'

    def create(self, validated_data):
        node = self.context['view'].get_node()
        validated_data['user'] = self.context['request'].user
        validated_data['node'] = node
        validated_data['id'] = node._id
        validated_data['target'] = self.get_target(validated_data['target_id'], node)
        now = datetime.utcnow()
        validated_data['date_created'] = now
        validated_data['date_modified'] = now

        comment = Comment(**validated_data)
        comment.save()

        return comment

    def get_target(self, target_id, node):
        if target_id == node._id:
            return node
        else:
            return Comment.load(target_id)

    def get_target_id(self, data):
        return data.target._id
