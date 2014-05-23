import solr_search
# TODO
# Abstracts search away from solr
def search(query, start=0):
    return solr_search.search(query, start=0)
