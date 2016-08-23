# -*- coding: utf-8 -*-

import os
import sys
from tabulate import tabulate

from framework.mongo import database
from website import settings
from website.addons.wiki import settings as wiki_settings

from .utils import mkdirp

wiki_collection = database['nodewikipage']
node_collection = database['node']

TAB_PATH = os.path.join(settings.ANALYTICS_PATH, 'tables', 'features')
mkdirp(TAB_PATH)

def get_wiki_counts():

    query_legacy = {'date': {'$lt': wiki_settings.WIKI_CHANGE_DATE}}
    wikis_legacy = wiki_collection.find(query_legacy)

    totals = {'pub_proj': {'total': 0, 'total_size': 0, 'largest': 0},
              'pub_reg': {'total': 0, 'total_size': 0, 'largest': 0},
              'priv_proj': {'total': 0, 'total_size': 0, 'largest': 0},
              'priv_reg': {'total': 0, 'total_size': 0, 'largest': 0},
              'orphaned': {'total': 0, 'total_size': 0, 'largest': 0},
              'gone': {'total': 0, 'total_size': 0, 'largest': 0}}

    metadata = {}
    for entry in wikis_legacy:
        node = entry.get('node')
        page_name = entry.get('page_name')
        size = sys.getsizeof(entry.get('content'))
        if not node in metadata.keys():
            node_meta = node_collection.find_one({'_id': node})
            # node refered to by wiki.node may no longer exist
            if node_meta == None:
                metadata.update({node: {'current': {page_name: 'unknown'},
                                        'node_type': 'gone'}})
                totals['gone']['total'] = totals['gone']['total'] + 1
            else:
                node_meta = node_collection.find_one({'_id': node})
                if node_meta['is_public']:
                    if node_meta['is_registration']:
                        node_type = 'pub_reg'
                    else:
                        node_type = 'pub_proj'
                elif node_meta['is_registration']:
                    node_type = 'priv_reg'
                else:
                    node_type = 'priv_proj'
                metadata.update({node: {'current':
                                              node_meta['wiki_pages_current'],
                                        'node_type': node_type}})
                node_type = metadata[node]['node_type']
                try:
                    if entry.get('_id') == metadata[node]['current'][page_name]:
                        totals[node_type]['total'] = totals[node_type]['total'] + 1
                        totals[node_type]['total_size'] = totals[node_type]['total_size'] + size
                        if size > totals[node_type]['largest']:
                            totals[node_type]['largest'] = size
                except KeyError:
                # node may not have a reference to wiki.page_name 'current'
                    metadata[node]['current'].update({page_name: 'unknown'})
                    totals['orphaned']['total'] = totals['orphaned']['total'] + 1

        elif metadata[node]['node_type'] == 'gone':
            if page_name not in metadata[node]['current'].keys():
                metadata[node]['current'].update({page_name: 'unknown'})
                totals[node_type]['total'] = totals[node_type]['total'] + 1
        else:
            if not entry.get('_id') == metadata[node]['current'][page_name]:
                continue
            totals[node_type]['total'] = totals[node_type]['total'] + 1
            totals[node_type]['total_size'] = totals[node_type]['total_size'] + size
            if size > totals[node_type]['largest']:
                totals[node_type]['largest'] = size


    for key in totals.keys():
        if not key == 'gone':
            try:
                totals[key]['average'] = (totals[key]['total_size'] /
                                          totals[key]['total'])
            except ZeroDivisionError:
                totals[key]['average'] = 0
    return totals


def main():

    counts = get_wiki_counts()
    table_data = [ ['pub_proj', counts['pub_proj']['total'],
                    counts['pub_proj']['total_size'],
                    counts['pub_proj']['average'],
                    counts['pub_proj']['largest']],
                   ['pub_reg', counts['pub_reg']['total'],
                    counts['pub_reg']['total_size'],
                    counts['pub_reg']['average'],
                    counts['pub_reg']['largest']],
                   ['priv_proj', counts['priv_proj']['total'],
                    counts['priv_proj']['total_size'],
                    counts['priv_proj']['average'],
                    counts['priv_proj']['largest']],
                   ['priv_reg', counts['priv_reg']['total'],
                    counts['priv_reg']['total_size'],
                    counts['priv_reg']['average'],
                    counts['priv_reg']['largest']],
                   ['orphaned', counts['orphaned']['total'], None, None, None],
                   ['node gone', counts['gone']['total'], None, None, None]]

    table = tabulate( table_data, headers=['node type', 'total', 'total size',
                                           'average size', 'largest'] )

    with open(os.path.join(TAB_PATH, 'legacy_wikis.txt'), 'w') as fp:
        fp.write('Data for current wikis\n\n')
        fp.write('Orphaned means that the node the wiki refers to does not refer back to the wiki in the "current" field\n\n')
        fp.write('Node gone means that the node the wiki refers to no longer exists\n\n')
        fp.write(table)
        fp.write('\n')


if __name__ == '__main__':
    main()

