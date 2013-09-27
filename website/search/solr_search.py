import urllib
import urllib2
import ast

from website import settings


def search_solr(query, start=0):
    # here is our query. the default search field is text which maps to tags,
    # description, wiki, and title
    # start is for our pagination
    query_args = {
        'q': query + ' AND public:true',
        'hl.query': query, 'hl': 'true', 'hl.fl': '*',
        'hl.fragsize': '100', 'hl.snippets': '10',
        'hl.preserveMulti': 'true',
        'spellcheck': 'true', 'spellcheck.collate': 'true',
        'start': start, 'rows': 10}
    encoded_args = urllib.urlencode(query_args)
    url = '{}spell?{}&wt=python'.format(settings.solr, encoded_args)
    # post to the url
    solrReq = urllib2.Request(url)
    solrReq.add_header('Content-Type', 'application/json')
    solrPost = urllib2.urlopen(solrReq)
    # get our result
    result = ast.literal_eval(solrPost.read())
    # spellcheck (if there is one)
    spellcheck = result['spellcheck']['suggestions'] \
        if 'spellcheck' in result else None
    # highlight
    highlight = result['highlighting']
    # and the list of documents
    result = result['response']
    # look for specllcheck,
    # dont return that public_project was part of the query to the user
    if spellcheck:
        # need to strip out the AND
        # so users dont see that we are searching for AND public:true!
        spellcheck_result = spellcheck[-1].split(' AND')[0]
    else:
        spellcheck_result = None
    solrPost.close()
    return result, highlight, spellcheck_result