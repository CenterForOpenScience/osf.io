from __future__ import division
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
    writer = csv.DictWriter(output, fieldnames=[bucket['key_as_string'] for bucket in data.aggregations.times.buckets])
    writer.writeheader()
    for preprint_id in preprint_ids:
        data = search.filter('match', preprint_id=preprint_id).execute()
        writer.writerow({bucket['key_as_string']: bucket['doc_count'] for bucket in data.aggregations.times.buckets})

    return output

def main():
    preprint_guids_to_search = ['ahvdn']
    preprint_csv = generate_preprint_csv(preprint_guids_to_search)
    with open('top_ten_preprints.csv', 'wb') as writeFile:
        writeFile.write(preprint_csv.getvalue())


if __name__ == '__main__':
    main()

