import re
import json

from scripts.migrate_piwik import utils
from scripts.migrate_piwik import settings


def main():

    input_filename = '/'.join([utils.get_dir_for('transform01'), settings.TRANSFORM01_FILE,])
    input_file = open(input_filename, 'r')

    run_id = utils.get_history_run_id_for('transform01')
    complaints_file = utils.get_complaints_for('transform01', 'w')
    complaints_file.write('Run ID: {}\n'.format(run_id))

    linenum = 0
    complaints = 0
    for pageview_json in input_file.readlines():
        linenum += 1
        if not linenum % 100:
            print('Validating line {}'.format(linenum))

        pageview = json.loads(pageview_json)

        if pageview['page']['url'] is None:
            complaints += 1
            complaints_file.write('Line {}: empty url!\n'.format(linenum))

        # if pageview['page']['title'] is None:
        #     complaints += 1
        #     complaints_file.write('Line {}: empty page title!\n'.format(linenum))

        if pageview['time']['utc'] is None:
            complaints += 1
            complaints_file.write('Line {}: missing timestamp!\n'.format(linenum))

        if pageview['tech']['ip'] is not None:
            if pageview['anon']['continent'] is None or pageview['anon']['country'] is None:
                complaints += 1
                complaints_file.write(
                    'Line {}: Have IP addr ({}), but missing continent and/or country: ({} / {})\n'.format(
                        linenum, pageview['tech']['ip'], pageview['anon']['continent'] or 'None',
                        pageview['anon']['country'] or 'None'
                    )
                )

    if complaints > 0:
        print("I got {} reasons to be mad at you.  ".format(complaints))
    else:
        print("You've done your homework, have a cookie!");

if __name__ == "__main__":
    main()
