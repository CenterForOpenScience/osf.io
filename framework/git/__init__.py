import os
import subprocess

import website.settings

def init(path):
	try:
		os.mkdir(path)
	except:
		pass

	subprocess.Popen(
        ["git", "init"],
        cwd=path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False
    ).communicate()

def branch_orphan_pull(old, new, user):
    folder_old = os.path.join(website.settings.UPLOADS_PATH, old)
    folder_new = os.path.join(website.settings.UPLOADS_PATH, new)

    p1 = subprocess.Popen(["git","checkout","--orphan", str(new)],
        cwd=folder_old,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False
    )
    p2 = subprocess.Popen(
        [   "git", "commit", "--author",
            '"{fullname} <{email}>"'.format(
                fullname=user.fullname,
                email='user-' + str(user.id) + '@openscienceframework.org'),
            "-m", '"Forked from {old} to {new}"'.format(old=str(old), new=str(new))
        ],
        cwd=folder_old,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False
    )

    p4 = subprocess.Popen(
        ["git", "pull", folder_old, "{new}:master".format(new=new)],
        cwd=folder_new,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False
    )
    p1.communicate()
    p2.communicate()
    init(folder_new)
    p4.communicate()
