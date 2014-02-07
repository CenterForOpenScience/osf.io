from nodefilecollector import NodeFileCollector


def to_hgrid(node, auth, mode, **data):
    return NodeFileCollector(node, auth, **data)(mode)
