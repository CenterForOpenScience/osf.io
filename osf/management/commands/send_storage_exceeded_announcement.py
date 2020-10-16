import logging
import json
from tqdm import tqdm

from website import mails
from django.core.management.base import BaseCommand

from osf.models import Node, OSFUser

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def obj_gen(targets):
    for u_id, n_dict in targets.items():
        try:
            u = OSFUser.load(u_id)
            priv = [n for n in [Node.load(n_id) for n_id in n_dict.get('private', [])] if not n.is_public]
            pub = []
            for n_id in n_dict.get('public', []):
                # Add previously-public nodes to private list, as 50>5.
                # Do not do the reverse.
                n = Node.load(n_id)
                if n.is_public:
                    pub.append(n)
                else:
                    priv.append(n)
            yield u, pub, priv
        except Exception:
            logger.error(f'Unknown exception handling {u_id}, skipping')

def main(json_file, dry=False):
    if not json_file:
        logger.info('No file detected, exiting.')
        return
    targets = json.load(json_file)
    errors = []
    p_bar = tqdm(total=len(targets))
    for user, public_nodes, private_nodes in obj_gen(targets):
        if public_nodes or private_nodes:
            if not dry:
                try:
                    mails.send_mail(
                        to_addr=user.username,
                        mail=mails.STORAGE_CAP_EXCEEDED_ANNOUNCEMENT,
                        user=user,
                        public_nodes=public_nodes,
                        private_nodes=private_nodes,
                        can_change_preferences=False,
                    )
                except Exception:
                    errors.append(user._id)
            else:
                logger.info(f'[Dry] Would mail {user._id}')
        p_bar.update()
    p_bar.close()
    logger.info(f'Complete. Errors mailing: {errors}')

class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            dest='dry',
            action='store_true',
            help='Dry run'
        )
        parser.add_argument(
            '--json',
            dest='json_file',
            type=open,
            help='Path of the json input',
        )

    def handle(self, *args, **options):
        json_file = options.get('json_file', None)
        dry = options.get('dry', None)
        main(json_file, dry)
