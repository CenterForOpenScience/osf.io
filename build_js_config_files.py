from os import path
import json


def run():
    from website import settings
    print('Building JS config files...')
    with open(path.join(settings.STATIC_FOLDER, 'built', 'nodeCategories.json'), 'w') as fp:
        json.dump(settings.NODE_CATEGORY_MAP, fp)
    print('...Done.')


if __name__ == '__main__':
    run()
