# from .active_users import ActiveUserReporter
from .storage_addon_usage import StorageAddonUsageReporter
from .download_count import DownloadCountReporter
from .institution_summary import InstitutionSummaryReporter
from .institution_dashboard_summary import InstitutionDashboardSummaryReport
from .new_user_domain import NewUserDomainReporter
from .node_count import NodeCountReporter
from .osfstorage_file_count import OsfstorageFileCountReporter
from .preprint_count import PreprintCountReporter
from .user_count import UserCountReporter
from .spam_count import SpamCountReporter


DAILY_REPORTERS = (
    # ActiveUserReporter,
    DownloadCountReporter,
    InstitutionSummaryReporter,
    InstitutionDashboardSummaryReport,
    NewUserDomainReporter,
    NodeCountReporter,
    OsfstorageFileCountReporter,
    PreprintCountReporter,
    StorageAddonUsageReporter,
    UserCountReporter,
)

MONTHLY_REPORTERS = (
    SpamCountReporter,
)
