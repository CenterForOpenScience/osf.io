import pytest
from future.moves.urllib.parse import urljoin

from osf.models import RegistrationSchema
from osf_tests.factories import DraftRegistrationFactory, RegistrationFactory

from osf.management.commands.migrate_registration_responses import (
    migrate_draft_registrations,
    migrate_registrations
)
from website import settings

"""
Regression test to prevent the migration of 'registration_metadata' behavior
from breaking
"""

prereg_registration_responses = {
    'q12.uploader': [],
    'q7.question': 'data collection procedures',
    'q20': 'transforming and recoding',
    'q21': 'research plan follow up',
    'q22': 'criteria',
    'q23': 'this is how outliers will be handled',
    'q24': 'this is how I will deal with incomplete data.',
    'q25': 'this is my exploratory analysis',
    'q26': [],
    'q27': 'No additional comments',
    'q12.question': 'these are my measured variables',
    'q1': 'This is my title',
    'q3': 'research questions',
    'q5': 'Registration prior to creation of data',
    'q4': 'this is my hypothesis',
    'q6': 'Explanation of existing data',
    'q9': 'this is the rationale for my sample size',
    'q8': 'this is my sample size',
    'q13.question': 'these are my indices',
    'q19.uploader': [],
    'q11.uploader': [
        {
            'file_name': 'Screen Shot 2019-08-30 at 9.04.01 AM.png',
            'file_id': '5d6d22264d476c088fb8e01f',
            'file_urls': {
                'html': urljoin(settings.DOMAIN, '/project/57zbh/files/osfstorage/5d6d22264d476c088fb8e01f'),
            },
            'file_hashes': {
                'sha256': 'sdf',
            },
        },
        {
            'file_name': 'Alphabet.txt',
            'file_id': '5d6d22274d476c088fb8e021',
            'file_urls': {
                'html': urljoin(settings.DOMAIN, '/project/57zbh/files/osfstorage/5d6d22274d476c088fb8e021'),
            },
            'file_hashes': {
                'sha256': 'dsdfds',
            },
        }
    ],
    'q16.question': 'this is my study design',
    'q15': [
        'No blinding is involved in this study.',
        'For studies that involve human subjects, they will not know the treatment group to which they have been assigned.',
        'Research personnel who interact directly with the study subjects (either human or non-human subjects) will not be aware of the assigned treatments.'
    ],
    'q14': '',
    'q17': 'this is my explanation of randomization',
    'q10': 'this is my stopping rule',
    'q11.question': 'these are my maniuplated variables',
    'q16.uploader': [],
    'q19.question': 'ANOVA',
    'q13.uploader': [],
    'q7.uploader': [
        {
            'file_name': 'Alphabet.txt',
            'file_id': '5d6d22274d476c088fb8e021',
            'file_urls': {
                'html': urljoin(settings.DOMAIN, '/project/57zbh/files/osfstorage/5d6d22274d476c088fb8e021'),
            },
            'file_hashes': {
                'sha256': 'dsdfds',
            },
        }
    ]
}

prereg_registration_metadata = {
    'q20': {
        'comments': [],
        'value': 'transforming and recoding',
        'extra': []
    },
    'q21': {
        'comments': [],
        'value': 'research plan follow up',
        'extra': []
    },
    'q22': {
        'comments': [],
        'value': 'criteria',
        'extra': []
    },
    'q23': {
        'comments': [],
        'value': 'this is how outliers will be handled',
        'extra': []
    },
    'q24': {
        'comments': [],
        'value': 'this is how I will deal with incomplete data.',
        'extra': []
    },
    'q25': {
        'comments': [],
        'value': 'this is my exploratory analysis',
        'extra': []
    },
    'q26': {
        'comments': [],
        'value': '',
        'extra': []
    },
    'q27': {
        'comments': [],
        'value': 'No additional comments',
        'extra': []
    },
    'q1': {
        'comments': [],
        'value': 'This is my title',
        'extra': []
    },
    'q3': {
        'comments': [],
        'value': 'research questions',
        'extra': []
    },
    'q5': {
        'comments': [],
        'value': 'Registration prior to creation of data',
        'extra': []
    },
    'q4': {
        'comments': [],
        'value': 'this is my hypothesis',
        'extra': []
    },
    'q7': {
        'comments': [],
        'value': {
            'question': {
                'comments': [],
                'value': 'data collection procedures',
                'extra': []
            },
            'uploader': {
                'comments': [],
                'value': 'Alphabet.txt',
                'extra': [
                    {
                        'descriptionValue': '',
                        'nodeId': '9bknu',
                        'viewUrl': '/project/57zbh/files/osfstorage/5d6d22274d476c088fb8e021/',
                        'selectedFileName': 'Alphabet.txt',
                        'sha256': 'dsdfds',
                        'data': {
                            'contentType': '',
                            'sizeInt': 3169,
                            'kind': 'file',
                            'resource': '9bknu',
                            'name': 'Alphabet.txt',
                            'extra': {
                                'downloads': 0,
                                'latestVersionSeen': '',
                                'version': 1,
                                'hashes': {
                                    'sha256': 'dsdfds',
                                    'md5': 'sdfsef'
                                },
                                'guid': '',
                                'checkout': ''
                            },
                            'materialized': '/Alphabet.txt',
                            'created_utc': '',
                            'nodeId': '9bknu',
                            'modified': '2019-09-02T14:04:14.776301+00:00',
                            'etag': 'b529584199f707abda42a42ec2f3c5a052d280e56fb3382f07efc77933053159',
                            'provider': 'osfstorage',
                            'path': '/5d6d215b4d476c088fb8e000',
                            'modified_utc': '2019-09-02T14:04:14+00:00',
                            'size': 3169
                        },
                        'fileId': '7ry42'
                    }
                ]
            }
        },
        'extra': []
    },
    'q6': {
        'comments': [],
        'value': 'Explanation of existing data',
        'extra': []
    },
    'q9': {
        'comments': [],
        'value': 'this is the rationale for my sample size',
        'extra': []
    },
    'q8': {
        'comments': [],
        'value': 'this is my sample size',
        'extra': []
    },
    'q15': {
        'comments': [],
        'value': [
            'No blinding is involved in this study.',
            'For studies that involve human subjects, they will not know the treatment group to which they have been assigned.',
            'Research personnel who interact directly with the study subjects (either human or non-human subjects) will not be aware of the assigned treatments.'
        ],
        'extra': []
    },
    'q14': {
        'comments': [],
        'value': '',
        'extra': []
    },
    'q17': {
        'comments': [],
        'value': 'this is my explanation of randomization',
        'extra': []
    },
    'q16': {
        'comments': [],
        'value': {
            'question': {
                'comments': [],
                'value': 'this is my study design',
                'extra': []
            },
            'uploader': {
                'comments': [],
                'value': '',
                'extra': []
            }
        },
        'extra': []
    },
    'q11': {
        'comments': [],
        'value': {
            'question': {
                'comments': [],
                'value': 'these are my maniuplated variables',
                'extra': []
            },
            'uploader': {
                'comments': [],
                'value': 'Screen Shot 2019-08-30 at 9.04.01 AM.png',
                'extra': [
                    {
                        'descriptionValue': '',
                        'nodeId': '9bknu',
                        'viewUrl': '/project/57zbh/files/osfstorage/5d6d22264d476c088fb8e01f/',
                        'selectedFileName': 'Screen Shot 2019-08-30 at 9.04.01 AM.png',
                        'sha256': 'sdf',
                        'data': {
                            'contentType': '',
                            'sizeInt': 78257,
                            'kind': 'file',
                            'resource': '9bknu',
                            'name': 'Screen Shot 2019-08-30 at 9.04.01 AM.png',
                            'extra': {
                                'downloads': 0,
                                'latestVersionSeen': '',
                                'version': 1,
                                'hashes': {
                                    'sha256': 'sdf',
                                    'md5': 'asdf'
                                },
                                'guid': '',
                                'checkout': ''
                            },
                            'materialized': '/Screen Shot 2019-08-30 at 9.04.01 AM.png',
                            'created_utc': '',
                            'nodeId': '9bknu',
                            'modified': '2019-09-02T14:04:47.793337+00:00',
                            'etag': 'd114466ad8f1e04c03e678fdaf642988c1accd1526bb6e81b34bf35612a77cbb',
                            'provider': 'osfstorage',
                            'path': '/5d6d217f4d476c088fb8e00d',
                            'modified_utc': '2019-09-02T14:04:47+00:00',
                            'size': 78257
                        },
                        'fileId': 'nc8qy'
                    },
                    {
                        'descriptionValue': '',
                        'nodeId': '9bknu',
                        'viewUrl': '/project/57zbh/files/osfstorage/5d6d22274d476c088fb8e021/',
                        'selectedFileName': 'Alphabet.txt',
                        'sha256': 'asdf',
                        'data': {
                            'links': {
                                'download': 'http://localhost:7777/v1/resources/9bknu/providers/osfstorage/5d6d215b4d476c088fb8e000',
                                'move': 'http://localhost:7777/v1/resources/9bknu/providers/osfstorage/5d6d215b4d476c088fb8e000',
                                'upload': 'http://localhost:7777/v1/resources/9bknu/providers/osfstorage/5d6d215b4d476c088fb8e000?kind=file',
                                'delete': 'http://localhost:7777/v1/resources/9bknu/providers/osfstorage/5d6d215b4d476c088fb8e000'
                            },
                            'extra': {
                                'downloads': 0,
                                'latestVersionSeen': '',
                                'version': 1,
                                'hashes': {
                                    'sha256': 'asdf',
                                    'md5': 'sdfs'
                                },
                                'guid': '',
                                'checkout': ''
                            },
                            'accept': {
                                'acceptedFiles': 'True',
                                'maxSize': 5120
                            },
                            'id': 'osfstorage/5d6d215b4d476c088fb8e000',
                            'size': 3169,
                            'nodeApiUrl': '/api/v1/project/9bknu/',
                            'nodeId': '9bknu',
                            'etag': 'b529584199f707abda42a42ec2f3c5a052d280e56fb3382f07efc77933053159',
                            'provider': 'osfstorage',
                            'type': 'files',
                            'nodeUrl': '/9bknu/',
                            'sizeInt': 3169,
                            'contentType': '',
                            'path': '/5d6d215b4d476c088fb8e000',
                            'permissions': {
                                'edit': 'True',
                                'view': 'True'
                            },
                            'waterbutlerURL': 'http://localhost:7777',
                            'kind': 'file',
                            'resource': '9bknu',
                            'name': 'Alphabet.txt',
                            'materialized': '/Alphabet.txt',
                            'created_utc': '2019-09-02T14:04:14.776301+00:00',
                            'modified': '2019-09-02T14:04:14.776301+00:00',
                            'modified_utc': '2019-09-02T14:04:14.776301+00:00'
                        },
                        'fileId': '7ry42'
                    }
                ]
            }
        },
        'extra': []
    },
    'q10': {
        'comments': [],
        'value': 'this is my stopping rule',
        'extra': []
    },
    'q13': {
        'comments': [],
        'value': {
            'question': {
                'comments': [],
                'value': 'these are my indices',
                'extra': []
            },
            'uploader': {
                'comments': [],
                'value': '',
                'extra': []
            }
        },
        'extra': []
    },
    'q12': {
        'comments': [],
        'value': {
            'question': {
                'comments': [],
                'value': 'these are my measured variables',
                'extra': []
            },
            'uploader': {
                'comments': [],
                'value': '',
                'extra': []
            }
        },
        'extra': []
    },
    'q19': {
        'comments': [],
        'value': {
            'question': {
                'comments': [],
                'value': 'ANOVA',
                'extra': []
            },
            'uploader': {
                'comments': [],
                'value': '',
                'extra': []
            }
        },
        'extra': []
    }
}

