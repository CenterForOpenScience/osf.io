import json
import logging
import os
import sys

from modularodm import Q

from framework.mongo import database
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app
from website.models import PreprintService, Subject
from website import settings


logger = logging.getLogger(__name__)

PLOS_TO_BP_MAP = {
    'Advertising and Promotion Management': 'Advertising and Promotion Management',
    'Aerospace engineering': 'Aerospace Engineering',
    'Agribusiness': 'Agribusiness',
    'Agricultural economics': 'Agricultural Economics',
    'Agriculture': 'Agriculture',
    'Alternative energy': 'Power and Energy',
    'Anthropology': 'Anthropology',
    'Archaeology': 'Archaeological Anthropology',
    'Architectural Technology': 'Architectural Technology',
    'Architecture': 'Architecture',
    'Art and Design': 'Art and Design',
    'Artificial intelligence': 'Artificial Intelligence and Robotics',
    'Arts and Humanities': 'Arts and Humanities',
    'Asian History': 'Asian History',
    'Attitudes (psychology)': 'Social Psychology',
    'Audio signal processing': 'Signal Processing',
    'Automotive engineering': 'Automotive Engineering',
    'Aviation': 'Aviation',
    'Bayesian method': 'Statistical Methodology',
    'Biochemistry': 'Biochemistry',
    'Biology and life sciences': 'Life Sciences',
    'Business': 'Business',
    'Catalysis': 'Chemistry',
    'Cell biology': 'Cell Biology',
    'Cell processes': 'Cell Biology',
    'Ceramic Arts': 'Ceramic Arts',
    'Chemical engineering': 'Chemical Engineering',
    'Chemistry': 'Chemistry',
    'Child psychiatry': 'Psychiatry and Psychology',
    'Civil engineering': 'Civil Engineering',
    'Clinical psychology': 'Clinical Psychology',
    'Cognitive linguistics': 'Linguistics',
    'Cognitive neuroscience': 'Cognitive Neuroscience',
    'Cognitive psychology': 'Cognitive Psychology',
    'Collective human behavior': 'Experimental Analysis of Behavior',
    'Comparative Philosophy': 'Comparative Philosophy',
    'Computer and information sciences': 'Computer Sciences',
    'Computer applications': 'Computer Sciences',
    'Computer-assisted instruction': 'Online and Distance Education',
    'Computers': 'Computer Sciences',
    'Continental Philosophy': 'Continental Philosophy',
    'Control engineering': 'Process Control and Systems',
    'Control systems': 'Process Control and Systems',
    'Cultural anthropology': 'Social and Cultural Anthropology',
    'Culture': 'Sociology of Culture',
    'Curriculum and Instruction': 'Curriculum and Instruction',
    'Daylight': 'Ecology and Evolutionary Biology',
    'Democracy': 'Political Science',
    'Developmental psychology': 'Developmental Psychology',
    'Ecology and environmental sciences': 'Ecology and Evolutionary Biology',
    'Economics': 'Economics',
    'Education': 'Education',
    'Educational Assessment, Evaluation, and Research': 'Educational Assessment, Evaluation, and Research',
    'Educational Psychology': 'Educational Psychology',
    'Elections': 'Political Science',
    'Electronics': 'Electrical and Electronics',
    'Electronics engineering': 'Electrical and Electronics',
    'Emotions': 'Personality and Social Contexts',
    'Energy and power': 'Power and Energy',
    'Engineering and technology': 'Engineering',
    'Environmental engineering': 'Environmental Engineering',
    'Equipment': 'Engineering',
    'Evolutionary biology': 'Ecology and Evolutionary Biology',
    'Experimental psychology': 'Psychology',
    'Governments': 'Political Science',
    'Higher Education': 'Higher Education',
    'History': 'History',
    'Human families': 'Family, Life Course, and Society',
    'Image processing': 'Signal Processing',
    'Immunology': 'Immunology and Infectious Disease',
    'Immunopathology': 'Immunopathology',
    'Information processing': 'Databases and Information Systems',
    'Information technology': 'Computer Sciences',
    'Instructional Media Design': 'Instructional Media Design',
    'Library science': 'Library and Information Science',
    'Linguistic anthropology': 'Linguistic Anthropology',
    'Linguistic morphology': 'Morphology',
    'Linguistics': 'Linguistics',
    'Mathematical and statistical techniques': 'Applied Statistics',
    'Mechanical engineering': 'Mechanical Engineering',
    'Medicine and health sciences': 'Medicine and Health Sciences',
    'Mental health and psychiatry': 'Psychiatric and Mental Health',
    'Metaphysics': 'Metaphysics',
    'Music': 'Music',
    'Music Theory': 'Music Theory',
    'Nanoengineering': 'Nanoscience and Nanotechnology',
    'Neuroimaging': 'Computational Neuroscience',
    'Neuroscience': 'Neuroscience and Neurobiology',
    'Open access': 'Scholarly Publishing',
    'Open data': 'Science and Technology Policy',
    'Open science': 'Science and Technology Policy',
    'Other Languages, Societies, and Cultures': 'Other Languages, Societies, and Cultures',
    'People and places': '<drop>',
    'Personality': 'Personality and Social Contexts',
    'Philosophy': 'Philosophy',
    'Philosophy of Language': 'Philosophy of Language',
    'Philosophy of Mind': 'Philosophy of Mind',
    'Physical sciences': 'Physical Sciences and Mathematics',
    'Political geography': 'Political Science',
    'Political science': 'Political Science',
    'Population mobility': 'Demography, Population, and Ecology',
    'Psycholinguistics': 'Psycholinguistics and Neurolinguistics',
    'Psychological anthropology': 'Biological and Physical Anthropology',
    'Psychology': 'Psychology',
    'Psychometrics': 'Quantitative Psychology',
    'Psychophysics': 'Psychology',
    'Public opinion': 'Political Science',
    'Public policy': 'Public Policy',
    'Publication practices': 'Scholarly Publishing',
    'Quantitative analysis': 'Design of Experiments and Sample Surveys',
    'Religion': 'Religion',
    'Research and analysis methods': 'Design of Experiments and Sample Surveys',
    'Research design': 'Design of Experiments and Sample Surveys',
    'Research integrity': 'Science and Technology Policy',
    'Sanitary engineering': 'Environmental Engineering',
    'Scholarship of Teaching and Learning': 'Scholarship of Teaching and Learning',
    'Science and Mathematics Education': 'Science and Mathematics Education',
    'Science policy': 'Science and Technology Policy',
    'Science policy and economics': 'Science and Technology Policy',
    'Scientific publishing': 'Scholarly Publishing',
    'Semantics': 'Semantics and Pragmatics',
    'Sensory perception': 'Cognition and Perception',
    'Signal processing': 'Signal Processing',
    'Signal transduction': 'Cell Biology',
    'Social and behavioral sciences': 'Social and Behavioral Sciences',
    'Social anthropology': 'Social and Cultural Anthropology',
    'Social discrimination': 'Inequality and Stratification',
    'Social networks': 'Social Psychology and Interaction',
    'Social policy': 'Social Policy',
    'Social psychology': 'Social Psychology',
    'Social systems': 'Civic and Community Engagement',
    'Social theory': 'Social Control, Law, Crime, and Deviance',
    'Sociolinguistics': 'Anthropological Linguistics and Sociolinguistics',
    'Sociology': 'Sociology',
    'Sociology of knowledge': 'Theory, Knowledge and Science',
    'Solid waste management': 'Environmental Engineering',
    'South and Southeast Asian Languages and Societies': 'South and Southeast Asian Languages and Societies',
    'Statistical methods': 'Statistical Methodology',
    'Structural linguistics': 'Linguistics',
    'Systems engineering': 'Systems Engineering',
    'Teacher Education and Professional Development': 'Teacher Education and Professional Development',
    'Transportation': 'Transportation Engineering',
    'Transportation infrastructure': 'Transportation Engineering',
    'Urban, Community and Regional Planning': 'Urban, Community and Regional Planning',
    'Virtual archaeology': 'Archaeological Anthropology',
    'Web-based applications': 'Computer Sciences',
    "Women's health": "Women's Health",
    'Gravitation': 'Cosmology, Relativity, and Gravity',
    'Relativity': 'Cosmology, Relativity, and Gravity',
    'Quantum mechanics': 'Quantum Physics',
    'Technology regulations': 'Science and Technology Policy',
    'Mathematics': 'Mathematics',
    'Bilingual, Multilingual, and Multicultural Education': 'Bilingual, Multilingual, and Multicultural Education',
    'Algebra': 'Algebra',
    'Earth sciences': 'Earth Sciences',
    'Mood disorders': 'Mental Disorders',
    'Physical laws and principles': 'Other Physics',
    'Law': 'Law',
    'Behavioral disorders': 'Mental Disorders',
    'Electromagnetism': 'Electromagnetics and Photonics',
    'Electrochemistry': 'Other Chemistry',
    'Number theory': 'Number Theory',
    'Discrete mathematics': 'Discrete Mathematics and Combinatorics',
    'Banking and Finance Law': 'Banking and Finance Law',
    'Physics': 'Physics',
    'Neural networks': 'Artificial Intelligence and Robotics',
    'Digital Humanities': 'Digital Humanities',
    'Multivariate data analysis': 'Multivariate Analysis',
    'Mathematical physics': 'Physics',
    'Gambling addiction': 'Mental and Social Health',
    'Adolescent psychiatry': 'Psychiatry',
    'Particle physics': 'Elementary Particles and Fields and String Theory',
    'Biogeochemistry': 'Biogeochemistry',
    'Drought': 'Climate',
    'Conservation science': 'Natural Resources and Conservation',
    'Appalachian Studies': 'Appalachian Studies',
    'Data acquisition': 'Computer Sciences',
}

