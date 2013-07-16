from framework import *
from Site.Project import Node

import time

import logging; logging.basicConfig(level=logging.DEBUG); 
logger = logging.getLogger('Search.Routes')

@get('/search/')
def search_search():
	tick = time.time()
	query = request.args.get('q')
	results = search(Node, query)
	return render(filename='search.mako', results=results, total=len(results), time=round(time.time()-tick, 2))