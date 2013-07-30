import urllib
import urllib2
import ast
import sunburnt
solr = sunburnt.SolrInterface("http://localhost:8983/solr/")

def search_solr(query):
    if ':' in query:
        search_solr_advanced(query)
    query = 'text:' + query
    query_args = {
        'q': query, 'hl':'true', 'hl.fl':'*',
        'hl.fragsize':'500', 'hl.presevereMulti':'true',
        'spellcheck':'true', 'spellcheck.collate':'true'}
    encoded_args = urllib.urlencode(query_args)
    url = "http://localhost:8983/solr/spell?"+encoded_args+'&wt=python'
    print url
    solrReq = urllib2.Request(url)
    solrReq.add_header('Content-Type', 'application/json')
    solrPost = urllib2.urlopen(solrReq)
    result = ast.literal_eval(solrPost.read())
    spellcheck = result['spellcheck']['suggestions']
    print 'the spellcheck is', spellcheck
    highlight = result['highlighting']
    result = result['response']
    if spellcheck:
        spellcheck_result =  spellcheck[-1].split('text:')[1]
    else:
        spellcheck_result = None
    solrPost.close()
    print 'the highlight is', highlight
    return result, highlight, spellcheck_result

def search_solr_advanced(query):
    pass