def validate_map_plos_correctness():
    logger.info('Validating correctness of PLOS terms in mapping')
    for text in PLOS_TO_BP_MAP:
        assert database['subject'].find({'text': text}).count(), 'Unable to find {}'.format(text)

def validate_map_bepress_correctness(bp_set):
    logger.info('Validating correctness of BePress terms in mapping')
    bp_map = set(PLOS_TO_BP_MAP.values())
    bp_map.remove('<drop>')
    assert bp_map.issubset(bp_set), '{} not found in BePress Taxonomy'.format(bp_map - bp_set)


def validate_map_completeness():
    logger.info('Validating completeness of PLOS->BePress mapping')
    assert set([s['text'] for p in PreprintService.find() for hier in p.get_subjects() for s in hier]).issubset(set(PLOS_TO_BP_MAP.keys())),\
        'Subjects not found in map: {}'.format(
            set([s['text'] for p in PreprintService.find() for hier in p.get_subjects() for s in hier]) - set(PLOS_TO_BP_MAP.keys())
        )

def get_targets():
    return database['preprintservice'].find({}, {'_id': 1, 'subjects': 1})    

def load_bepress(f_path):
    assert Subject.find().count() == 0
    logger.info('Loading BePress...')
    with open(f_path) as fp:
        bpress = json.load(fp)
        validate_map_bepress_correctness(set(bpress.keys()))
        logger.info('Populating Subjects...')
        for text in bpress.keys():
            Subject(text=text).save()
        assert Subject.find().count() == len(bpress.keys())
        logger.info('Setting parents...')
        for s in Subject.find():
            if bpress[s.text]['lineage']:
                s.parents = [Subject.find_one(Q('text', 'eq', bpress[s.text]['lineage'][-1]))]
                s.save()
        logger.info('Setting children...')
        for s in Subject.find():
            s.children = Subject.find(Q('parents', 'eq', s))
            s.save()
    logger.info('Successfully imported BePress taxonomy.')

