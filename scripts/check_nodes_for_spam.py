import argparse
from modularodm import Q

from website.app import init_app
from website.project import model
from website.project.spam.model import SpamStatus

parser = argparse.ArgumentParser()
parser.add_argument('-n', '--number', type=int, default=200,
                    help='Number of nodes to look at. Uses N most recent nodes.')
parser.add_argument('-f', '--flag', type=bool, default=False,
                    help='Actually flag nodes as spam?')


def check_nodes(num_nodes, flag=False):
    nodes = model.Node.find(
        Q('is_registration', 'eq', False) &
        Q('spam_status', 'ne', SpamStatus.FLAGGED) &
        Q('spam_status', 'ne', SpamStatus.SPAM)
    ).sort('-date_created').limit(num_nodes)
    for node in nodes:
        node.check_spam(
            ['is_public'],  # force check on all spam fields
            {  # must supply request headers or spam checking is ignored (always best to use original client headers for spam reporting)
                'Remote-Addr': '127.0.0.1',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36'
            }
        )

def main():
    args = parser.parse_args()
    init_app(routes=False)
    check_nodes(args.number, flag=args.flag)


main() if __name__ == '__main__' else None
