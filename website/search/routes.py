from framework import *
from website.project import Node

import time

import logging; logging.basicConfig(level=logging.DEBUG); 
logger = logging.getLogger('search.routes')

@get('/search/')
def search_search():
	tick = time.time()
	query = request.args.get('q')
	results = search(Node, query)
	return render(filename='search.mako', results=results, total=len(results), time=round(time.time()-tick, 2))