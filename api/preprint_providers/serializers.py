from rest_framework import serializers as ser
from api.base.serializers import ShowIfVersion
from api.providers.serializers import PreprintProviderSerializer
from osf.models import PreprintProvider


class DeprecatedPreprintProviderSerializer(PreprintProviderSerializer):
    class Meta:
        type_ = 'preprint_providers'

    # Deprecated fields
    header_text = ShowIfVersion(
        ser.CharField(read_only=True, default=''),
        min_version='2.0', max_version='2.3',
    )
    banner_path = ShowIfVersion(
        ser.CharField(read_only=True, default=''),
        min_version='2.0', max_version='2.3',
    )
    logo_path = ShowIfVersion(
        ser.CharField(read_only=True, default=''),
        min_version='2.0', max_version='2.3',
    )
    email_contact = ShowIfVersion(
        ser.CharField(read_only=True, allow_null=True),
        min_version='2.0', max_version='2.3',
    )
    social_twitter = ShowIfVersion(
        ser.CharField(read_only=True, allow_null=True),
        min_version='2.0', max_version='2.3',
    )
    social_facebook = ShowIfVersion(
        ser.CharField(read_only=True, allow_null=True),
        min_version='2.0', max_version='2.3',
    )
    social_instagram = ShowIfVersion(
        ser.CharField(read_only=True, allow_null=True),
        min_version='2.0', max_version='2.3',
    )
    subjects_acceptable = ShowIfVersion(
        ser.ListField(read_only=True, default=[]),
        min_version='2.0', max_version='2.4',
    )

class PreprintProviderCitationStylesSerializer(ser.ModelSerializer):
    """
    Serializer for citation styles associated with a PreprintProvider.

    This serializer fetches and formats the citation styles supported by a specific PreprintProvider.
    """
    supported_citation_styles = ser.StringRelatedField(many=True)

    class Meta:
        """
        Meta class for PreprintProviderCitationStylesSerializer.

        Specifies the model and fields to be serialized.
        """
        model = PreprintProvider
        fields = ['id', 'citation_styles']
