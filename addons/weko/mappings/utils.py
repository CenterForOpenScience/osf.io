LICENSE_DEFS = [
    {
        'text': 'CC0',
        'tooltip': 'CC0 1.0 Universal',
        'en': 'CC0 1.0 Universal',
        'url': 'https://creativecommons.org/publicdomain/zero/1.0/deed.en'
    },
    {
        'text': 'CCBY',
        'tooltip': 'CC BY 4.0 表示 国際|CC BY 4.0 Attribution International',
        'en': 'Creative Commons Attribution 4.0 International',
        'url': 'https://creativecommons.org/licenses/by/4.0/deed.en'
    },
    {
        'text': 'CCBYSA',
        'tooltip': 'CC BY-SA 4.0 表示—継承|CC BY-SA 4.0 Attribution-ShareAlike',
        'en': 'Creative Commons Attribution-ShareAlike 4.0 International',
        'url': 'https://creativecommons.org/licenses/by-sa/4.0/deed.en'
    },
    {
        'text': 'CCBYND',
        'tooltip': 'CC BY-ND 4.0 表示—改変禁止|CC BY-ND 4.0 Attribution—NoDerivatives',
        'en': 'Creative Commons Attribution-NoDerivatives 4.0 International',
        'url': 'https://creativecommons.org/licenses/by-nd/4.0/deed.en'
    },
    {
        'text': 'CCBYNC',
        'tooltip': 'CC BY-NC 4.0 表示—非営利|CC BY-NC 4.0 Attribution—NonCommercial',
        'en': 'Creative Commons Attribution-NonCommercial 4.0 International',
        'url': 'https://creativecommons.org/licenses/by-nc/4.0/deed.en'
    },
    {
        'text': 'CCBYNCSA',
        'tooltip': 'CC BY-NC-SA 4.0 表示—非営利—継承|CC BY-NC-SA 4.0 Attribution—NonCommercial—ShareAlike',
        'en': 'Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International',
        'url': 'https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en'
    },
    {
        'text': 'CCBYNCND',
        'tooltip': 'CC BY-NC-ND 4.0 表示—非営利—改変禁止|CC BY-NC-ND 4.0 Attribution—NonCommercial—NoDerivatives',
        'en': 'Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International',
        'url': 'https://creativecommons.org/licenses/by-nc-nd/4.0/deed.en'
    },
    {
        'text': 'AFL',
        'tooltip': 'Academic Free License (AFL) 3.0',
        'en': 'Academic Free License version 3.0',
        'url': 'https://opensource.org/licenses/AFL-3.0'
    },
    {
        'text': 'MIT',
        'tooltip': 'MIT License',
        'en': 'MIT License',
        'url': 'https://opensource.org/licenses/MIT'
    },
    {
        'text': 'Apache2',
        'tooltip': 'Apache License 2.0',
        'en': 'Apache License Version 2.0',
        'url': 'https://www.apache.org/licenses/LICENSE-2.0'
    },
    {
        'text': 'BSD2',
        'tooltip': 'BSD 2-Clause \"Simplified\" License',
        'en': '2-Clause BSD License',
        'url': 'https://opensource.org/licenses/BSD-2-Clause'
    },
    {
        'text': 'BSD3',
        'tooltip': 'BSD 3-Clause \"New\"/\"Revised\" License',
        'en': '3-Clause BSD License',
        'url': 'https://opensource.org/licenses/BSD-3-Clause'
    },
    {
        'text': 'GPL3',
        'tooltip': 'GNU General Public License (GPL) 3.0',
        'en': 'GNU General Public License version 3',
        'url': 'https://www.gnu.org/licenses/gpl-3.0.html'
    },
    {
        'text': 'GPL2',
        'tooltip': 'GNU General Public License (GPL) 2.0',
        'en': 'GNU General Public License version 2',
        'url': 'https://www.gnu.org/licenses/gpl-2.0.html'
    },
    {
        'text': 'Artistic2',
        'tooltip': 'Artistic License 2.0',
        'en': 'Artistic License 2.0',
        'url': 'https://opensource.org/licenses/Artistic-2.0'
    },
    {
        'text': 'Eclipse1',
        'tooltip': 'Eclipse Public License 1.0',
        'en': 'Eclipse Public License -v 1.0',
        'url': 'https://opensource.org/licenses/EPL-1.0'
    },
    {
        'text': 'LGPL3',
        'tooltip': 'GNU Lesser General Public License (LGPL) 3.0',
        'en': 'GNU Lesser General Public License version 3',
        'url': 'https://www.gnu.org/licenses/lgpl-3.0.html'
    },
    {
        'text': 'LGPL2_1',
        'tooltip': 'GNU Lesser General Public License (LGPL) 2.1',
        'en': 'GNU Lesser General Public License version 2.1',
        'url': 'https://www.gnu.org/licenses/lgpl-2.1.html'
    },
    {
        'text': 'Mozilla2',
        'tooltip': 'Mozilla Public License 2.0',
        'en': 'Mozilla Public License 2.0',
        'url': 'https://opensource.org/licenses/MPL-2.0'
    },
]

def _get_license_for_jpcoar2(value):
    for license in LICENSE_DEFS:
        if license['text'] == value:
            return license
    return None

def _has_license_def_for_jpcoar2(value):
    return _get_license_for_jpcoar2(value) is not None

def _get_ja_license_name_for_jpcoar2(license):
    license = _get_license_for_jpcoar2(license)
    if license is None:
        return None
    return license['ja'] if 'ja' in license else ''

def _get_en_license_name_for_jpcoar2(license):
    license = _get_license_for_jpcoar2(license)
    if license is None:
        return None
    return license['en'] if 'en' in license else ''

def _get_license_url_for_jpcoar2(license):
    license = _get_license_for_jpcoar2(license)
    if license is None:
        return None
    return license['url'] if 'url' in license else ''

JINJA2_FILTERS = {
    'has_license_def_for_jpcoar2': _has_license_def_for_jpcoar2,
    'to_normalized_ja_license_name_for_jpcoar2': _get_ja_license_name_for_jpcoar2,
    'to_normalized_en_license_name_for_jpcoar2': _get_en_license_name_for_jpcoar2,
    'to_license_url_for_jpcoar2': _get_license_url_for_jpcoar2,
}
