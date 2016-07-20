import re
import json

from scripts.migrate_piwik import utils
from scripts.migrate_piwik import settings


def main():

    input_filename = '/'.join([utils.get_dir_for('extract'), settings.EXTRACT_FILE,])
    input_file = open(input_filename, 'r')

    run_id = utils.get_history_run_id_for('extract')
    complaints_file = utils.get_complaints_for('extract', 'w')
    complaints_file.write('Run ID: {}\n'.format(run_id))

    linenum = 0
    complaints = 0
    for pageview_json in input_file.readlines():
        linenum += 1
        pageview = json.loads(pageview_json)

        visit = pageview['visit']
        action = pageview['action']

        # ip address are all scrubbed?
        if not re.search('0\.0$', visit['ip_addr']):
            complaints += 1
            complaints_file.write(
                'Line {}, ID {}: unscrubbed ip address! ({})\n'.format(
                    linenum, action['id'], visit['ip_addr']
                )
            )

        if not action['page']['url']:
            complaints += 1
            complaints_file.write('Line {}, ID {}: page url is missing!\n'.format(linenum, action['id']))
        elif re.match('https?:\/\/', action['page']['url']):
            complaints += 1
            complaints_file.write(
                'Line {}, ID {}: page url includes domain! ({})\n'.format(
                    linenum, action['id'], action['page']['url'].encode('utf-8')
                )
            )

    if complaints > 0:
        print("You've got {} problems, but a ready-to-go migration ain't one!".format(complaints))
    else:
        print("Looks good.  How'd you manage that?");

if __name__ == "__main__":
    main()
