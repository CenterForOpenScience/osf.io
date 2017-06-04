from copy import deepcopy

import mock
from nose.tools import *  # noqa

from tests import factories
from tests.base import OsfTestCase, fake
from tests.utils import unique

from scripts.prereg.migrate_metadata_for_uploaders import migrate_draft_metadata, parse_view_url

from website.files.models import osfstorage

file_name_factory = unique(fake.file_name)
ean8_factory = unique(fake.ean8)
sha256_factory = unique(fake.sha256)

FILE_ONE = {
    "name": file_name_factory(),
    "path": '/' + ean8_factory(),
    "sha256": sha256_factory()
}
FILE_TWO = {
    "name": file_name_factory(),
    "path": '/' + ean8_factory(),
    "sha256": sha256_factory()
}
FILE_MAP = {
    FILE_ONE['path'].lstrip('/'): FILE_ONE,
    FILE_TWO['path'].lstrip('/'): FILE_TWO,
}

class FakeVersion(object):
    def __init__(self, metadata):
        self.metadata = metadata

class FakeFileNode(object):

    def __init__(self, sha256):
        self.sha256 = sha256

    @classmethod
    def get(cls, path, node):
        file_obj = FILE_MAP[path]
        return cls(file_obj['sha256'])

    def get_version(self):
        return FakeVersion({
            'sha256': self.sha256
        })

NODE_ID = ean8_factory()

