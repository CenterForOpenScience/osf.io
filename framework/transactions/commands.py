# -*- coding: utf-8 -*-

from framework.mongo import database


def begin(database=database):
    database.command('beginTransaction')


def rollback(database=database):
    database.command('rollbackTransaction')


def commit(database=database):
    database.command('commitTransaction')


def show_live(database=database):
    return database.command('showLiveTransactions')
