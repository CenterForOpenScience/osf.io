from framework.search.model import Keyword
from modularodm.query.querydialect import DefaultQueryDialect as Q

from topia.termextract import extract

import logging; logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('project.search')

def database_get_search_results(search_term, collection):
    return collection.find(
        Q('_terms.term', 'eq', search_term)
        & Q('is_public', 'eq', True)
        #'is_registration':False, 
        #'is_deleted':False
    )

def generate_keywords(fields):
    e = extract.TermExtractor()
    e.filter = extract.permissiveFilter
    words = {}
    for field in fields:
        if field:
            for i in e(field.lower()):
                if i[0] not in words:
                    words[i[0]] = i[1]
                else:
                    words[i[0]] += i[1]
    return [{'term':key, 'weight':value} for key, value in words.iteritems()]

def search(collection, text, page=1, term='_terms'):
    e = extract.TermExtractor()
    e.filter = extract.permissiveFilter
    results = {}
    weights = {}
    searchTerms = [i[0] for i in e(text.lower())]
    for i in searchTerms:
        for result in database_get_search_results(i, collection):
            tId = str(result._id)
            if tId not in results:
                results[tId] = result
                for tTermDict in result._terms:
                    tTerm = tTermDict['term']
                    tWeight = tTermDict['weight']
                    if tTerm in searchTerms:
                        if tId not in weights:
                            weights[tId] = tWeight
                        else:
                            weights[tId] += tWeight
    weights = [x for x in weights.iteritems()]
    weights.sort(key=lambda x: x[1])
    weights.reverse()
    sortedResults = []
    for key in [x[0] for x in weights]:
        sortedResults.append(results[key])
    return sortedResults