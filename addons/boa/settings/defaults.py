# Not used currently, but may be expanded to accommodate other Boa databases in the future
DEFAULT_HOSTS = []

# Max file size allowed for submission
MAX_SUBMISSION_SIZE = 512 * 1024  # 512 KB

# Max time for Celery to wait for Boa to finish the job
MAX_JOB_WAITING_TIME = 24 * 60 * 60  # 24 hours

# Time to wait / sleep between job status check
REFRESH_JOB_INTERVAL = 10  # 10 seconds

# Suffix to replace '.boa' for the output file
OUTPUT_FILE_SUFFIX = '_results.txt'

BOA_DATASETS = [
    '2022 Jan/Java',
    '2022 Feb/Python',
    '2021 Method Chains',
    '2021 Aug/Python',
    '2021 Aug/Kotlin (small)',
    '2021 Aug/Kotlin',
    '2021 Jan/ML-Verse',
    '2020 August/Python-DS',
    '2019 October/GitHub (small)',
    '2019 October/GitHub (medium)',
    '2019 October/GitHub',
    '2015 September/GitHub',
    '2013 September/SF (small)',
    '2013 September/SF (medium)',
    '2013 September/SF',
    '2013 May/SF',
    '2013 February/SF',
    '2012 July/SF',
]

BOA_JOB_LIST_URL = 'https://boa.cs.iastate.edu/boa/index.php?q=boa/jobs'
BOA_SUPPORT_EMAIL = 'boasupport@iastate.edu'
