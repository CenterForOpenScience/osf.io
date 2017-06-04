# -*- coding: utf-8 -*-
"""Ensure all projects have a Piwik node."""
import logging
import sys


from scripts import utils as scripts_utils
from website.app import init_app
from website.conferences.model import Conference, DEFAULT_FIELD_NAMES


logger = logging.getLogger(__name__)

def main():
    init_app(set_backends=True, routes=False)
    dry = '--dry' in sys.argv
    if not dry:
        scripts_utils.add_file_logger(logger, __file__)

    for conf in Conference.find():
        if not conf.field_names.get('homepage_link_text'):
            logger.info('Setting conference {} field_names["homepage_link_text"] to default value: {}'.format(conf.endpoint, DEFAULT_FIELD_NAMES['homepage_link_text']))
            conf.field_names['homepage_link_text'] = DEFAULT_FIELD_NAMES['homepage_link_text']
            if not dry:
                conf.save()
    logger.info('Done.')


if __name__ == '__main__':
    main()
