# -*- coding: utf-8 -*-
import solr
#TODO
# This abstracts all index updates to an engine agnostic class
def update_project(args=None):
    solr.update_solr(args)

def update_user(user):
    solr.update_user(user)

def delete_doc(args=None):
    solr.delete_solr_doc(args)

def migrate_wiki(args=None):
    solr.migrate_solr_wiki(args)
