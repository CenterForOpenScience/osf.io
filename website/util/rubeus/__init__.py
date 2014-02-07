from nodefilecollector import NodeFileCollector


def get_hgrid(node, auth, mode, **data):
    return NodeFileCollector(node, auth, **data)(mode)
