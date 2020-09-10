# -*- coding: utf-8 -*-
# groups maintainance utility - bulk remove groups
#
# Synopsis:
#   rmgroups [options]
#
# Options:
#   -u  filter groups by creator's mail address.  When ommited, all groups in GRDM are listed
#   -g  remove target groups in GRDM
#   -k  remove juat the link between GRDM and mAP.  it is useful for re-link to another mAP server
#   -m  remove target groups in mAP
#   -f  <file>  read group file that contains list of group_key
#   -i  interactive operation.  it will ask delete or not for every group
#   -v  verbose messages
#   -d  dry-run mode.  just print actions
from __future__ import print_function
import sys
from pprint import pformat as pp

# initialize for standalone exec
if __name__ == '__main__':
    from website.app import init_app
    init_app(routes=False, set_backends=False)

from osf.models.user import OSFUser
from osf.models.node import Node
from django.core.exceptions import ObjectDoesNotExist
from nii.mapcore import remove_node
from nii.mapcore_api import (MAPCore, MAPCoreException)
import argparse


def error_out(msg):
    print(msg, file=sys.stderr)


class Options:

    def arg_parser(self):
        parser = argparse.ArgumentParser(description='GRDM/mAP group maintanance utility')
        parser.add_argument('-g', '--grdm', action='store_true', help='remove groups from GRDM')
        parser.add_argument('-m', '--map', action='store_true', help='remove groups from mAP')
        parser.add_argument('-k', '--key_only', action='store_true', help='remove link (group_key) only')
        parser.add_argument('-f', '--key_file', help='file name contains group_key list')
        parser.add_argument('-u', '--user', help='filter with creator\'s mail address')
        parser.add_argument('-i', '--interactive', action='store_true', help='select delete groups interactively')
        parser.add_argument('-v', '--verbose', action='store_true', help='show more group information')
        parser.add_argument('-d', '--dryrun', action='store_true', help='dry run')
        args = parser.parse_args()

        # --user
        self.user = None
        if args.user is not None:
            try:
                self.user = OSFUser.objects.get(username=args.user)
            except Exception as e:
                error_out(e.message)
                raise
        # --key_file
        self.keys = None
        if args.key_file is not None:
            self.keys = []
            try:
                f = open(args.key_file, 'rt')
            except Exception as e:
                error_out(e.message)
                raise
            for k in f:
                if k == '' or k == '\n' or k[:1] == '#':
                    continue
                self.keys.append(k.rstrip('\n'))

        # flags
        self.delete_grdm = args.grdm
        self.delete_map = args.map
        self.key_only = args.key_only
        self.interactive = args.intearactive
        self.verbose = args.verbose
        self.dryrun = args.dryrun

    # for invoke
    def __init__(self, user=None, key_file=None, grdm=False, map=False, key_only=False,
                 interactive=False, verbose=False, dry_run=False):
        # -u option
        self.user = None
        if user is not None:
            try:
                self.user = OSFUser.objects.get(username=user)
            except Exception as e:
                error_out(e.message)
                raise

        # --key_file
        self.keys = None
        if key_file is not None:
            self.keys = []
            try:
                f = open(key_file, 'rt')
            except Exception as e:
                error_out(e.message)
                raise
            for k in f:
                if k == '' or k == '\n' or k[:1] == '#':
                    continue
                self.keys.append(k.rstrip('\n'))

        # flags
        self.delete_grdm = grdm
        self.delete_map = map
        self.key_only = key_only
        self.interactive = interactive
        self.verbose = verbose
        self.dryrun = dry_run

    def dump(self):
        print(pp(vars(self)))