prereg_registration_metadata_built = {
    'q20': {
        'comments': [],
        'value': 'transforming and recoding',
        'extra': []
    },
    'q21': {
        'comments': [],
        'value': 'research plan follow up',
        'extra': []
    },
    'q22': {
        'comments': [],
        'value': 'criteria',
        'extra': []
    },
    'q23': {
        'comments': [],
        'value': 'this is how outliers will be handled',
        'extra': []
    },
    'q24': {
        'comments': [],
        'value': 'this is how I will deal with incomplete data.',
        'extra': []
    },
    'q25': {
        'comments': [],
        'value': 'this is my exploratory analysis',
        'extra': []
    },
    'q26': {
        'comments': [],
        'value': '',
        'extra': []
    },
    'q27': {
        'comments': [],
        'value': 'No additional comments',
        'extra': []
    },
    'q1': {
        'comments': [],
        'value': 'This is my title',
        'extra': []
    },
    'q3': {
        'comments': [],
        'value': 'research questions',
        'extra': []
    },
    'q5': {
        'comments': [],
        'value': 'Registration prior to creation of data',
        'extra': []
    },
    'q4': {
        'comments': [],
        'value': 'this is my hypothesis',
        'extra': []
    },
    'q7': {
        'value': {
            'question': {
                'comments': [],
                'value': 'data collection procedures',
                'extra': []
            },
            'uploader': {
                'comments': [],
                'value': '',
                'extra': [
                    {
                        'viewUrl': '/project/57zbh/files/osfstorage/5d6d22274d476c088fb8e021',
                        'selectedFileName': 'Alphabet.txt',
                        'nodeId': '57zbh',
                        'sha256': 'dsdfds',
                        'data': {
                            'name': 'Alphabet.txt'
                        }
                    }
                ]
            }
        },
    },
    'q6': {
        'comments': [],
        'value': 'Explanation of existing data',
        'extra': []
    },
    'q9': {
        'comments': [],
        'value': 'this is the rationale for my sample size',
        'extra': []
    },
    'q8': {
        'comments': [],
        'value': 'this is my sample size',
        'extra': []
    },
    'q15': {
        'comments': [],
        'value': [
            'No blinding is involved in this study.',
            'For studies that involve human subjects, they will not know the treatment group to which they have been assigned.',
            'Research personnel who interact directly with the study subjects (either human or non-human subjects) will not be aware of the assigned treatments.'
        ],
        'extra': []
    },
    'q14': {
        'comments': [],
        'value': '',
        'extra': []
    },
    'q17': {
        'comments': [],
        'value': 'this is my explanation of randomization',
        'extra': []
    },
    'q16': {
        'value': {
            'question': {
                'comments': [],
                'value': 'this is my study design',
                'extra': []
            },
            'uploader': {
                'comments': [],
                'value': '',
                'extra': []
            }
        },
    },
    'q11': {
        'value': {
            'question': {
                'comments': [],
                'value': 'these are my maniuplated variables',
                'extra': []
            },
            'uploader': {
                'comments': [],
                'value': '',
                'extra': [
                    {
                        'selectedFileName': 'Screen Shot 2019-08-30 at 9.04.01 AM.png',
                        'viewUrl': '/project/57zbh/files/osfstorage/5d6d22264d476c088fb8e01f',
                        'nodeId': '57zbh',
                        'sha256': 'sdf',
                        'data': {
                            'name': 'Screen Shot 2019-08-30 at 9.04.01 AM.png'
                        }
                    },
                    {
                        'selectedFileName': 'Alphabet.txt',
                        'viewUrl': '/project/57zbh/files/osfstorage/5d6d22274d476c088fb8e021',
                        'nodeId': '57zbh',
                        'sha256': 'dsdfds',
                        'data': {
                            'name': 'Alphabet.txt'
                        }
                    }
                ]
            }
        },
    },
    'q10': {
        'comments': [],
        'value': 'this is my stopping rule',
        'extra': []
    },
    'q13': {
        'value': {
            'question': {
                'comments': [],
                'value': 'these are my indices',
                'extra': []
            },
            'uploader': {
                'comments': [],
                'value': '',
                'extra': []
            }
        },
    },
    'q12': {
        'value': {
            'question': {
                'comments': [],
                'value': 'these are my measured variables',
                'extra': []
            },
            'uploader': {
                'comments': [],
                'value': '',
                'extra': []
            }
        },
    },
    'q19': {
        'value': {
            'question': {
                'comments': [],
                'value': 'ANOVA',
                'extra': []
            },
            'uploader': {
                'comments': [],
                'value': '',
                'extra': []
            }
        },
    }
}

