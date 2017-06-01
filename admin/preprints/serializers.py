from admin.nodes.serializers import serialize_node


def serialize_preprint(preprint):

    return {
        'id': preprint._id,
        'date_created': preprint.date_created,
        'modified': preprint.date_modified,
        'provider': preprint.provider,
        'node': serialize_node(preprint.node),
        'is_published': preprint.is_published,
        'date_published': preprint.date_published,
        'subjects': serialize_subjects(preprint.subject_hierarchy),
    }


def serialize_subjects(subject_hierarchy):
    return [{'id': subject._id, 'text': subject.text} for subjects in subject_hierarchy for subject in subjects]