def get_user_response(flag, options):
    # show prompt and response
    delete_rdm = True
    delete_map = True
    delete_key = False
    if not options.delete_grdm:
        delete_rdm = False
    if not options.delete_map or flag == 'R':
        delete_map = False
    prompt = []
    chars = 'sS'
    if delete_rdm and delete_map:
        prompt.append('B)oth')
        prompt.append('K)ey')
        chars += 'bBkK'
    if delete_rdm:
        prompt.append('R)dm')
        chars += 'rR'
    if delete_map:
        prompt.append('M)ap')
        chars += 'mM'
    prompt.append('S)kip')
    prompt_str = ', '.join(prompt) + ' >> '
    chars += 'sS'

    # input
    while True:
        try:
            res = input(prompt_str)
        except EOFError:
            pass  # simply ignore
            continue
        cmd = res[:1]
        if cmd == '' or chars.find(cmd) < 0:
            continue

        # set action flags
        if cmd in ['b', 'B']:
            delete_rdm = True
            delete_map = True
        elif cmd in ['k', 'K']:
            delete_rdm = False
            delete_map = False
            delete_key = True
        elif cmd in ['r', 'R']:
            delete_rdm = True
            delete_map = False
        elif cmd in ['m', 'M']:
            delete_rdm = False
            delete_map = True
        elif cmd in ['s', 'S']:
            delete_rdm = False
            delete_map = False
        else:
            pass  # not reached
        break

    return delete_rdm, delete_map, delete_key


def remove_one_group(node, options):
    # get linked mAP group
    creator = node.creator
    mapcore = MAPCore(creator)
    group_key = node.map_group_key
    flag = 'B'  # default: BOTH exist
    if group_key is not None:
        try:
            mapcore.get_group_by_key(group_key)
        except MAPCoreException as e:
            if e.group_does_not_exist():
                flag = 'R'  # GRDM only
    else:
        flag = 'R'  # GRDM only

    # display group info
    if options.interactive:
        msg1 = u'{}, title="{}", grp_key="{}"'.format(flag, node.title, node.map_group_key)
        msg2 = u', desc="{}", creator="{}", created={}'.format(
            node.description, creator.username, node.created.strftime('%Y/%m/%d'))
    else:
        msg1 = u'{}, "{}", "{}"'.format(flag, node.title, node.map_group_key)
        msg2 = u', "{}", "{}", {}'.format(node.description, creator.username, node.created.strftime('%Y/%m/%d'))
    if options.verbose:
        print(msg1 + msg2)
    else:
        print(msg1)

    # promting
    if options.interactive:
        delete_rdm, delete_map, delete_key = get_user_response(flag, options)
    else:
        delete_rdm = False
        delete_map = False
        delete_key = False
        if options.delete_map and flag == 'B':
            delete_map = True
        if options.key_only and not options.delete_grdm:
            delete_key = True
        if options.delete_grdm:
            delete_rdm = True

    # do action
    map_deleted = False
    if delete_map and mapcore is not None and group_key is not None:
        if options.dryrun:
            print('-->(dryrun) mAP group is deleted!')
            print('-->(dryrun) group key in GRDM is deleted!')
            map_deleted = True
        else:
            try:
                mapcore.delete_group(group_key)
                if options.verbose:
                    print('--> mAP group is deleted!')
                node.map_group_key = None
                node.save()
                map_deleted = True
                if options.verbose:
                    print('--> group key in GRDM is deleted!')
            except MAPCoreException as e:
                print('--> mAP group is not deleted by error: ' + e.message)
    if group_key is not None and \
       not map_deleted and (delete_key or delete_rdm):
        if options.dryrun:
            print('-->(dryrun) group key in GRDM is deleted!')
        else:
            node.map_group_key = None
            node.save()
            if options.verbose:
                print('--> group key in GRDM is deleted!')
    if delete_rdm:
        if options.dryrun:
            print('-->(dryrun) GRDM group is deleted!')
        else:
            remove_node(node)
            if options.verbose:
                print('--> GRDM group is deleted!')
    return


def remove_multi_groups(options):
    # make list of candidate
    if options.user is not None:
        glist = Node.objects.filter(is_deleted=False).filter(creator=options.user)
    elif options.keys is not None:
        # list of group keys
        glist = []
        for key in options.keys:
            try:
                grp = Node.objects.get(map_group_key=key)
            except ObjectDoesNotExist:
                error_out(u'RDM group having group_key[{}] is not found!.  Ignore.'.format(key))
                continue
            glist.append(grp)
    else:
        # no filter
        glist = Node.objects.filter(is_deleted=False)

    if len(glist) == 0:
        error_out('No group found.')

    # group loop
    for grp in glist:
        remove_one_group(grp, options)


if __name__ == '__main__':
    # command line options
    options = Options()
    options.arg_parser()
    remove_multi_groups(options)