veer_registration_metadata = {
    'dataCollectionDates': {
        'comments': [],
        'value': '2020 - 2030',
        'extra': []
    },
    'description-methods': {
        'comments': [],
        'value': {
            'exclusion-criteria': {
                'comments': [],
                'value': {
                    'question8b': {
                        'comments': [],
                        'value': 'these are failing check-tests',
                        'extra': []
                    }
                },
                'extra': []
            },
            'design': {
                'comments': [],
                'value': {
                    'question2a': {
                        'comments': [],
                        'value': 'a. whether they are between participants',
                        'extra': []
                    },
                    'question2b': {
                        'comments': [],
                        'value': 'these are my dependent variables',
                        'extra': []
                    },
                    'question3b': {
                        'comments': [],
                        'value': 'These variables are acting as covariates.',
                        'extra': []
                    }
                },
                'extra': []
            },
            'procedure': {
                'comments': [],
                'value': {
                    'question10b': {
                        'comments': [],
                        'value': 'describe all manipulations',
                        'extra': []
                    }
                },
                'extra': []
            },
            'planned-sample': {
                'comments': [],
                'value': {
                    'question4b': {
                        'comments': [],
                        'value': 'these are the preselection rults',
                        'extra': []
                    },
                    'question7b': {
                        'comments': [],
                        'value': 'here is my data collection termination rule',
                        'extra': []
                    },
                    'question5b': {
                        'comments': [],
                        'value': 'here is how the data will be collected',
                        'extra': []
                    },
                    'question6b-upload': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question6b': {
                        'comments': [],
                        'value': 'this is my planned sample size',
                        'extra': []
                    }
                },
                'extra': []
            }
        },
        'extra': []
    },
    'recommended-analysis': {
        'comments': [],
        'value': {
            'specify': {
                'comments': [],
                'value': {
                    'question6c': {
                        'comments': [],
                        'value': 'I used a method of correction for multiple tests',
                        'extra': []
                    },
                    'question8c': {
                        'comments': [],
                        'value': 'reliability criteria',
                        'extra': []
                    },
                    'question9c': {
                        'comments': [],
                        'value': 'these are the anticipated data transformations',
                        'extra': []
                    },
                    'question7c': {
                        'comments': [],
                        'value': 'method of missing data handling',
                        'extra': []
                    },
                    'question11c': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question10c': {
                        'comments': [],
                        'value': 'assumptions of analysses',
                        'extra': []
                    }
                },
                'extra': []
            }
        },
        'extra': []
    },
    'description-hypothesis': {
        'comments': [],
        'value': {
            'question2a': {
                'comments': [],
                'value': 'expected interaction shape',
                'extra': []
            },
            'question1a': {
                'comments': [],
                'value': 'These are the essential elements',
                'extra': []
            },
            'question3a': {
                'comments': [],
                'value': 'predictions for successful checks',
                'extra': []
            }
        },
        'extra': []
    },
    'confirmatory-analyses-first': {
        'comments': [],
        'value': {
            'first': {
                'comments': [],
                'value': {
                    'question4c': {
                        'comments': [],
                        'value': 'this the covariate rationale',
                        'extra': []
                    },
                    'question5c': {
                        'comments': [],
                        'value': 'these are techniques for null hypo testing',
                        'extra': []
                    },
                    'question2c': {
                        'comments': [],
                        'value': 'this is the statistical technicque',
                        'extra': []
                    },
                    'question3c': {
                        'comments': [],
                        'value': 'this is each variable role',
                        'extra': []
                    },
                    'question1c': {
                        'comments': [],
                        'value': 'these are the relevant variables',
                        'extra': []
                    }
                },
                'extra': []
            }
        },
        'extra': []
    },
    'confirmatory-analyses-third': {
        'comments': [],
        'value': {
            'third': {
                'comments': [],
                'value': {
                    'question4c': {
                        'comments': [],
                        'value': 'here was the rationale',
                        'extra': []
                    },
                    'question5c': {
                        'comments': [],
                        'value': 'I used BAYESIAN STATISTICS',
                        'extra': []
                    },
                    'question2c': {
                        'comments': [],
                        'value': 't-test',
                        'extra': []
                    },
                    'question3c': {
                        'comments': [],
                        'value': 't-test informed covariate',
                        'extra': []
                    },
                    'question1c': {
                        'comments': [],
                        'value': '3rd prediction',
                        'extra': []
                    }
                },
                'extra': []
            }
        },
        'extra': []
    },
    'datacompletion': {
        'comments': [],
        'value': 'No, data collection has not begun',
        'extra': []
    },
    'looked': {
        'comments': [],
        'value': 'Yes',
        'extra': []
    },
    'confirmatory-analyses-fourth': {
        'comments': [],
        'value': {
            'fourth': {
                'comments': [],
                'value': {
                    'question4c': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question5c': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question2c': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question3c': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question1c': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    }
                },
                'extra': []
            }
        },
        'extra': []
    },
    'confirmatory-analyses-further': {
        'comments': [],
        'value': {
            'further': {
                'comments': [],
                'value': {
                    'question4c': {
                        'comments': [],
                        'value': 'this was the rationale',
                        'extra': []
                    },
                    'question5c': {
                        'comments': [],
                        'value': 'also Bayesian',
                        'extra': []
                    },
                    'question2c': {
                        'comments': [],
                        'value': 'i used a common statistical technique',
                        'extra': []
                    },
                    'question3c': {
                        'comments': [],
                        'value': 'this was the independent variable',
                        'extra': []
                    },
                    'question1c': {
                        'comments': [],
                        'value': 'FURTHER PREdictions:',
                        'extra': []
                    }
                },
                'extra': []
            }
        },
        'extra': []
    },
    'recommended-hypothesis': {
        'comments': [],
        'value': {
            'question5a': {
                'comments': [],
                'value': 'This is the hypotheses that was tested.',
                'extra': []
            },
            'question4a': {
                'comments': [],
                'value': 'Alphabet.txt',
                'extra': [
                    {
                        'descriptionValue': '',
                        'nodeId': '9bknu',
                        'viewUrl': '/project/85qku/files/osfstorage/5d6d25024d476c088fb8e03b/',
                        'selectedFileName': 'Alphabet.txt',
                        'sha256': 'asdf',
                        'data': {
                            'links': {
                                'download': 'http://localhost:7777/v1/resources/9bknu/providers/osfstorage/5d6d215b4d476c088fb8e000',
                                'move': 'http://localhost:7777/v1/resources/9bknu/providers/osfstorage/5d6d215b4d476c088fb8e000',
                                'upload': 'http://localhost:7777/v1/resources/9bknu/providers/osfstorage/5d6d215b4d476c088fb8e000?kind=file',
                                'delete': 'http://localhost:7777/v1/resources/9bknu/providers/osfstorage/5d6d215b4d476c088fb8e000'
                            },
                            'extra': {
                                'downloads': 0,
                                'latestVersionSeen': '',
                                'version': 1,
                                'hashes': {
                                    'sha256': 'asdf',
                                    'md5': 'asd'
                                },
                                'guid': '',
                                'checkout': ''
                            },
                            'accept': {
                                'acceptedFiles': 'True',
                                'maxSize': 5120
                            },
                            'id': 'osfstorage/5d6d215b4d476c088fb8e000',
                            'size': 3169,
                            'nodeApiUrl': '/api/v1/project/9bknu/',
                            'nodeId': '9bknu',
                            'etag': 'b529584199f707abda42a42ec2f3c5a052d280e56fb3382f07efc77933053159',
                            'provider': 'osfstorage',
                            'type': 'files',
                            'nodeUrl': '/9bknu/',
                            'sizeInt': 3169,
                            'contentType': '',
                            'path': '/5d6d215b4d476c088fb8e000',
                            'permissions': {
                                'edit': 'True',
                                'view': 'True'
                            },
                            'waterbutlerURL': 'http://localhost:7777',
                            'kind': 'file',
                            'resource': '9bknu',
                            'name': 'Alphabet.txt',
                            'materialized': '/Alphabet.txt',
                            'created_utc': '2019-09-02T14:04:14.776301+00:00',
                            'modified': '2019-09-02T14:04:14.776301+00:00',
                            'modified_utc': '2019-09-02T14:04:14.776301+00:00'
                        },
                        'fileId': '7ry42'
                    },
                    {
                        'descriptionValue': '',
                        'nodeId': '9bknu',
                        'viewUrl': '/project/85qku/files/osfstorage/5d6d25014d476c088fb8e038/',
                        'selectedFileName': 'Screen Shot 2019-08-30 at 9.04.01 AM.png',
                        'sha256': 'asdf',
                        'data': {
                            'links': {
                                'download': 'http://localhost:7777/v1/resources/9bknu/providers/osfstorage/5d6d217f4d476c088fb8e00d',
                                'move': 'http://localhost:7777/v1/resources/9bknu/providers/osfstorage/5d6d217f4d476c088fb8e00d',
                                'upload': 'http://localhost:7777/v1/resources/9bknu/providers/osfstorage/5d6d217f4d476c088fb8e00d?kind=file',
                                'delete': 'http://localhost:7777/v1/resources/9bknu/providers/osfstorage/5d6d217f4d476c088fb8e00d'
                            },
                            'extra': {
                                'downloads': 0,
                                'latestVersionSeen': '',
                                'version': 1,
                                'hashes': {
                                    'sha256': 'asdf',
                                    'md5': 'asd'
                                },
                                'guid': '',
                                'checkout': ''
                            },
                            'accept': {
                                'acceptedFiles': 'True',
                                'maxSize': 5120
                            },
                            'id': 'osfstorage/5d6d217f4d476c088fb8e00d',
                            'size': 78257,
                            'nodeApiUrl': '/api/v1/project/9bknu/',
                            'nodeId': '9bknu',
                            'etag': 'd114466ad8f1e04c03e678fdaf642988c1accd1526bb6e81b34bf35612a77cbb',
                            'provider': 'osfstorage',
                            'type': 'files',
                            'nodeUrl': '/9bknu/',
                            'sizeInt': 78257,
                            'contentType': '',
                            'path': '/5d6d217f4d476c088fb8e00d',
                            'permissions': {
                                'edit': 'True',
                                'view': 'True'
                            },
                            'waterbutlerURL': 'http://localhost:7777',
                            'kind': 'file',
                            'resource': '9bknu',
                            'name': 'Screen Shot 2019-08-30 at 9.04.01 AM.png',
                            'materialized': '/Screen Shot 2019-08-30 at 9.04.01 AM.png',
                            'created_utc': '2019-09-02T14:04:47.793337+00:00',
                            'modified': '2019-09-02T14:04:47.793337+00:00',
                            'modified_utc': '2019-09-02T14:04:47.793337+00:00'
                        },
                        'fileId': 'nc8qy'
                    }
                ]
            },
            'question6a': {
                'comments': [],
                'value': 'this is the outcome that would be predicted by each theory',
                'extra': []
            }
        },
        'extra': []
    },
    'additionalComments': {
        'comments': [],
        'value': 'no additional comments',
        'extra': []
    },
    'confirmatory-analyses-second': {
        'comments': [],
        'value': {
            'second': {
                'comments': [],
                'value': {
                    'question4c': {
                        'comments': [],
                        'value': 'here is the rationale',
                        'extra': []
                    },
                    'question5c': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question2c': {
                        'comments': [],
                        'value': 'ANOVA test',
                        'extra': []
                    },
                    'question3c': {
                        'comments': [],
                        'value': 'it was the covariate',
                        'extra': []
                    },
                    'question1c': {
                        'comments': [],
                        'value': 'how 2nd prediction calculated',
                        'extra': []
                    }
                },
                'extra': []
            }
        },
        'extra': []
    },
    'recommended-methods': {
        'comments': [],
        'value': {
            'procedure': {
                'comments': [],
                'value': {
                    'question9b-file': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question9b': {
                        'comments': [],
                        'value': 'set fail-safe levels of exclusions',
                        'extra': []
                    }
                },
                'extra': []
            }
        },
        'extra': []
    }
}

