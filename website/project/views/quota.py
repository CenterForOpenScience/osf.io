from website.project.decorators import must_be_contributor_or_public


@must_be_contributor_or_public
def creator_quota(auth, node, **kwargs):
    return {'status': 'ok'}
