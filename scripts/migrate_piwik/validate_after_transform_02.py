import re
import glob
import json

from scripts.migrate_piwik import utils
from scripts.migrate_piwik import settings


def main():
    """Verification of batching/anonymization script.

    Asserts:

    * Expected number of batch files exist for both public and private collections.

    * No extra batch files exist for both public and private collections.

    * All of the batch files are part on the current run.

    * Number of events is consistent between public and private, and matches up with upstream counts

    * No sensitive fields exists in public collections.

    """

    run_id = utils.get_history_run_id_for('transform02')
    complaints_file = utils.get_complaints_for('transform02', 'w')
    complaints_file.write(settings.RUN_HEADER + '{}\n'.format(run_id))

    batch_count = utils.get_batch_count()

    complaints = 0
    print('Validating private data\n')
    complaints += verify_files('private', batch_count, run_id, complaints_file)
    print('Validating public data\n')
    complaints += verify_files('public', batch_count, run_id, complaints_file)

    if complaints > 0:
        print("This is {}.\n\nThat's {} {}!".format(
            ', '.join(['gross'] * complaints), complaints, 'whole "gross"' if complaints == 1 else '"grosses"'
        ))
    else:
        print("You've passed the final challenge! Huzzah, brave warrior!")


def verify_files(domain, batch_count, run_id, complaints_file):
    complaints = 0
    work_dir = utils.get_dir_for('transform02')
    files = glob.glob(work_dir + '/' + domain + '-*.data')
    if batch_count > len(files):
        complaints += 1
        complaints_file.write('Too many {} files found! got {}, expected {}\n'.format(
            domain, len(files), batch_count,
        ))
    elif batch_count < len(files):
        complaints += 1
        complaints_file.write('Too few {} files found! got {}, expected {}\n'.format(
            domain, len(files), batch_count,
        ))

    lastfile_re = domain + '\-\d*' + str(batch_count) + '\.data'
    for filename in files:
        data_file = open(filename, 'r')
        file_run_id = data_file.readline().replace(settings.RUN_HEADER, '').rstrip()
        if file_run_id != run_id:
            complaints += 1
            complaints_file.write('Invalid Run ID for {}! got {}, expected {}\n'.format(
                filename, file_run_id, run_id,
            ))
            break

        events = json.loads(data_file.readline())
        if len(events) != settings.BATCH_SIZE and not re.search(lastfile_re, filename):
            complaints += 1
            complaints_file.write('Not enough events for {}! got {}, expected {}\n'.format(
                filename, len(events), settings.BATCH_SIZE,
            ))

        if domain == 'public':
            eventnum = 0
            for event in events:
                eventnum += 1
                if hasattr(event, 'tech'):
                    complaints += 1
                    complaints_file.write(
                        'Event {} in {} has private data! "tech" shouldn\'t be included\n'.format(
                            eventnum, filename,
                        )
                    )
                if hasattr(event, 'user'):
                    complaints += 1
                    complaints_file.write(
                        'Event {} in {} has private data! "user" shouldn\'t be included\n'.format(
                            eventnum, filename,
                        )
                    )

    return complaints


if __name__ == "__main__":
    main()