veer_condensed = {
    'dataCollectionDates': {
        'comments': [],
        'value': '2020 - 2030',
        'extra': []
    },
    'description-methods': {
        'value': {
            'exclusion-criteria': {
                'value': {
                    'question8b': {
                        'comments': [],
                        'value': 'these are failing check-tests',
                        'extra': []
                    }
                },
            },
            'design': {
                'value': {
                    'question2a': {
                        'comments': [],
                        'value': 'a. whether they are between participants',
                        'extra': []
                    },
                    'question2b': {
                        'comments': [],
                        'value': 'these are my dependent variables',
                        'extra': []
                    },
                    'question3b': {
                        'comments': [],
                        'value': 'These variables are acting as covariates.',
                        'extra': []
                    }
                },
            },
            'procedure': {
                'value': {
                    'question10b': {
                        'comments': [],
                        'value': 'describe all manipulations',
                        'extra': []
                    }
                },
            },
            'planned-sample': {
                'value': {
                    'question4b': {
                        'comments': [],
                        'value': 'these are the preselection rults',
                        'extra': []
                    },
                    'question7b': {
                        'comments': [],
                        'value': 'here is my data collection termination rule',
                        'extra': []
                    },
                    'question5b': {
                        'comments': [],
                        'value': 'here is how the data will be collected',
                        'extra': []
                    },
                    'question6b-upload': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question6b': {
                        'comments': [],
                        'value': 'this is my planned sample size',
                        'extra': []
                    }
                },
            }
        },
    },
    'recommended-analysis': {
        'value': {
            'specify': {
                'value': {
                    'question6c': {
                        'comments': [],
                        'value': 'I used a method of correction for multiple tests',
                        'extra': []
                    },
                    'question8c': {
                        'comments': [],
                        'value': 'reliability criteria',
                        'extra': []
                    },
                    'question9c': {
                        'comments': [],
                        'value': 'these are the anticipated data transformations',
                        'extra': []
                    },
                    'question7c': {
                        'comments': [],
                        'value': 'method of missing data handling',
                        'extra': []
                    },
                    'question11c': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question10c': {
                        'comments': [],
                        'value': 'assumptions of analysses',
                        'extra': []
                    }
                },
            }
        },
    },
    'description-hypothesis': {
        'value': {
            'question2a': {
                'comments': [],
                'value': 'expected interaction shape',
                'extra': []
            },
            'question1a': {
                'comments': [],
                'value': 'These are the essential elements',
                'extra': []
            },
            'question3a': {
                'comments': [],
                'value': 'predictions for successful checks',
                'extra': []
            }
        },
    },
    'confirmatory-analyses-first': {
        'value': {
            'first': {
                'value': {
                    'question4c': {
                        'comments': [],
                        'value': 'this the covariate rationale',
                        'extra': []
                    },
                    'question5c': {
                        'comments': [],
                        'value': 'these are techniques for null hypo testing',
                        'extra': []
                    },
                    'question2c': {
                        'comments': [],
                        'value': 'this is the statistical technicque',
                        'extra': []
                    },
                    'question3c': {
                        'comments': [],
                        'value': 'this is each variable role',
                        'extra': []
                    },
                    'question1c': {
                        'comments': [],
                        'value': 'these are the relevant variables',
                        'extra': []
                    }
                },
            }
        },
    },
    'confirmatory-analyses-third': {
        'value': {
            'third': {
                'value': {
                    'question4c': {
                        'comments': [],
                        'value': 'here was the rationale',
                        'extra': []
                    },
                    'question5c': {
                        'comments': [],
                        'value': 'I used BAYESIAN STATISTICS',
                        'extra': []
                    },
                    'question2c': {
                        'comments': [],
                        'value': 't-test',
                        'extra': []
                    },
                    'question3c': {
                        'comments': [],
                        'value': 't-test informed covariate',
                        'extra': []
                    },
                    'question1c': {
                        'comments': [],
                        'value': '3rd prediction',
                        'extra': []
                    }
                },
            }
        },
    },
    'datacompletion': {
        'comments': [],
        'value': 'No, data collection has not begun',
        'extra': []
    },
    'looked': {
        'comments': [],
        'value': 'Yes',
        'extra': []
    },
    'confirmatory-analyses-fourth': {
        'value': {
            'fourth': {
                'value': {
                    'question4c': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question5c': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question2c': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question3c': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question1c': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    }
                },
            }
        },
    },
    'confirmatory-analyses-further': {
        'value': {
            'further': {
                'value': {
                    'question4c': {
                        'comments': [],
                        'value': 'this was the rationale',
                        'extra': []
                    },
                    'question5c': {
                        'comments': [],
                        'value': 'also Bayesian',
                        'extra': []
                    },
                    'question2c': {
                        'comments': [],
                        'value': 'i used a common statistical technique',
                        'extra': []
                    },
                    'question3c': {
                        'comments': [],
                        'value': 'this was the independent variable',
                        'extra': []
                    },
                    'question1c': {
                        'comments': [],
                        'value': 'FURTHER PREdictions:',
                        'extra': []
                    }
                },
            }
        },
    },
    'recommended-hypothesis': {
        'value': {
            'question5a': {
                'comments': [],
                'value': 'This is the hypotheses that was tested.',
                'extra': []
            },
            'question4a': {
                'comments': [],
                'value': '',
                'extra': [
                    {
                        'selectedFileName': 'Alphabet.txt',
                        'viewUrl': '/project/85qku/files/osfstorage/5d6d25024d476c088fb8e03b',
                        'sha256': 'asdf',
                        'nodeId': '85qku',
                        'data': {
                            'name': 'Alphabet.txt',
                        },
                    },
                    {
                        'selectedFileName': 'Screen Shot 2019-08-30 at 9.04.01 AM.png',
                        'viewUrl': '/project/85qku/files/osfstorage/5d6d25014d476c088fb8e038',
                        'sha256': 'asdf',
                        'nodeId': '85qku',
                        'data': {
                            'name': 'Screen Shot 2019-08-30 at 9.04.01 AM.png'
                        }
                    }
                ]
            },
            'question6a': {
                'comments': [],
                'value': 'this is the outcome that would be predicted by each theory',
                'extra': []
            }
        },
    },
    'additionalComments': {
        'comments': [],
        'value': 'no additional comments',
        'extra': []
    },
    'confirmatory-analyses-second': {
        'value': {
            'second': {
                'value': {
                    'question4c': {
                        'comments': [],
                        'value': 'here is the rationale',
                        'extra': []
                    },
                    'question5c': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question2c': {
                        'comments': [],
                        'value': 'ANOVA test',
                        'extra': []
                    },
                    'question3c': {
                        'comments': [],
                        'value': 'it was the covariate',
                        'extra': []
                    },
                    'question1c': {
                        'comments': [],
                        'value': 'how 2nd prediction calculated',
                        'extra': []
                    }
                },
            }
        },
    },
    'recommended-methods': {
        'value': {
            'procedure': {
                'value': {
                    'question9b-file': {
                        'comments': [],
                        'value': '',
                        'extra': []
                    },
                    'question9b': {
                        'comments': [],
                        'value': 'set fail-safe levels of exclusions',
                        'extra': []
                    }
                },
            }
        },
    }
}

