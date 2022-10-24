# from .active_users import ActiveUserReporter
# from .addon_usage import AddonUsageReporter
from .download_count import DownloadCountReporter
from .institution_summary import InstitutionSummaryReporter
from .new_user_domain import NewUserDomainReporter
from .node_count import NodeCountReporter
from .osfstorage_file_count import OsfstorageFileCountReporter
from .preprint_count import PreprintCountReporter
from .user_count import UserCountReporter


DAILY_REPORTERS = (
    # ActiveUserReporter,
    # AddonUsageReporter,
    DownloadCountReporter,
    InstitutionSummaryReporter,
    NewUserDomainReporter,
    NodeCountReporter,
    OsfstorageFileCountReporter,
    PreprintCountReporter,
    UserCountReporter,
)
