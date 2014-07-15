# GitLab Migration

The GitLab add-on has been implemented as a drop-in replacement for the
original OSF storage, meaning that all OSF files and their associated meta-
data must be migrated to GitLab.

1. Configure settings
    * In website/settings/local.py add 'gitlab' to `ADDONS_REQUESTED`.
    * In website/addons/gitlab/settings/defaults.py set ROUTE to 'gitlab'.
2. Copy all git data from the app server to a backup directory on the GitLab server
    * sudo rsync -aP /opt/data/uploads root@50.116.57.122:/opt/data/backup
    * sudo rsync -aP --checksum /opt/data/uploads root@50.116.57.122:/opt/data/backup
3. Create GitLab users and projects corresponding to OSF users and components
    * [On app server]
        * cd /opt/apps/osf
        * python -m scripts.gitlab.migrate_mongo
4. Clone OSF repo to GitLab machine
    * [On Gitlab server]
        * git clone https://github.com/jmcarp/osf
        * git checkout feature/gitlab
5. Copy backed-up repos to bare repos in GitLab directory
    * OSF must be down
    * Repeat #2, #3
	* [On GitLab server]
	    * Verify SOURCE_PATH and DEST_PATH in scripts/gitlab/migrate_files.py
		* cd /root/osf
		* sudo -u git -H python scripts/gitlab/migrate_files.py
		    * Must run as user git for permissions happiness
6. Migrate file GUIDs from OSF files to GitLab
	* On app server
		* cd /opt/apps/osf
		* python -m scripts.gitlab.migrate_guids
7. Build routing table to preserve old URLs
	* On app server
		* cd /opt/apps/osf
		* sudo env/bin/python -m scripts.gitlab.routing_table
8. Migrate download counts from OSF files to GitLab
	* On app server
		* cd /opt/apps/osf
		* python -m scripts.gitlab.migrate_counts
9. Finalize settings
    * In website/settings/local.py remove 'osffiles' from `ADDONS_REQUESTED`.
    * In website/addons/gitlab/settings/defaults.py switch `ROUTE` from 'gitlab' to 'osffiles'.
