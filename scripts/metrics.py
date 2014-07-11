#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Old metrics script."""
from math import log

from urlparse import urlsplit

from pymongo import Connection
import website.settings.defaults as settings
import itertools

from framework.auth import User

from framework.analytics import get_basic_counters
from website.models import *
from website import models
from website.addons.osffiles.model import NodeFile

from website.app import init_app
app = init_app()

import framework

def median(a):
    ordered = sorted(a)
    length = len(a)
    return float((ordered[length/2] + ordered[-(length+1)/2]))/2

#connect = Connection(settings.MONGO_URI)
#
#db_name = urlsplit(settings.MONGO_URI).path[1:] # Slices off the leading slash of the path (database name)
#
#db = connect[db_name]
#
#dict_people = {} # _id = name, links, group
#dict_project = {} # _id = name, links, group

#number_users = len(list(db['user'].find({})))
number_users = models.User.find().count()

from framework import Q

projects = models.Node.find(
    Q('category', 'eq', 'project') &
    Q('is_deleted', 'eq', False)
)
projects_forked = list(models.Node.find(
    Q('category', 'eq', 'project') &
    Q('is_deleted', 'eq', False) &
    Q('is_fork', 'eq', True)
))
projects_registered = models.Node.find(
    Q('category', 'eq', 'project') &
    Q('is_deleted', 'eq', False) &
    Q('is_registration', 'eq', True)
)

#projects = list(db['node'].find({'category':'project', 'is_deleted':False}))
#projects_forked = list(db['node'].find({'category':'project', 'is_deleted':False, 'is_fork':True}))
#projects_registered = list(db['node'].find({'category':'project', 'is_deleted':False, 'is_registration':True}))

pf = []
for p in projects_forked:
    #project = Node.load(p['_id'])
    if not p.contributors[0]:
        continue
    name = p.contributors[0].fullname
    #name = User.load(project.contributor_list[0]['id']).fullname
    #if not unicode(name)==u'Jeffrey R. Spies' and not (name)=='Brian A. Nosek':
    if unicode(name) not in [u'Jeffres R. Spies', 'Brian A. Nosek']:
        pf.append(p)

pr = []
for p in projects_registered:
    #project = Node.load(p['_id'])
    name = p.contributors[0].fullname
    if not p.contributors[0]:
        continue
    #name = User.load(project.contributor_list[0]['id']).fullname
    if not unicode(name)==u'Jeffrey R. Spies' and not unicode(name)==u'Brian A. Nosek':
        pr.append(p)

number_projects = len(projects)
#number_projects_public = len(list(db['node'].find({'category':'project', 'is_deleted':False, 'is_public':True})))
number_projects_public = models.Node.find(
    Q('category', 'eq', 'project') &
    Q('is_deleted', 'eq', False) &
    Q('is_public', 'eq', True)
).count()
number_projects_forked = len(pf)

number_projects_registered = len(pr)

##############

number_downloads_total = 0
number_downloads_unique = 0

number_views_total = 0
number_views_unique = 0

contributors_per_project = []
contributors_per_user = []

contrib = {}

for project in projects:
	#project = Node.load(p['_id'])
	contributors_per_project.append(len(project.contributors))
	for person in project.contributors:
                if not person:
                    continue
		if person._id not in contrib:
			contrib[person._id] = []
		for neighbor in project.contributors:
                        if not neighbor:
                            continue
			if neighbor._id not in contrib[person._id]:
				contrib[person._id].append(neighbor._id)
	unique, total = get_basic_counters('node:' + str(project._id))
	if total:
		number_views_total += total
		number_views_unique += unique
	for k,v in project.files_versions.iteritems():
		for i, f in enumerate(v):
			fi = NodeFile.load(f)
			unique, total = get_basic_counters('download:' + str(project._id) + ':' + fi.path.replace('.', '_'))
			if total:
				number_downloads_total += total
				number_downloads_unique += unique

print "number_users"              , number_users
print "number_projects"           , number_projects
print "number_projects_public"    , number_projects_public
print "number_projects_forked"    , number_projects_forked
print "number_projects_registered", number_projects_registered
print "number_downloads_total"    , number_downloads_total
print "number_downloads_unique"   , number_downloads_unique
print "number_views_total"        , number_views_total
print "number_views_unique"       , number_views_unique
