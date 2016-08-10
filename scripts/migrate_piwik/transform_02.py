import sys
import copy
import json
from datetime import datetime

from scripts.migrate_piwik import utils
from scripts.migrate_piwik import settings


def main(force=False):

    history_run_id = utils.get_history_run_id_for('transform01')
    complaints_run_id = utils.get_complaints_run_id_for('transform01')
    if history_run_id != complaints_run_id:
        print("You need to validate your first-phase transformed data! Bailing...")
        sys.exit()

    extract_complaints = utils.get_complaints_for('transform01', 'r')
    extract_complaints.readline()  # toss header
    if extract_complaints.readline():
        print("You have unaddressed complaints in your first-phase transform!")
        if not force:
            print("  ...pass --force to ignore")
            sys.exit()


    history_file = utils.get_history_for('transform02', 'w')
    history_file.write('Run ID: {}\n'.format(complaints_run_id))
    history_file.write('Beginning extraction at: {}Z\n'.format(datetime.utcnow()))

    transform_dir = utils.get_dir_for('transform02')
    public_template = transform_dir + '/public-{0:04d}.data'
    private_template = transform_dir + '/private-{0:04d}.data'

    lastline = 0
    try:
        with open(utils.get_dir_for('transform02') + '/resume.log', 'r') as fp:
            fp.seek(-32, 2)
            lastline = int(fp.readlines()[-1].strip('\n'))
    except IOError:
        pass


    linenum = 0
    batchnum = 0
    public_pageviews = []
    private_pageviews = []

    with open(transform_dir + '/resume.log', 'a', 0) as resume_file:  # Pass 0 for unbuffered writing
        with open(utils.get_dir_for('transform01') + '/' + settings.TRANSFORM01_FILE, 'r') as input_file:
            print('Lastline is: {}\n'.format(lastline))
            for i, pageview_json in enumerate(input_file):
                linenum = i + 1
                if linenum <= lastline:
                    if not linenum % 1000:
                        print('Skipping line {} of ***{}***'.format(linenum, lastline))
                    continue

                if not linenum % 1000:
                    print('Batching line {}'.format(linenum))

                pageview = json.loads(pageview_json)
                made_public_date = pageview['node']['made_public_date']
                del pageview['node']['made_public_date']

                private_pageviews.append(pageview)

                # only pageviews logged after the most recent make public date are copied to public
                # collection
                if made_public_date is not None and made_public_date < pageview['keen']['timestamp']:
                    public_pageview = copy.deepcopy(pageview)

                    for private_property in ('tech', 'user', 'visitor', 'geo' ):
                        del public_pageview[private_property]

                    for addon in public_pageview['keen']['addons']:
                        if addon['name'] in ('keen:ip_to_geo', 'keen:ua_parser'):
                            public_pageview['keen']['addons'].remove(addon)

                    public_pageviews.append(public_pageview)

                if linenum % settings.BATCH_SIZE == 0:
                    batchnum += 1
                    write_batch(batchnum, complaints_run_id, 'public', public_pageviews, transform_dir)
                    write_batch(batchnum, complaints_run_id, 'private', private_pageviews, transform_dir)
        
        if linenum % settings.BATCH_SIZE != 0:
            batchnum += 1
            write_batch(batchnum, complaints_run_id, 'public', public_pageviews, transform_dir)
            write_batch(batchnum, complaints_run_id, 'private', private_pageviews, transform_dir)

    history_file.write(settings.BATCH_HEADER + '{}\n'.format(batchnum))


def write_batch(batchnum, run_id, domain, pageviews, base_dir):
    print("---Writing Batch")
    with open(base_dir + '/' + settings.EVENT_DATA_FILE_TEMPLATE.format(domain=domain, batch_id=batchnum), 'w') as batch_file:
        batch_file.write(settings.RUN_HEADER + '{}\n'.format(run_id))
        batch_file.write(json.dumps(pageviews))

    del pageviews[:]


if __name__ == "__main__":
    force = '--force' in sys.argv
    main(force=force)

