# GitLab Migration

The GitLab add-on has been implemented as a drop-in replacement for the
original OSF storage, meaning that all OSF files and their associated meta-
data must be migrated to GitLab.

1. In `website/settings/local.py` add `'gitlab'` to `ADDONS_REQUESTED`.
2. Copy all git data from the app server to a backup directory on the GitLab server
    * sudo rsync -vaz /opt/data/uploads root@50.116.57.122:/opt/data/backup
3. Create GitLab users and projects corresponding to OSF users and components
    * [On app server]
        * cd /opt/apps/osf
        * python -m scripts.gitlab.migrate_mongo
4. Clone backed-up repos to bare repos in GitLab directory
	* [On GitLab server]
		* cd /root/osf
		* python -m scripts.gitlab.migrate_files
5. Migrate file GUIDs from OSF files to GitLab
	* On app server
		* cd /opt/apps/osf
		* python -m scripts.gitlab.migrate_guids
6. Build routing table to preserve old URLs
	* On app server
		* cd /opt/apps/osf
		* python -m scripts.gitlab.routing_table
7. Migrate download counts from OSF files to GitLab
	* On app server
		* cd /opt/apps/osf
		* python -m scripts.gitlab.migrate_counts
8. In `website/settings/local.py` remove `'osffiles'` from `ADDONS_REQUESTED`.
9. In `website/addons/gitlab/settings/defaults.py` switch `ROUTE` from `'gitlab'` to `'osffiles'`.
