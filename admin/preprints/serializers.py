from website.project.taxonomies import Subject
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
        'subjects': serialize_subjects(preprint.subjects),
    }


def serialize_subjects(subjects):
    serialized_subjects = []
    for subject in subjects:
        if len(subject) == 1:
            subject = Subject.load(subject[0])
            if subject:
                serialized_subjects.append({
                    'id': subject._id,
                    'text': subject.text
                })
    return serialized_subjects
