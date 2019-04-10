from api.files.serializers import (
    BaseFileSerializer,
    RelationshipField,
    LinksField,
    Link,
    WaterbutlerLink,
    IDField
)


class QuickFilesSerializer(BaseFileSerializer):
    user = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<target._id>'},
        help_text='The user who uploaded this file',
    )


class UserQuickFilesSerializer(QuickFilesSerializer):
    links = LinksField({
        'info': Link('files:file-detail', kwargs={'file_id': '<_id>'}),
        'upload': WaterbutlerLink(),
        'delete': WaterbutlerLink(),
        'move': WaterbutlerLink(),
        'download': WaterbutlerLink(must_be_file=True),
    })


class QuickFilesDetailSerializer(QuickFilesSerializer):
    id = IDField(source='_id', required=True)
