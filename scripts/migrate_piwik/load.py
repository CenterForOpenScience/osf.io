import sys
import json
from datetime import datetime

from keen import KeenClient
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk as es_bulk

import website.settings as settings
from scripts.migrate_piwik import utils
from scripts.migrate_piwik import settings as script_settings


def main(dry_run=True, batch_count=None, force=False):
    """Upload the pageviews to Keen.
    """

    history_run_id = utils.get_history_run_id_for('transform02')
    complaints_run_id = utils.get_complaints_run_id_for('transform02')
    if history_run_id != complaints_run_id:
        print("You need to validate your first-phase transformed data! Bailing...")
        sys.exit()

    extract_complaints = utils.get_complaints_for('transform02', 'r')
    extract_complaints.readline()  # toss header
    if extract_complaints.readline():
        print("You have unaddressed complaints in your second-phase transform!")
        if not force:
            print("  ...pass --force to ignore")
            sys.exit()


    history_file = utils.get_history_for('load', 'w')
    history_file.write(script_settings.RUN_HEADER + '{}\n'.format(complaints_run_id))
    history_file.write('Beginning upload at: {}Z\n'.format(datetime.utcnow()))

    keen_clients = {'public': None, 'private': None}
    es_client = None
    if dry_run:
        print("Doing dry-run upload to Elastic search.  Pass --for-reals to upload to Keen")
        es_client = Elasticsearch()
        try:
            es_client.indices.delete(script_settings.ES_INDEX)
        except Exception as exc:
            print(exc)
            pass
    else:
        keen_clients = {
            'public': KeenClient(
                project_id=settings.KEEN['public']['project_id'],
                write_key=settings.KEEN['public']['write_key'],
            ),
            'private':  KeenClient(
                project_id=settings.KEEN['private']['project_id'],
                write_key=settings.KEEN['private']['write_key'],
            )
        }

    tally = {}
    seen = {}

    try:
        resume_log = open(utils.get_dir_for('load') + '/resume.log', 'r')
        for seen_file in resume_log.readlines():
            seen[seen_file.strip('\n')] = 1
    except:
        pass

    resume_log = open(utils.get_dir_for('load') + '/resume.log', 'a')
    batch_count = utils.get_batch_count() if batch_count is None else batch_count
    print("Beginning Upload")
    for batch_id in range(1, batch_count+1):
        print("  Batch {}".format(batch_id))
        for domain in ('private', 'public'):
            print("    Domain: {}".format(domain))

            file_id = '{}-{}'.format(domain, batch_id)
            if file_id in seen.keys():
                print("  ...seen, skipping.\n")
                continue

            history_file.write('Uploading for {} project, batch {}'.format(domain, batch_id))
            load_batch_for(batch_id, domain, tally, dry_run, es_client, keen_clients[domain])
            resume_log.write('{}\n'.format(file_id))
            history_file.write('  ...finished\n')

    print("Finished Upload")
    history_file.write('Finished upload at: {}Z\n'.format(datetime.utcnow()))
    history_file.write('Tally was:\n')
    for k, v in sorted(tally.items()):
        history_file.write('  {}: {}\n'.format(k, v))


def load_batch_for(batch_id, domain, tally, dry_run, es_client, keen_client):
    data_dir = utils.get_dir_for('transform02')
    batch_filename = script_settings.EVENT_DATA_FILE_TEMPLATE.format(
        domain=domain, batch_id=batch_id
    )
    data_file = open(data_dir + '/' + batch_filename, 'r')
    run_id = data_file.readline().rstrip()
    events = json.loads(data_file.readline())

    if dry_run:
        actions = [{
            '_index': script_settings.ES_INDEX,
            '_type': domain + '-pageviews',
            '_source': event,
        } for event in events]

        stats = es_bulk(
            client=es_client, stats_only=True, actions=actions,
        )
        tally[domain + '-' + str(batch_id)] = stats
    else:
        keen_client.add_events({'pageviews': events})


if __name__ == "__main__":
    dry_run = '--for-reals' not in sys.argv
    force = '--force' in sys.argv
    main(dry_run=dry_run, force=force)
