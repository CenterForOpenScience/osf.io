from website.app import setup_django
setup_django()
from osf.models import Preprint
from website.preprints.tasks import update_preprint_share
import progressbar

 # To run: docker-compose run --rm web python -m scripts.remove_after_use.node_preprint_share
def main():
    """
    Updates all preprints in SHARE post-divorce
    """
    preprints = Preprint.objects.all()
    progress_bar = progressbar.ProgressBar(maxval=preprints.count()).start()
    for i, preprint in enumerate(preprints, 1):
        progress_bar.update(i)
        update_preprint_share(preprint)
    progress_bar.finish()


if __name__ == '__main__':
    main()
