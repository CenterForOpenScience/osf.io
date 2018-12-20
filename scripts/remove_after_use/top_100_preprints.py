import datetime
import pytz
import csv
import sys

from website.app import setup_django
setup_django()

from osf.models import Preprint
from osf.metrics import PreprintDownload, PreprintView

TWENTY_EIGHTEEN = datetime.datetime(2018, 1, 1, tzinfo=pytz.UTC)

def main():
    public_preprints = Preprint.objects.filter(is_published=True, is_public=True)

    # Get the top 100 Preprints by download count
    top_preprints = PreprintDownload.get_top_by_count(
        qs=public_preprints,
        model_field='guids___id',
        metric_field='preprint_id',
        annotation='download_count',
        size=500,
        after=TWENTY_EIGHTEEN,
    )[:100]

    fieldnames = ['provider', 'url', 'title', '2018_download_count', '2018_view_count']
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    for preprint in top_preprints:
        row = {
            'provider': preprint.provider._id,
            'url': preprint.absolute_url,
            'title': preprint.title.encode('utf-8'),
            '2018_download_count': preprint.download_count,
            '2018_view_count': PreprintView.get_count_for_preprint(preprint, after=TWENTY_EIGHTEEN)
        }
        writer.writerow(row)

if __name__=='__main__':
    main()
