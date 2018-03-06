
import logging
import django
django.setup()

from osf.models import Subject, PreprintProvider


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():
    eartharxiv = PreprintProvider.objects.get(_id='eartharxiv')
    physical_sciences_mathmatics = Subject.objects.get(text='Physical Sciences and Mathematics', provider=eartharxiv)
    earth_sciences = Subject.objects.get(text='Earth Sciences', provider=eartharxiv)

    logger.info('creating subject Planetary Sciences')
    planetary_sciences = Subject.objects.create(
        provider=eartharxiv,
        parent=physical_sciences_mathmatics,
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
        Subject.objects.create(
            provider=eartharxiv,
            parent=planetary_sciences,
            text=child_text,
            bepress_subject=earth_sciences
        )

if __name__ == '__main__':
    main()
