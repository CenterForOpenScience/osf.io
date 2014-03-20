from model import Badge


def is_valid_badge(badge):
    pass


#TODO Clean with bleach
def build_badge(issuer, badge):
    new = Badge()
    new.creator = issuer
    new.name = badge['badgeName']
    new.description = badge['description']
    new.image = badge['imageurl']
    new.criteria = badge['criteria']
    new.issuer_url = issuer.site_url
    #TODO alignment and tags
    new.save()
    return new._id


def load_badge(id):
    pass


def build_assertion(issuer, badge):
    pass