veer_registration_responses = {
    'confirmatory-analyses-third.third.question4c': 'here was the rationale',
    'recommended-hypothesis.question5a': 'This is the hypotheses that was tested.',
    'confirmatory-analyses-further.further.question4c': 'this was the rationale',
    'confirmatory-analyses-fourth.fourth.question5c': '',
    'description-methods.design.question3b': 'These variables are acting as covariates.',
    'confirmatory-analyses-further.further.question2c': 'i used a common statistical technique',
    'description-methods.exclusion-criteria.question8b': 'these are failing check-tests',
    'description-methods.planned-sample.question4b': 'these are the preselection rults',
    'confirmatory-analyses-second.second.question3c': 'it was the covariate',
    'dataCollectionDates': '2020 - 2030',
    'recommended-analysis.specify.question6c': 'I used a method of correction for multiple tests',
    'confirmatory-analyses-first.first.question2c': 'this is the statistical technicque',
    'description-methods.procedure.question10b': 'describe all manipulations',
    'recommended-analysis.specify.question11c': [],
    'recommended-methods.procedure.question9b': 'set fail-safe levels of exclusions',
    'description-hypothesis.question2a': 'expected interaction shape',
    'confirmatory-analyses-second.second.question5c': '',
    'confirmatory-analyses-first.first.question4c': 'this the covariate rationale',
    'description-methods.planned-sample.question6b': 'this is my planned sample size',
    'confirmatory-analyses-third.third.question1c': '3rd prediction',
    'confirmatory-analyses-fourth.fourth.question1c': '',
    'recommended-analysis.specify.question9c': 'these are the anticipated data transformations',
    'confirmatory-analyses-fourth.fourth.question2c': '',
    'confirmatory-analyses-third.third.question3c': 't-test informed covariate',
    'recommended-hypothesis.question6a': 'this is the outcome that would be predicted by each theory',
    'confirmatory-analyses-fourth.fourth.question4c': '',
    'confirmatory-analyses-second.second.question4c': 'here is the rationale',
    'recommended-hypothesis.question4a': [
        {
            'file_name': 'Alphabet.txt',
            'file_id': '5d6d25024d476c088fb8e03b',
            'file_urls': {
                'html': urljoin(settings.DOMAIN, '/project/85qku/files/osfstorage/5d6d25024d476c088fb8e03b'),
            },
            'file_hashes': {
                'sha256': 'asdf',
            },
        },
        {
            'file_name': 'Screen Shot 2019-08-30 at 9.04.01 AM.png',
            'file_id': '5d6d25014d476c088fb8e038',
            'file_urls': {
                'html': urljoin(settings.DOMAIN, '/project/85qku/files/osfstorage/5d6d25014d476c088fb8e038'),
            },
            'file_hashes': {
                'sha256': 'asdf',
            },
        }
    ],
    'confirmatory-analyses-third.third.question5c': 'I used BAYESIAN STATISTICS',
    'description-methods.design.question2b': 'these are my dependent variables',
    'description-methods.design.question2a': 'a. whether they are between participants',
    'datacompletion': 'No, data collection has not begun',
    'description-methods.planned-sample.question5b': 'here is how the data will be collected',
    'confirmatory-analyses-further.further.question3c': 'this was the independent variable',
    'confirmatory-analyses-further.further.question1c': 'FURTHER PREdictions:',
    'confirmatory-analyses-second.second.question2c': 'ANOVA test',
    'additionalComments': 'no additional comments',
    'confirmatory-analyses-first.first.question1c': 'these are the relevant variables',
    'recommended-analysis.specify.question7c': 'method of missing data handling',
    'confirmatory-analyses-first.first.question3c': 'this is each variable role',
    'description-hypothesis.question3a': 'predictions for successful checks',
    'confirmatory-analyses-further.further.question5c': 'also Bayesian',
    'recommended-analysis.specify.question10c': 'assumptions of analysses',
    'recommended-methods.procedure.question9b-file': [],
    'description-hypothesis.question1a': 'These are the essential elements',
    'description-methods.planned-sample.question7b': 'here is my data collection termination rule',
    'confirmatory-analyses-first.first.question5c': 'these are techniques for null hypo testing',
    'looked': 'Yes',
    'confirmatory-analyses-second.second.question1c': 'how 2nd prediction calculated',
    'confirmatory-analyses-third.third.question2c': 't-test',
    'confirmatory-analyses-fourth.fourth.question3c': '',
    'recommended-analysis.specify.question8c': 'reliability criteria',
    'description-methods.planned-sample.question6b-upload': []
}


