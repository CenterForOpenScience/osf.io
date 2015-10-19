from website.project.model import Comment


def serialize_comments():
    return [c.content for c in Comment.find()]
