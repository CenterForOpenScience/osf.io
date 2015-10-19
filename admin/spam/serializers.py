from website.project.model import Comment
from modularodm import Q


def serialize_comments():
    query = Q('reports', 'size gte', '1')
    return [c.content for c in Comment.find(query)]
