from website.app import setup_django
setup_django()

from website import search
from website.search.elastic_search import delete_doc
from osf.models import Preprint, AbstractNode
import progressbar

# To run: docker-compose run --rm web python -m scripts.remove_after_use.node_preprint_es
def main():
    """
    Temporary script for updating elastic search after the node-preprint divorce
    - Removes nodes from the index that are categorized as preprints
    - Adds these nodes to the index, this time categorized as nodes
    - Adds preprints to the index, categorized as preprints
    """
    preprints = Preprint.objects
    progress_bar = progressbar.ProgressBar(maxval=preprints.count()).start()

    for i, p in enumerate(preprints.all(), 1):
        progress_bar.update(i)
        search.search.update_preprint(p, bulk=False, async=False) # create new index for preprint
        if p.node:
            delete_doc(p.node._id, p.node, category='preprint') # delete old index for node categorized as a preprint
            search.search.update_node(p.node, bulk=False, async=False) # create new index for node (this time categorized as a node)
    progress_bar.finish()


if __name__ == '__main__':
    main()
