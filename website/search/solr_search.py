import urllib
import urllib2
import ast

from website import settings


def search(query, start=0):
    # here is our query. the default search field is text which maps to tags,
    # description, wiki, and title
    # start is for our pagination
    query_args = {
        'q': query,
        'hl.query': query, 'hl': 'true', 'hl.fl': '*',
        'hl.fragsize': '100', 'hl.snippets': '10',
        'hl.preserveMulti': 'true',
        'spellcheck': 'true', 'spellcheck.collate': 'true',
        'start': start, 'rows': 10}
    encoded_args = urllib.urlencode(_encoded_dict(query_args))
    url = '{}spell?{}&wt=python'.format(settings.SOLR_URI, encoded_args)
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
        spellcheck_result = spellcheck[-1]
    else:
        spellcheck_result = None
    solrPost.close()
    return result, highlight, spellcheck_result

def _encoded_dict(in_dict):
    out_dict = {}
    for k, v in in_dict.iteritems():
        if isinstance(v, unicode):
            v = v.encode('utf8')
        elif isinstance(v, str):
            # Must be encoded in UTF-8
            v.decode('utf8')
        out_dict[k] = v
    return out_dict