@pytest.fixture()
def osf_standard_schema():
    return RegistrationSchema.objects.get(
        name='OSF-Standard Pre-Data Collection Registration',
        schema_version=2
    )

@pytest.fixture()
def prereg_schema():
    return RegistrationSchema.objects.get(
        name='Prereg Challenge',
        schema_version=2
    )

@pytest.fixture()
def veer_schema():
    return RegistrationSchema.objects.get(
        name__icontains='Pre-Registration in Social Psychology',
        schema_version=2
    )


@pytest.mark.django_db
class TestMigrateDraftRegistrationRegistrationResponses:

    @pytest.fixture()
    def draft_osf_standard(self, osf_standard_schema):
        draft = DraftRegistrationFactory(
            registration_schema=osf_standard_schema,
            registration_metadata={
                'looked': {
                    'comments': [],
                    'value': 'Yes',
                    'extra': []
                },
                'datacompletion': {
                    'comments': [],
                    'value': 'No, data collection has not begun',
                    'extra': []
                },
                'comments': {
                    'comments': [],
                    'value': 'more comments',
                    'extra': []
                }
            }
        )
        draft.registration_responses = {}
        draft.save()
        return draft

    @pytest.fixture()
    def empty_draft_osf_standard(self, osf_standard_schema):
        draft = DraftRegistrationFactory(
            registration_schema=osf_standard_schema,
            registration_metadata={}
        )
        draft.registration_responses = {}
        draft.registration_responses_migrated = False
        draft.save()
        return draft

    @pytest.fixture()
    def draft_prereg(self, prereg_schema):
        draft = DraftRegistrationFactory(
            registration_schema=prereg_schema,
            registration_metadata=prereg_registration_metadata
        )
        draft.registration_responses = {}
        draft.registration_responses_migrated = False
        draft.save()
        return draft

    @pytest.fixture()
    def draft_veer(self, veer_schema):
        draft = DraftRegistrationFactory(
            registration_schema=veer_schema,
            registration_metadata=veer_registration_metadata
        )
        draft.registration_responses = {}
        draft.registration_responses_migrated = False
        draft.save()
        return draft

    def test_migrate_empty_draft(self, app, empty_draft_osf_standard):
        assert empty_draft_osf_standard.registration_responses == {}
        assert empty_draft_osf_standard.registration_responses_migrated is False

        migrate_draft_registrations(dry_run=False)

        empty_draft_osf_standard.reload()
        assert empty_draft_osf_standard.registration_responses_migrated is True
        responses = empty_draft_osf_standard.registration_responses
        assert responses['looked'] == ''
        assert responses['datacompletion'] == ''
        assert responses['comments'] == ''

    def test_migrate_draft_registrations(self, app, draft_osf_standard, draft_prereg, draft_veer):
        drafts = [
            draft_osf_standard,
            draft_prereg,
            draft_veer
        ]

        for draft in drafts:
            assert draft.registration_responses == {}
            draft.registration_responses_migrated = False
            draft.save()

        migrate_draft_registrations(dry_run=False)

        # Verifying OSF Standard Migration
        draft_osf_standard.reload()
        assert draft_osf_standard.registration_responses_migrated is True
        responses = draft_osf_standard.registration_responses
        assert responses['looked'] == 'Yes'
        assert responses['datacompletion'] == 'No, data collection has not begun'
        assert responses['comments'] == 'more comments'

        # Verifying Prereg Migration
        draft_prereg.reload()
        assert draft_prereg.registration_responses_migrated is True
        responses = draft_prereg.registration_responses
        assert responses['q12.uploader'] == []
        assert responses['q7.question'] == 'data collection procedures'
        assert responses['q21'] == 'research plan follow up'
        assert responses['q22'] == 'criteria'
        assert responses['q23'] == 'this is how outliers will be handled'
        assert responses['q24'] == 'this is how I will deal with incomplete data.'
        assert responses['q25'] == 'this is my exploratory analysis'
        assert responses['q26'] == []
        assert responses['q27'] == 'No additional comments'
        assert responses['q12.question'] == 'these are my measured variables'
        assert responses['q1'] == 'This is my title'
        assert responses['q3'] == 'research questions'
        assert responses['q5'] == 'Registration prior to creation of data'
        assert responses['q4'] == 'this is my hypothesis'
        assert responses['q6'] == 'Explanation of existing data'
        assert responses['q9'] == 'this is the rationale for my sample size'
        assert responses['q8'] == 'this is my sample size'
        assert responses['q13.question'] == 'these are my indices'
        assert responses['q19.uploader'] == []
        assert responses['q11.uploader'] == [
            {
                'file_name': 'Screen Shot 2019-08-30 at 9.04.01 AM.png',
                'file_id': '5d6d22264d476c088fb8e01f',
                'file_urls': {
                    'html': urljoin(settings.DOMAIN, '/project/57zbh/files/osfstorage/5d6d22264d476c088fb8e01f'),
                    'download': urljoin(settings.DOMAIN, '/download/5d6d22264d476c088fb8e01f'),
                },
                'file_hashes': {
                    'sha256': 'sdf',
                },
            },
            {
                'file_name': 'Alphabet.txt',
                'file_id': '5d6d22274d476c088fb8e021',
                'file_urls': {
                    'html': urljoin(settings.DOMAIN, '/project/57zbh/files/osfstorage/5d6d22274d476c088fb8e021'),
                    'download': urljoin(settings.DOMAIN, '/download/5d6d22274d476c088fb8e021'),
                },
                'file_hashes': {
                    'sha256': 'asdf',
                },
            }
        ]
        assert responses['q16.question'] == 'this is my study design'
        assert responses['q15'] == [
            'No blinding is involved in this study.',
            'For studies that involve human subjects, they will not know the treatment group to which they have been assigned.',
            'Research personnel who interact directly with the study subjects (either human or non-human subjects) will not be aware of the assigned treatments.'
        ]
        assert responses['q14'] == ''
        assert responses['q17'] == 'this is my explanation of randomization'
        assert responses['q10'] == 'this is my stopping rule'
        assert responses['q11.question'] == 'these are my maniuplated variables'
        assert responses['q16.uploader'] == []
        assert responses['q19.question'] == 'ANOVA'
        assert responses['q13.uploader'] == []
        assert responses['q7.uploader'] == [
            {
                'file_name': 'Alphabet.txt',
                'file_id': '5d6d22274d476c088fb8e021',
                'file_urls': {
                    'html': urljoin(settings.DOMAIN, '/project/57zbh/files/osfstorage/5d6d22274d476c088fb8e021'),
                    'download': urljoin(settings.DOMAIN, '/download/5d6d22274d476c088fb8e021'),
                },
                'file_hashes': {
                    'sha256': 'dsdfds'
                },
            }
        ]

        # Verifying Veer Migration
        draft_veer.reload()
        assert draft_veer.registration_responses_migrated is True
        responses = draft_veer.registration_responses
        assert responses['confirmatory-analyses-third.third.question4c'] == 'here was the rationale'
        assert responses['recommended-hypothesis.question5a'] == 'This is the hypotheses that was tested.'
        assert responses['confirmatory-analyses-further.further.question4c'] == 'this was the rationale'
        assert responses['confirmatory-analyses-fourth.fourth.question5c'] == ''
        assert responses['description-methods.design.question3b'] == 'These variables are acting as covariates.'
        assert responses['confirmatory-analyses-second.second.question1c'] == 'how 2nd prediction calculated'
        assert responses['description-methods.exclusion-criteria.question8b'] == 'these are failing check-tests'
        assert responses['description-methods.planned-sample.question4b'] == 'these are the preselection rults'
        assert responses['confirmatory-analyses-second.second.question3c'] == 'it was the covariate'
        assert responses['recommended-analysis.specify.question6c'] == 'I used a method of correction for multiple tests'
        assert responses['confirmatory-analyses-first.first.question2c'] == 'this is the statistical technicque'
        assert responses['description-methods.procedure.question10b'] == 'describe all manipulations'
        assert responses['recommended-analysis.specify.question11c'] == []
        assert responses['recommended-methods.procedure.question9b'] == 'set fail-safe levels of exclusions'
        assert responses['description-hypothesis.question2a'] == 'expected interaction shape'
        assert responses['confirmatory-analyses-second.second.question5c'] == ''
        assert responses['confirmatory-analyses-first.first.question4c'] == 'this the covariate rationale'
        assert responses['description-methods.planned-sample.question6b'] == 'this is my planned sample size'
        assert responses['confirmatory-analyses-third.third.question1c'] == '3rd prediction'
        assert responses['recommended-analysis.specify.question9c'] == 'these are the anticipated data transformations'
        assert responses['confirmatory-analyses-fourth.fourth.question2c'] == ''
        assert responses['confirmatory-analyses-third.third.question3c'] == 't-test informed covariate'
        assert responses['recommended-hypothesis.question6a'] == 'this is the outcome that would be predicted by each theory'
        assert responses['confirmatory-analyses-fourth.fourth.question4c'] == ''
        assert responses['confirmatory-analyses-second.second.question4c'] == 'here is the rationale'
        assert responses['recommended-hypothesis.question4a'] == [
            {
                'file_name': 'Alphabet.txt',
                'file_id': '5d6d25024d476c088fb8e03b',
                'file_urls': {
                    'html': urljoin(settings.DOMAIN, '/project/85qku/files/osfstorage/5d6d25024d476c088fb8e03b'),
                    'download': urljoin(settings.DOMAIN, '/download/5d6d25024d476c088fb8e03b'),
                },
                'file_hashes': {
                    'sha256': 'asdf',
                },
            },
            {
                'file_name': 'Screen Shot 2019-08-30 at 9.04.01 AM.png',
                'file_id': '5d6d25014d476c088fb8e038',
                'file_urls': {
                    'html': urljoin(settings.DOMAIN, '/project/85qku/files/osfstorage/5d6d25014d476c088fb8e038'),
                    'download': urljoin(settings.DOMAIN, '/download/5d6d25014d476c088fb8e038'),
                },
                'file_hashes': {
                    'sha256': 'asdf',
                },
            }
        ]
        assert responses['confirmatory-analyses-third.third.question5c'] == 'I used BAYESIAN STATISTICS'
        assert responses['description-methods.design.question2b'] == 'these are my dependent variables'
        assert responses['description-methods.design.question2a'] == 'a. whether they are between participants'
        assert responses['datacompletion'] == 'No, data collection has not begun'
        assert responses['description-methods.planned-sample.question5b'] == 'here is how the data will be collected'
        assert responses['confirmatory-analyses-further.further.question3c'] == 'this was the independent variable'
        assert responses['confirmatory-analyses-further.further.question1c'] == 'FURTHER PREdictions:'
        assert responses['confirmatory-analyses-second.second.question2c'] == 'ANOVA test'
        assert responses['additionalComments'] == 'no additional comments'
        assert responses['looked'] == 'Yes'
        assert responses['confirmatory-analyses-first.first.question1c'] == 'these are the relevant variables'
        assert responses['recommended-analysis.specify.question7c'] == 'method of missing data handling'
        assert responses['confirmatory-analyses-first.first.question3c'] == 'this is each variable role'
        assert responses['description-hypothesis.question3a'] == 'predictions for successful checks'
        assert responses['confirmatory-analyses-further.further.question2c'] == 'i used a common statistical technique'
        assert responses['confirmatory-analyses-further.further.question5c'] == 'also Bayesian'
        assert responses['recommended-analysis.specify.question10c'] == 'assumptions of analysses'
        assert responses['recommended-methods.procedure.question9b-file'] == []
        assert responses['description-hypothesis.question1a'] == 'These are the essential elements'
        assert responses['description-methods.planned-sample.question7b'] == 'here is my data collection termination rule'
        assert responses['confirmatory-analyses-first.first.question5c'] == 'these are techniques for null hypo testing'
        assert responses['dataCollectionDates'] == '2020 - 2030'
        assert responses['confirmatory-analyses-fourth.fourth.question1c'] == ''
        assert responses['confirmatory-analyses-third.third.question2c'] == 't-test'
        assert responses['confirmatory-analyses-fourth.fourth.question3c'] == ''
        assert responses['recommended-analysis.specify.question8c'] == 'reliability criteria'
        assert responses['description-methods.planned-sample.question6b-upload'] == []


