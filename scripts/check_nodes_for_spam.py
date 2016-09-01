import argparse
import random
from modularodm import Q

from website.app import init_app
from website.project import spam, model
from website.search.elastic_search import serialize_node, get_doctype_from_node


parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-n', '--number', type=int, default=200,
                    help='Number of nodes to look at. Uses N most recent nodes.')

def generate_ip():
    ip_ranges = zip(
        (1, 6, 0, 0),
        (1, 7, 255, 255)
    )
    return '.'.join(map(lambda p: str(random.randint(*p)), ip_ranges))

def check_nodes(num_nodes, flag=False):
    nodes = model.Node.find(Q(
        'is_registration', 'eq', False
    )).sort('-date_created').limit(num_nodes)
    for node in nodes:
        serialized = serialize_node(node, get_doctype_from_node(node))
        spam.check_node_for_spam(
            serialized,
            node.creator,
            {
                'Remote-Addr': generate_ip(),
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'
            }          
        )

def main():
    args = parser.parse_args()
    init_app(routes=False)    
    check_nodes(args.number)


main() if __name__ == '__main__' else None
