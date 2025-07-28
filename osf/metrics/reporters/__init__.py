import enum

# from .active_users import ActiveUserReporter
from .storage_addon_usage import StorageAddonUsageReporter
from .download_count import DownloadCountReporter
from .institution_summary import InstitutionSummaryReporter
from .institutional_users import InstitutionalUsersReporter
from .institution_summary_monthly import InstitutionalSummaryMonthlyReporter
from .new_user_domain import NewUserDomainReporter
from .node_count import NodeCountReporter
from .osfstorage_file_count import OsfstorageFileCountReporter
from .preprint_count import PreprintCountReporter
from .public_item_usage import PublicItemUsageReporter
from .user_count import UserCountReporter
from .spam_count import SpamCountReporter
from .private_spam_metrics import PrivateSpamMetricsReporter
from .notification_count import NotificationCountReporter


class AllDailyReporters(enum.Enum):
    # ACTIVE_USER = ActiveUserReporter
    DOWNLOAD_COUNT = DownloadCountReporter
    INSTITUTION_SUMMARY = InstitutionSummaryReporter
    NEW_USER_DOMAIN = NewUserDomainReporter
    NODE_COUNT = NodeCountReporter
    OSFSTORAGE_FILE_COUNT = OsfstorageFileCountReporter
    PREPRINT_COUNT = PreprintCountReporter
    STORAGE_ADDON_USAGE = StorageAddonUsageReporter
    USER_COUNT = UserCountReporter


class AllMonthlyReporters(enum.Enum):
    SPAM_COUNT = SpamCountReporter
    INSTITUTIONAL_USERS = InstitutionalUsersReporter
    INSTITUTIONAL_SUMMARY = InstitutionalSummaryMonthlyReporter
    ITEM_USAGE = PublicItemUsageReporter
    PRIVATE_SPAM_METRICS = PrivateSpamMetricsReporter
    NOTIFICATIONS_COUNT = NotificationCountReporter
