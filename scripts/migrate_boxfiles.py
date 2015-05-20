import logging
from website.app import init_app
from website.addons.box.model import BoxFile
from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)


def main():
    for file in BoxFile.find():
        new_path = '/' + file.path.split('/')[1]
        logger.info(u'{} -> {}'.format(file.path, new_path))
        file.path = new_path
        file.save()


if __name__ == '__main__':
    scripts_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    main()
