from website.settings import DRAFT_REGISTRATION_AUTHORIZERS as authorizers


def members_for(group):
    global_members = authorizers['global']
    return global_members | set(authorizers.get(group, []))
