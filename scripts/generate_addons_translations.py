#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate message resources for i18n.
scripts/translations/messages_addonsJson.js - Description about permissions of addons
"""

import os
import pathlib

from website.app import setup_django, init_addons
from website import settings

def main():
    scripts_path = pathlib.Path(__file__).parent.absolute()
    json_path = os.path.join(scripts_path, 'translations', 'messages_addonsJson.js')
    print(json_path)

    setup_django()
    init_addons(settings)
    with open(json_path, 'w') as f:
        f.write('var _ = require(\'js/rdmGettext\')._;\n\n')
        for addon in settings.ADDONS_AVAILABLE:
            if addon.short_name not in settings.ADDON_CAPABILITIES:
                print('Skipped - {}'.format(addon.short_name))
                continue
            print('Found the description - {}'.format(addon.short_name))
            message = settings.ADDON_CAPABILITIES[addon.short_name]
            message = message.replace('\n', '\\n')
            message = message.replace('\'', '\\\'')
            f.write('var addonTerms_{} = _(\'{}\');\n\n'.format(addon.short_name, message))
    print('Generated: {}'.format(json_path))

if __name__ == '__main__':
    main()
