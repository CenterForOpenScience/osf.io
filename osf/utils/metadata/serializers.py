serializer_registry = {}

def register(schema_id):
    """Register classes into serializer_registry"""
    # TODO: validate schema_id here?
    def decorator(cls):
        serializer_registry[schema_id] = cls
        return cls
    return decorator


class SchemaSerializer(object):

    def serialize_json(self, metadata_record):
        raise NotImplementedError

    def serialize_xml(self, metadata_record):
        raise NotImplementedError

    def serialize(self, metadata_record, format='json'):
        if format == 'json':
            self.serialize_json(metadata_record)
        elif format == 'xml':
            self.serialize_xml(metadata_record)


@register(schema_id='datacite')
class DataciteMetadataSerializer(SchemaSerializer):

    def serialize_json(self, metadata_record):
        # Some sort of serialization like:
        # https://github.com/CenterForOpenScience/osf.io/pull/8354/files#diff-c27a325cb74cc23fa575bd376c86662aR55
        # ?
        pass

@register(schema_id='crossref')
class CrossrefMetadataSerializer(SchemaSerializer):

    def serialize_json(self, metadata_record):
        # Some sort of serialization like:
        # https://github.com/CenterForOpenScience/osf.io/pull/8354/files#diff-c27a325cb74cc23fa575bd376c86662aR55
        # ?
        pass