SCHEMA_DATA = {
    "q20": {
        "comments": [],
        "value": "The Effect of sugar on brownie tastiness does not require any additional transformations. However, if it were using a regression analysis and each level of sweet had been categorically described (e.g. not sweet, somewhat sweet, sweet, and very sweet), sweet could be dummy coded with not sweet as the reference category.",
        "extra": {}
    },
    "q21": {
        "comments": [],
        "value": "If the the ANOVA indicates that the mean taste perceptions are significantly different (p&lt;.05), then we will use a Tukey-Kramer HSD test to conduct all possible pairwise comparison.",
        "extra": {}
    },
    "q22": {
        "comments": [],
        "value": "We will use the standard p&lt;.05 criteria for determining if the ANOVA and the post hoc test suggest that the results are significantly different from those expected if the null hypothesis were correct. The post-hoc Tukey-Kramer test adjusts for multiple comparisons.",
        "extra": {}
    },
    "q23": {
        "comments": [],
        "value": "No checks will be performed to determine eligibility for inclusion besides verification that each subject answered each of the three tastiness indices. Outliers will be included in the analysis",
        "extra": {}
    },
    "q24": {
        "comments": [],
        "value": "If a subject does not complete any of the three indices of tastiness, that subject will not be included in the analysis.",
        "extra": {}
    },
    "q25": {
        "comments": [],
        "value": "",
        "extra": {}
    },
    "q26": {
        "comments": [],
        "value": "sugar_taste.R",
        "extra": {
            "viewUrl": "/project/{0}/files/osfstorage{1}".format(
                NODE_ID,
                FILE_ONE['path']
            ),
            "hasSelectedFile": True,
            "selectedFileName": FILE_ONE['name']
        }
    },
    "q27": {
        "comments": [],
        "value": "",
        "extra": {}
    },
    "q1": {
        "comments": [],
        "value": "Effect of sugar on brownie tastiness",
        "extra": {}
    },
    "q3": {
        "comments": [],
        "value": "Though there is strong evidence to suggest that sugar affects taste preferences, the effect has never been demonstrated in brownies. Therefore, we will measure taste preference for four different levels of sugar concentration in a standard brownie recipe to determine if the effect exists in this pastry. ",
        "extra": {}
    },
    "q2": {
        "comments": [],
        "value": "David Mellor, Jolene Esposito",
        "extra": {}
    },
    "q5": {
        "comments": [],
        "value": "Registration prior to creation of data: As of the date of submission of this research plan for preregistration, the data have not yet been collected, created, or realized.",
        "extra": {}
    },
    "q4": {
        "comments": [],
        "value": "If taste affects preference, then mean preference indices will be higher with higher concentrations of sugar.",
        "extra": {}
    },
    "q7": {
        "comments": [],
        "value": {
            "question": {
                "comments": [],
                "value": "Participants will be recruited through advertisements at local pastry shops. Participants will be paid $10 for agreeing to participate (raised to $30 if our sample size is not reached within 15 days of beginning recruitment). Participants must be at least 18 years old and be able to eat the ingredients of the pastries.",
                "extra": {}
            },
            "uploader16": {
                "comments": [],
                "value": "",
                "extra": {
                    "viewUrl": "/project/{0}/files/osfstorage{1}".format(
                        NODE_ID,
                        FILE_TWO['path']
                    ),
                    "hasSelectedFile": True,
                    "selectedFileName": FILE_TWO['name']
                }
            }
        },
        "extra": {}
    },
    "q6": {
        "comments": [],
        "value": "Data do not yet exist",
        "extra": {}
    },
    "q9": {
        "comments": [],
        "value": "We used the software program G*Power to conduct a power analysis. Our goal was to obtain .95 power to detect a medium effect size of .25 at the standard .05 alpha error probability. ",
        "extra": {}
    },
    "q8": {
        "comments": [],
        "value": "Our target sample size is 280 participants. We will attempt to recruit up to 320, assuming that not all will complete the total task. ",
        "extra": {}
    },
    "q15": {
        "comments": [],
        "value": ["For studies that involve human subjects, they will not know the treatment group to which they have been assigned."],
        "extra": {}
    },
    "q14": {
        "comments": [],
        "value": "Experiment - A researcher randomly assigns treatments to study subjects, this includes field or lab experiments. This is also known as an intervention experiment and includes randomized controlled trials.",
        "extra": {}
    },
    "q17": {
        "comments": [],
        "value": "We will use block randomization, where each participant will be randomly assigned to one of the four equally sized, predetermined blocks. The random number list used to create these four blocks will be created using the web applications available at http://random.org. ",
        "extra": {}
    },
    "q16": {
        "comments": [],
        "value": {
            "question": {
                "comments": [],
                "value": "We have a between subjects design with 1 factor (sugar by mass) with 4 levels. ",
                "extra": {}
            },
            "uploader16": {
                "comments": [],
                "value": "",
                "extra": {}
            }
        },
        "extra": {}
    },
    "q11": {
        "comments": [],
        "value": "We manipulated the percentage of sugar by mass added to brownies. The four levels of this categorical variable are: 15%, 20%, 25%, or 40% cane sugar by mass. ",
        "extra": {}
    },
    "q10": {
        "comments": [],
        "value": "We will post participant sign-up slots by week on the preceding Friday night, with 20 spots posted per week. We will post 20 new slots each week if, on that Friday night, we are below 320 participants. ",
        "extra": {}
    },
    "q13": {
        "comments": [],
        "value": "We will take the mean of the two questions above to create a single measure of brownie enjoyment.",
        "extra": {}
    },
    "q12": {
        "comments": [],
        "value": "The single outcome variable will be the perceived tastiness of the single brownie each participant will eat. We will measure this by asking participants How much did you enjoy eating the brownie (on a scale of 1-7, 1 being not at all, 7 being a great deal) and How good did the brownie taste (on a scale of 1-7, 1 being very bad, 7 being very good). ",
        "extra": {}
    },
    "q19": {
        "comments": [],
        "value": {
            "q19a": {
                "value": "We will use a one-way between subjects ANOVA to analyze our results. The manipulated, categorical independent variable is 'sugar' whereas the dependent variable is our taste index. ",
                "extra": {}
            },
            "uploader19": {
                "value": "",
                "extra": {}
            },
        },
        "extra": {}
    }
}

EXISTING_UPLOADERS = set(('q26', ))
EXISTING_OPTIONAL_UPLOADERS = set(('q7', 'q16', 'q19'))
UPLOADERS_ADDED = set(('q11', 'q12', 'q13'))

OTHER_QUESTIONS = set(SCHEMA_DATA.keys()) - EXISTING_UPLOADERS - EXISTING_OPTIONAL_UPLOADERS - UPLOADERS_ADDED

