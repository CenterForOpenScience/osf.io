from osf.models import DraftRegistration, MetaSchema
from admin.pre_reg.views import get_metadata_files


def draft_reg_util():
    DraftRegistration.objects.all().delete()
    return MetaSchema.objects.get(name='Prereg Challenge', schema_version=2)


def checkin_files(draft):
    if draft.approval_id:
        for item in get_metadata_files(draft):
            item.checkout = None
            item.save()


SCHEMA_DATA = {
    'q20': {
        'comments': [],
        'value': 'The Effect of sugar on brownie tastiness does not require any additional transformations. However, if it were using a regression analysis and each level of sweet had been categorically described (e.g. not sweet, somewhat sweet, sweet, and very sweet), sweet could be dummy coded with not sweet as the reference category.',
        'extra': {}
    },
    'q21': {
        'comments': [],
        'value': 'If the the ANOVA indicates that the mean taste perceptions are significantly different (p&lt;.05), then we will use a Tukey-Kramer HSD test to conduct all possible pairwise comparison.',
        'extra': {}
    },
    'q22': {
        'comments': [],
        'value': 'We will use the standard p&lt;.05 criteria for determining if the ANOVA and the post hoc test suggest that the results are significantly different from those expected if the null hypothesis were correct. The post-hoc Tukey-Kramer test adjusts for multiple comparisons.',
        'extra': {}
    },
    'q23': {
        'comments': [],
        'value': 'No checks will be performed to determine eligibility for inclusion besides verification that each subject answered each of the three tastiness indices. Outliers will be included in the analysis',
        'extra': {}
    },
    'q24': {
        'comments': [],
        'value': 'If a subject does not complete any of the three indices of tastiness, that subject will not be included in the analysis.',
        'extra': {}
    },
    'q25': {
        'comments': [],
        'value': '',
        'extra': {}
    },
    'q26': {
        'comments': [],
        'value': 'sugar_taste.R',
        'extra': {}
    },
    'q27': {
        'comments': [],
        'value': '',
        'extra': {}
    },
    'q1': {
        'comments': [],
        'value': 'Effect of sugar on brownie tastiness',
        'extra': {}
    },
    'q3': {
        'comments': [],
        'value': 'Though there is strong evidence to suggest that sugar affects taste preferences, the effect has never been demonstrated in brownies. Therefore, we will measure taste preference for four different levels of sugar concentration in a standard brownie recipe to determine if the effect exists in this pastry. ',
        'extra': {}
    },
    'q2': {
        'comments': [],
        'value': 'David Mellor, Jolene Esposito',
        'extra': {}
    },
    'q5': {
        'comments': [],
        'value': 'Registration prior to creation of data: As of the date of submission of this research plan for preregistration, the data have not yet been collected, created, or realized.',
        'extra': {}
    },
    'q4': {
        'comments': [],
        'value': 'If taste affects preference, then mean preference indices will be higher with higher concentrations of sugar.',
        'extra': {}
    },
    'q7': {
        'comments': [],
        'value': {
            'question': {
                'comments': [],
                'value': 'Participants will be recruited through advertisements at local pastry shops. Participants will be paid $10 for agreeing to participate (raised to $30 if our sample size is not reached within 15 days of beginning recruitment). Participants must be at least 18 years old and be able to eat the ingredients of the pastries.',
                'extra': {}
            },
            'uploader16': {
                'comments': [],
                'value': '',
                'extra': {}
            }
        },
        'extra': {}
    },
    'q6': {
        'comments': [],
        'value': 'Data do not yet exist',
        'extra': {}
    },
    'q9': {
        'comments': [],
        'value': 'We used the software program G*Power to conduct a power analysis. Our goal was to obtain .95 power to detect a medium effect size of .25 at the standard .05 alpha error probability. ',
        'extra': {}
    },
    'q8': {
        'comments': [],
        'value': 'Our target sample size is 280 participants. We will attempt to recruit up to 320, assuming that not all will complete the total task. ',
        'extra': {}
    },
    'q15': {
        'comments': [],
        'value': [
            'For studies that involve human subjects, they will not know the treatment group to which they have been assigned.'],
        'extra': {}
    },
    'q14': {
        'comments': [],
        'value': 'Experiment - A researcher randomly assigns treatments to study subjects, this includes field or lab experiments. This is also known as an intervention experiment and includes randomized controlled trials.',
        'extra': {}
    },
    'q17': {
        'comments': [],
        'value': 'We will use block randomization, where each participant will be randomly assigned to one of the four equally sized, predetermined blocks. The random number list used to create these four blocks will be created using the web applications available at http://random.org. ',
        'extra': {}
    },
    'q16': {
        'comments': [],
        'value': {
            'question': {
                'comments': [],
                'value': 'We have a between subjects design with 1 factor (sugar by mass) with 4 levels. ',
                'extra': {}
            },
            'uploader16': {
                'comments': [],
                'value': '',
                'extra': {}
            }
        },
        'extra': {}
    },
    'q11': {
        'comments': [],
        'value': 'We manipulated the percentage of sugar by mass added to brownies. The four levels of this categorical variable are: 15%, 20%, 25%, or 40% cane sugar by mass. ',
        'extra': {}
    },
    'q10': {
        'comments': [],
        'value': 'We will post participant sign-up slots by week on the preceding Friday night, with 20 spots posted per week. We will post 20 new slots each week if, on that Friday night, we are below 320 participants. ',
        'extra': {}
    },
    'q13': {
        'comments': [],
        'value': 'We will take the mean of the two questions above to create a single measure of brownie enjoyment.',
        'extra': {}
    },
    'q12': {
        'comments': [],
        'value': 'The single outcome variable will be the perceived tastiness of the single brownie each participant will eat. We will measure this by asking participants How much did you enjoy eating the brownie (on a scale of 1-7, 1 being not at all, 7 being a great deal) and How good did the brownie taste (on a scale of 1-7, 1 being very bad, 7 being very good). ',
        'extra': {}
    },
    'q19': {
        'comments': [],
        'value': {
            'q19a': {
                'value': "We will use a one-way between subjects ANOVA to analyze our results. The manipulated, categorical independent variable is 'sugar' whereas the dependent variable is our taste index. ",
                'extra': {}
            },
            'uploader19': {
                'value': '',
                'extra': {}
            },
        },
        'extra': {}
    }
}