@pytest.mark.django_db
class TestMigrateRegistrationRegistrationResponses:

    @pytest.fixture()
    def reg_osf_standard(self, osf_standard_schema):
        draft = DraftRegistrationFactory(
            registration_schema=osf_standard_schema,
            registration_metadata={
                'looked': {
                    'comments': [],
                    'value': 'Yes',
                    'extra': []
                },
                'datacompletion': {
                    'comments': [],
                    'value': 'No, data collection has not begun',
                    'extra': []
                },
                'comments': {
                    'comments': [],
                    'value': 'more comments',
                    'extra': []
                }
            }
        )
        return RegistrationFactory(
            schema=osf_standard_schema,
            draft_registration=draft,
            project=draft.branched_from
        )

    @pytest.fixture()
    def reg_prereg(self, prereg_schema):
        draft = DraftRegistrationFactory(
            registration_schema=prereg_schema,
            registration_metadata=prereg_registration_metadata
        )
        return RegistrationFactory(
            schema=prereg_schema,
            draft_registration=draft,
            project=draft.branched_from
        )

    @pytest.fixture()
    def reg_veer(self, veer_schema):
        draft = DraftRegistrationFactory(
            registration_metadata=veer_registration_metadata,
            registration_schema=veer_schema,
        )
        return RegistrationFactory(
            schema=veer_schema,
            draft_registration=draft,
            project=draft.branched_from
        )

    def test_migrate_registrations(self, app, reg_osf_standard, reg_prereg, reg_veer):
        regs = [
            reg_osf_standard,
            reg_prereg,
            reg_veer
        ]

        for reg in regs:
            reg.registration_responses = {}
            reg.registration_responses_migrated = False
            reg.save()

        migrate_registrations(dry_run=False)

        # Verifying OSF Standard Migration
        reg_osf_standard.reload()
        assert reg_osf_standard.registration_responses_migrated is True
        responses = reg_osf_standard.registration_responses
        assert responses['looked'] == 'Yes'
        assert responses['datacompletion'] == 'No, data collection has not begun'
        assert responses['comments'] == 'more comments'

        # Verifying Prereg Migration
        reg_prereg.reload()
        assert reg_prereg.registration_responses_migrated is True
        responses = reg_prereg.registration_responses
        assert responses['q12.uploader'] == []
        assert responses['q7.question'] == 'data collection procedures'
        assert responses['q21'] == 'research plan follow up'
        assert responses['q22'] == 'criteria'
        assert responses['q23'] == 'this is how outliers will be handled'
        assert responses['q24'] == 'this is how I will deal with incomplete data.'
        assert responses['q25'] == 'this is my exploratory analysis'
        assert responses['q26'] == []
        assert responses['q27'] == 'No additional comments'
        assert responses['q12.question'] == 'these are my measured variables'
        assert responses['q1'] == 'This is my title'
        assert responses['q3'] == 'research questions'
        assert responses['q5'] == 'Registration prior to creation of data'
        assert responses['q4'] == 'this is my hypothesis'
        assert responses['q6'] == 'Explanation of existing data'
        assert responses['q9'] == 'this is the rationale for my sample size'
        assert responses['q8'] == 'this is my sample size'
        assert responses['q13.question'] == 'these are my indices'
        assert responses['q19.uploader'] == []
        assert responses['q11.uploader'] == [
            {
                'file_name': 'Screen Shot 2019-08-30 at 9.04.01 AM.png',
                'file_id': '5d6d22264d476c088fb8e01f',
                'file_urls': {
                    'html': urljoin(settings.DOMAIN, '/project/57zbh/files/osfstorage/5d6d22264d476c088fb8e01f'),
                    'download': urljoin(settings.DOMAIN, '/download/5d6d22264d476c088fb8e01f'),
                },
                'file_hashes': {
                    'sha256': 'sdf',
                },
            },
            {
                'file_name': 'Alphabet.txt',
                'file_id': '5d6d22274d476c088fb8e021',
                'file_urls': {
                    'html': urljoin(settings.DOMAIN, '/project/57zbh/files/osfstorage/5d6d22274d476c088fb8e021'),
                    'download': urljoin(settings.DOMAIN, '/download/5d6d22274d476c088fb8e021'),
                },
                'file_hashes': {
                    'sha256': 'asdf',
                },
            }
        ]
        assert responses['q16.question'] == 'this is my study design'
        assert responses['q15'] == [
            'No blinding is involved in this study.',
            'For studies that involve human subjects, they will not know the treatment group to which they have been assigned.',
            'Research personnel who interact directly with the study subjects (either human or non-human subjects) will not be aware of the assigned treatments.'
        ]
        assert responses['q14'] == ''
        assert responses['q17'] == 'this is my explanation of randomization'
        assert responses['q10'] == 'this is my stopping rule'
        assert responses['q11.question'] == 'these are my maniuplated variables'
        assert responses['q16.uploader'] == []
        assert responses['q19.question'] == 'ANOVA'
        assert responses['q13.uploader'] == []
        assert responses['q7.uploader'] == [
            {
                'file_name': 'Alphabet.txt',
                'file_id': '5d6d22274d476c088fb8e021',
                'file_urls': {
                    'html': urljoin(settings.DOMAIN, '/project/57zbh/files/osfstorage/5d6d22274d476c088fb8e021'),
                    'download': urljoin(settings.DOMAIN, '/download/5d6d22274d476c088fb8e021'),
                },
                'file_hashes': {
                    'sha256': 'dsdfds',
                },
            }
        ]

        # Verifying Veer Migration
        reg_veer.reload()
        assert reg_veer.registration_responses_migrated is True
        responses = reg_veer.registration_responses
        assert responses['confirmatory-analyses-third.third.question4c'] == 'here was the rationale'
        assert responses['recommended-hypothesis.question5a'] == 'This is the hypotheses that was tested.'
        assert responses['confirmatory-analyses-further.further.question4c'] == 'this was the rationale'
        assert responses['confirmatory-analyses-fourth.fourth.question5c'] == ''
        assert responses['description-methods.design.question3b'] == 'These variables are acting as covariates.'
        assert responses['confirmatory-analyses-second.second.question1c'] == 'how 2nd prediction calculated'
        assert responses['description-methods.exclusion-criteria.question8b'] == 'these are failing check-tests'
        assert responses['description-methods.planned-sample.question4b'] == 'these are the preselection rults'
        assert responses['confirmatory-analyses-second.second.question3c'] == 'it was the covariate'
        assert responses['recommended-analysis.specify.question6c'] == 'I used a method of correction for multiple tests'
        assert responses['confirmatory-analyses-first.first.question2c'] == 'this is the statistical technicque'
        assert responses['description-methods.procedure.question10b'] == 'describe all manipulations'
        assert responses['recommended-analysis.specify.question11c'] == []
        assert responses['recommended-methods.procedure.question9b'] == 'set fail-safe levels of exclusions'
        assert responses['description-hypothesis.question2a'] == 'expected interaction shape'
        assert responses['confirmatory-analyses-second.second.question5c'] == ''
        assert responses['confirmatory-analyses-first.first.question4c'] == 'this the covariate rationale'
        assert responses['description-methods.planned-sample.question6b'] == 'this is my planned sample size'
        assert responses['confirmatory-analyses-third.third.question1c'] == '3rd prediction'
        assert responses['recommended-analysis.specify.question9c'] == 'these are the anticipated data transformations'
        assert responses['confirmatory-analyses-fourth.fourth.question2c'] == ''
        assert responses['confirmatory-analyses-third.third.question3c'] == 't-test informed covariate'
        assert responses['recommended-hypothesis.question6a'] == 'this is the outcome that would be predicted by each theory'
        assert responses['confirmatory-analyses-fourth.fourth.question4c'] == ''
        assert responses['confirmatory-analyses-second.second.question4c'] == 'here is the rationale'
        assert responses['recommended-hypothesis.question4a'] == [
            {
                'file_name': 'Alphabet.txt',
                'file_id': '5d6d25024d476c088fb8e03b',
                'file_urls': {
                    'html': urljoin(settings.DOMAIN, '/project/85qku/files/osfstorage/5d6d25024d476c088fb8e03b'),
                    'download': urljoin(settings.DOMAIN, '/download/5d6d25024d476c088fb8e03b'),
                },
                'file_hashes': {
                    'sha256': 'asdf',
                },
            },
            {
                'file_name': 'Screen Shot 2019-08-30 at 9.04.01 AM.png',
                'file_id': '5d6d25014d476c088fb8e038',
                'file_urls': {
                    'html': urljoin(settings.DOMAIN, '/project/85qku/files/osfstorage/5d6d25014d476c088fb8e038'),
                    'download': urljoin(settings.DOMAIN, '/download/5d6d25014d476c088fb8e038'),
                },
                'file_hashes': {
                    'sha256': 'asdf',
                },
            }
        ]
        assert responses['confirmatory-analyses-third.third.question5c'] == 'I used BAYESIAN STATISTICS'
        assert responses['description-methods.design.question2b'] == 'these are my dependent variables'
        assert responses['description-methods.design.question2a'] == 'a. whether they are between participants'
        assert responses['datacompletion'] == 'No, data collection has not begun'
        assert responses['description-methods.planned-sample.question5b'] == 'here is how the data will be collected'
        assert responses['confirmatory-analyses-further.further.question3c'] == 'this was the independent variable'
        assert responses['confirmatory-analyses-further.further.question1c'] == 'FURTHER PREdictions:'
        assert responses['confirmatory-analyses-second.second.question2c'] == 'ANOVA test'
        assert responses['additionalComments'] == 'no additional comments'
        assert responses['looked'] == 'Yes'
        assert responses['confirmatory-analyses-first.first.question1c'] == 'these are the relevant variables'
        assert responses['recommended-analysis.specify.question7c'] == 'method of missing data handling'
        assert responses['confirmatory-analyses-first.first.question3c'] == 'this is each variable role'
        assert responses['description-hypothesis.question3a'] == 'predictions for successful checks'
        assert responses['confirmatory-analyses-further.further.question2c'] == 'i used a common statistical technique'
        assert responses['confirmatory-analyses-further.further.question5c'] == 'also Bayesian'
        assert responses['recommended-analysis.specify.question10c'] == 'assumptions of analysses'
        assert responses['recommended-methods.procedure.question9b-file'] == []
        assert responses['description-hypothesis.question1a'] == 'These are the essential elements'
        assert responses['description-methods.planned-sample.question7b'] == 'here is my data collection termination rule'
        assert responses['confirmatory-analyses-first.first.question5c'] == 'these are techniques for null hypo testing'
        assert responses['dataCollectionDates'] == '2020 - 2030'
        assert responses['confirmatory-analyses-fourth.fourth.question1c'] == ''
        assert responses['confirmatory-analyses-third.third.question2c'] == 't-test'
        assert responses['confirmatory-analyses-fourth.fourth.question3c'] == ''
        assert responses['recommended-analysis.specify.question8c'] == 'reliability criteria'
        assert responses['description-methods.planned-sample.question6b-upload'] == []