def get_leaf(hier):
    if len(hier) == 1:
        return hier[0]
    for _id in hier:
        if not set(database['plos_subject'].find_one({'_id': _id})['children']) & set(hier):
            return _id
    raise RuntimeError('Unable to find leaf in {}'.format(hier))

def migrate_preprint(preprint):
    logger.info('Preparint to migrate {}'.format(preprint['_id']))
    new_hiers = []
    for hier in preprint['subjects']:
        leaf = get_leaf(hier)
        new_leaf_name = PLOS_TO_BP_MAP[database['plos_subject'].find_one({'_id': leaf})['text']]
        if new_leaf_name != '<drop>':
            new_hiers.append(
                Subject.find_one(Q('text', 'eq', new_leaf_name)).hierarchy
            )

    logger.info('Setting subjects on {} to {}'.format(preprint['_id'], new_hiers))
    database['preprintservice'].find_and_modify(
        {'_id': preprint['_id']},
        {'$set':{
            'subjects': new_hiers
        }}
    )

def migrate(bpress_file_path):
    count = 0
    validate_map_plos_correctness()
    validate_map_completeness()
    database.subject.rename('plos_subject')
    load_bepress(bpress_file_path)

    targets = list(get_targets())
    total = len(targets)
    logger.info('Preparing to migrate {} Preprints'.format(total))
    for preprint in targets:
        migrate_preprint(preprint)
        count += 1
        logger.info('Successfully migrated {}/{} -- {}'.format(count, total, preprint['_id']))

def main():
    dry_run = '--dry' in sys.argv
    path = None
    if '--file' in sys.argv:
        path = sys.argv[1 + sys.argv.index('--file')]
    if not path:
        raise RuntimeError('Specify a file with --file.')
    if not os.path.isfile(path):
        raise RuntimeError('Unable to find specified file.')
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    settings.SHARE_API_TOKEN = None  # blocks `on_preprint_updated`
    with TokuTransaction():
        migrate(bpress_file_path=path)
        if dry_run:
            raise RuntimeError('Dry run, transaction rolled back.')

if __name__ == "__main__":
    main()
