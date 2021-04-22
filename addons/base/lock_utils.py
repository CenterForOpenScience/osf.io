from addons.dropboxbusiness import lock as dpbiz_lock
from addons.nextcloudinstitutions import lock as nci_lock

def init_lock():
    dpbiz_lock.init_lock()
    nci_lock.init_lock()