def check_migration(orig_data, draft):
    # check for uploader added
    for qid in UPLOADERS_ADDED:
        if qid not in orig_data:
            continue
        if orig_data[qid]['value']:
            assert_equal(
                orig_data[qid]['value'],
                draft.registration_metadata[qid]['value']['question']['value']
            )
    # check for regular uploader type
    for qid in EXISTING_UPLOADERS:
        if qid not in orig_data:
            continue
        assert_equal(
            orig_data[qid]['value'],
            draft.registration_metadata[qid]['value']
        )
        if orig_data[qid]['extra']:
            assert_equal(
                orig_data[qid]['extra'].get('selectedFileName'),
                draft.registration_metadata[qid]['extra'].get('selectedFileName'),
            )
            assert_equal(
                orig_data[qid]['extra']['viewUrl'],
                draft.registration_metadata[qid]['extra']['viewUrl'],
            )
            if orig_data[qid]['extra'].get('viewUrl'):
                node_id, path = parse_view_url(orig_data[qid]['extra']['viewUrl'])
                assert_equal(
                    draft.registration_metadata[qid]['extra']['nodeId'],
                    node_id
                )
    # check for properties on object type
    for qid in EXISTING_OPTIONAL_UPLOADERS:
        if qid not in orig_data:
            continue
        uid = [k for k in orig_data[qid]['value'].keys() if 'uploader' in k][0]
        assert_equal(
            orig_data[qid]['value'][uid].get('value'),
            draft.registration_metadata[qid]['value']['uploader'].get('value')
        )
        if orig_data[qid]['value'][uid].get('extra'):
            assert_equal(
                orig_data[qid]['value'][uid]['extra'].get('selectedFileName'),
                draft.registration_metadata[qid]['value']['uploader'].get('extra', {}).get('selectedFileName'),
            )
            sqid = [k for k in orig_data[qid]['value'].keys() if not k == uid][0]
            assert_equal(
                orig_data[qid]['value'][sqid].get('value'),
                draft.registration_metadata[qid]['value']['question'].get('value', '')
            )
            if orig_data[qid]['extra'].get('viewUrl'):
                node_id, path = parse_view_url(orig_data[qid]['extra'].get('viewUrl'))
                assert_equal(
                    draft.registration_metadata[qid]['value'][sqid]['extra']['nodeId'],
                    node_id
                )
    # check everything else
    for qid in OTHER_QUESTIONS:
        if qid not in orig_data:
            continue
        assert_equal(
            orig_data[qid]['value'],
            draft.registration_metadata[qid]['value']
        )


class TestMigratePreregMetadata(OsfTestCase):

    def setUp(self):
        super(TestMigratePreregMetadata, self).setUp()

        self.draft = factories.DraftRegistrationFactory(
            registration_metadata=SCHEMA_DATA
        )

    @mock.patch.object(osfstorage, 'OsfStorageFileNode', FakeFileNode)
    def test_migrate_draft_metadata(self):
        orig_data = SCHEMA_DATA
        migrate_draft_metadata(self.draft)

        check_migration(orig_data, self.draft)

        # check for regular uploader type
        assert_equal(
            self.draft.registration_metadata['q26']['extra']['nodeId'],
            NODE_ID
        )
        assert_equal(
            self.draft.registration_metadata['q26']['extra']['sha256'],
            FILE_ONE['sha256']
        )
        assert_equal(
            self.draft.registration_metadata['q26']['extra']['selectedFileName'],
            FILE_ONE['name']
        )
        # check for properties on object type
        uid = [k for k in orig_data['q7']['value'].keys() if 'uploader' in k][0]
        assert_equal(
            self.draft.registration_metadata['q7']['value']['uploader']['extra']['nodeId'],
            NODE_ID
        )
        assert_equal(
            self.draft.registration_metadata['q7']['value']['uploader']['extra']['sha256'],
            FILE_TWO['sha256']
        )
        assert_equal(
            self.draft.registration_metadata['q7']['value']['uploader']['extra']['selectedFileName'],
            FILE_TWO['name']
        )
        assert_equal(
            orig_data['q7']['value'][uid]['extra']['viewUrl'],
            self.draft.registration_metadata['q7']['value']['uploader']['extra']['viewUrl']
        )
