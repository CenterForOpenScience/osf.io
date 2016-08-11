from framework.auth.signals import user_confirmed
from website.exceptions import NodeStateError
from website.project.model import Node

@user_confirmed.connect
def give_user_public_files_node(user):

    if not user.is_registered:
        raise NodeStateError('Users must be registered to have a public files node')

    if user.public_files_node is not None:
        raise NodeStateError('Users may only have one public files node')

    node = Node(
        title='Public Files',
        creator=user,
        category='other',
        is_public=True,
        is_public_files_node=True,
    )

    node.save()

    return node
