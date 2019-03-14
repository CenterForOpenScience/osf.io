from __future__ import division
import argparse
import logging
import csv
import io

from website.app import setup_django
setup_django()


from osf.metrics import PreprintDownload

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def generate_preprint_csv(preprint_ids):
    search = PreprintDownload.search().aggs.metric('times', {'date_histogram': {'field': 'timestamp', 'interval': 'day', 'format': 'yyyy-MM-dd'}})
    output = io.BytesIO()
    data = search.execute()
    writer = csv.DictWriter(output, restval=0, fieldnames=[bucket['key_as_string'] for bucket in data.aggregations.times.buckets])
    writer.writeheader()
    for preprint_id in preprint_ids:
        data = search.filter('match', preprint_id=preprint_id).execute()
        if data.aggregations.times.buckets:
            writer.writerow({bucket['key_as_string']: bucket['doc_count'] for bucket in data.aggregations.times.buckets})
        else:
            logger.info('preprint {} could not be found skipping')

    return output

# defined command line options
# this also generates --help and error handling

# parse the command line
def main():
    preprint_guids_to_search = ['vdz32', 'hv28a', 'yj8xw', '35juv', 'pbhr4', 'mky9j', 'qt3k6', 'kr3z8', 'nbhxq', 'az5bg', 'd7av9', '447b3']

    cli = argparse.ArgumentParser()
    cli.add_argument(
        '--guids',
        nargs='*',
        type=str,
        default=preprint_guids_to_search,
    )
    args = cli.parse_args()

    preprint_csv = generate_preprint_csv(args.guids)
    with open('top_ten_preprints.csv', 'wb') as writeFile:
        writeFile.write(preprint_csv.getvalue())


if __name__ == '__main__':
    main()

