from datetime import datetime
from rest_framework import serializers as ser
from framework.guid.model import Guid
from website.project.model import Node, Comment
from api.base.serializers import (JSONAPISerializer,
                                  JSONAPIHyperlinkedRelatedField,
                                  JSONAPIHyperlinkedGuidRelatedField,
                                  JSONAPIHyperlinkedIdentityField,
                                  IDField, TypeField)


class CommentSerializer(JSONAPISerializer):
    id = IDField(source='_id', read_only=True)
    type = TypeField()
    content = ser.CharField()

    user = JSONAPIHyperlinkedRelatedField(view_name='users:user-detail', lookup_field='pk', lookup_url_kwarg='user_id', link_type='related', read_only=True)
    node = JSONAPIHyperlinkedRelatedField(view_name='nodes:node-detail', lookup_field='pk', lookup_url_kwarg='node_id', link_type='related', read_only=True)
    target = JSONAPIHyperlinkedGuidRelatedField(link_type='related', meta={'type': 'get_target_type'})
    replies = JSONAPIHyperlinkedIdentityField(view_name='comments:comment-replies', lookup_field='pk', link_type='related', lookup_url_kwarg='comment_id')

    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)
    modified = ser.BooleanField(read_only=True, default=False)
    deleted = ser.BooleanField(read_only=True, source='is_deleted', default=False)

    # add reports as a hyperlinked field instead of a dictionary

    class Meta:
        type_ = 'comments'

    def create(self, validated_data):
        node_id = self.context['view'].kwargs.get('node_id', None)
        target_id = self.context['view'].kwargs.get('comment_id', None)

        if node_id:
            node = self.context['view'].get_node()
            target = node
        elif target_id:
            target = Comment.load(target_id)
            node = target.node

        validated_data['user'] = self.context['request'].user
        validated_data['node'] = node
        validated_data['target'] = target
        now = datetime.utcnow()
        validated_data['date_created'] = now
        validated_data['date_modified'] = now

        comment = Comment(**validated_data)
        comment.save()

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
