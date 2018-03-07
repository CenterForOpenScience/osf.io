
import logging
from django.db import transaction
from website.app import setup_django
setup_django()

from osf.models import Subject, PreprintProvider

logger = logging.getLogger(__name__)

def main():
    eartharxiv = PreprintProvider.objects.get(_id='eartharxiv')
    physical_sciences_mathematics = Subject.objects.get(text='Physical Sciences and Mathematics', provider=eartharxiv)
    earth_sciences, _ = Subject.objects.get_or_create(text='Earth Sciences', provider=eartharxiv)

    logger.info('creating subject Planetary Sciences')
    planetary_sciences, _ = Subject.objects.get_or_create(
        provider=eartharxiv,
        parent=physical_sciences_mathematics,
        text='Planetary Sciences',
        bepress_subject=earth_sciences
    )

    new_ps_children = [
        'Planetary Biogeochemistry',
        'Planetary Cosmochemistry',
        'Planetary Geochemistry',
        'Planetary Geology',
        'Planetary Geomorphology',
        'Planetary Geophysics and Seismology',
        'Planetary Glaciology',
        'Planetary Hydrology',
        'Planetary Mineral Physics',
        'Planetary Paleobiology',
        'Planetary Paleontology',
        'Planetary Sedimentology',
        'Planetary Soil Science',
        'Planetary Stratigraphy',
        'Planetary Tectonics and Structure',
        'Planetary Volcanology',
        'Other Planetary Sciences'
    ]

    for child_text in new_ps_children:
        logger.info('creating subject {}'.format(child_text))
        Subject.objects.get_or_create(
            provider=eartharxiv,
            parent=planetary_sciences,
            text=child_text,
            bepress_subject=earth_sciences
        )

if __name__ == '__main__':
    with transaction.atomic():
        main()
