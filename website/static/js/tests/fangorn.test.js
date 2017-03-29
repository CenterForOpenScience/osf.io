/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';

var testUtils = require('./utils');
var $osf = require('js/osfHelpers');
var Fangorn = require('js/fangorn');

var assert = require('chai').assert;
var utils = require('tests/utils');
var faker = require('faker');
var $ = require('jquery');
var Raven = require('raven-js');
var language = require('js/osfLanguage').projectSettings;

describe('fangorn', () => {
    describe('FangornMoveAndDeleteUnitTests', () => {
        // folder setup
        var folder;
        var item;
        var getItem = function(kind, id){
            if(typeof id === 'undefined'){
                id = 2;
            }
            return {
                'data': {
                    'provider': 'osfstorage',
                    'kind': kind,
                    'permissions': {
                        'edit': true
                    }
                },
                'children': [],
                'id': id,
                'parentID': 1,
            };
        };
        describe('getCopyMode integration', () => {
            it('can be dropped and returns move if valid', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                assert.equal(Fangorn.getCopyMode(folder, [item]), 'move');
            });

            it('can be dropped and returns copy if github provider', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.data.provider = 'github';
                assert.equal(Fangorn.getCopyMode(folder, [item]), 'copy');
            });

            it('cannot be dropped if folder.data is undefined', () => {
                folder = getItem('file', 2);
                delete folder.data;
                item = getItem('file', 3);
                assert.equal(Fangorn.getCopyMode(folder, [item]), 'forbidden');
            });                        

            it('cannot be dropped if isInvalidDropFolder returns true', () => {
                folder = getItem('file', 2);
                item = getItem('file', 3);
                assert.equal(Fangorn.getCopyMode(folder, [item]), 'forbidden');
            });

            it('cannot be dropped if isInvalidDropItem returns true', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.data.nodeType = 'project';
                assert.equal(Fangorn.getCopyMode(folder, [item]), 'forbidden');
            });

            it('cannot be dropped if dragging parent into child', () => {
                folder = getItem('folder', 2);
                item = getItem('folder', 3);
                item.children = [folder];
                assert.equal(Fangorn.getCopyMode(folder, [item]), 'forbidden');
            });

            it('cannot be dropped if item inProgress is true', () => {
                folder = getItem('folder', 2);
                item = getItem('folder', 3);
                item.inProgress = true;
                folder.children = [item];
                assert.equal(Fangorn.getCopyMode(folder, [item]), 'forbidden');
            });

            it('folder can be dropped if target is figshare addon root with type project', () => {
                folder = getItem('folder', 0);
                folder.data.provider = 'figshare';
                folder.data.isAddonRoot = true;
                folder.data.rootFolderType = 'project';
                item = getItem('folder', 3);
                assert.equal(Fangorn.getCopyMode(folder, [item]), 'move');
            });

            it('folder cannot be dropped if target is figshare addon root with type fileset', () => {
                folder = getItem('folder', 2);
                folder.data.provider = 'figshare';
                folder.data.isAddonRoot = false;
                item = getItem('folder', 3);
                assert.equal(Fangorn.getCopyMode(folder, [item]), 'forbidden');
            });

            it('folder cannot be dropped if target is figshare non-root fileset', () => {
                folder = getItem('folder', 0);
                folder.data.provider = 'figshare';
                folder.data.isAddonRoot = true;
                folder.data.rootFolderType = 'fileset';
                item = getItem('folder', 3);
                assert.equal(Fangorn.getCopyMode(folder, [item]), 'forbidden');
            });
        });

        describe('isInvalidDropFolder', () => {
            it('can be dropped if valid', () => {
                assert.equal(Fangorn.isInvalidDropFolder(getItem('folder')), false);
            });      

            it('cannot be dropped if target parentID is root', () => {
                folder = getItem('folder');
                folder.parentID = 0;
                assert.equal(Fangorn.isInvalidDropFolder(folder), true);
            });

            it('cannot be dropped into if target inProgress is true', () => {
                folder = getItem('folder');
                folder.inProgress = true;
                assert.equal(Fangorn.isInvalidDropFolder(folder), true);
            });            

            it('cannot be dropped if target kind is undefined', () => {
                assert.equal(Fangorn.isInvalidDropFolder(getItem()), true);
            });      

            it('cannot be dropped if target kind is file', () => {
                assert.equal(Fangorn.isInvalidDropFolder(getItem('file')), true);
            });                

            it('cannot be dropped if no edit permission for target', () => {
                folder = getItem('folder');
                folder.data.permissions.edit = false;
                assert.equal(Fangorn.isInvalidDropFolder(folder), true);
            });

            it('cannot be dropped if target has no provider', () => {
                folder = getItem('folder');
                folder.data.provider = null;
                assert.equal(Fangorn.isInvalidDropFolder(folder), true);
            });          

            it('cannot be dropped if target has an associated status', () => {
                folder = getItem('folder');
                folder.data.status = true;
                assert.equal(Fangorn.isInvalidDropFolder(folder), true);
            });

            it('cannot be dropped if target provider is dataverse', () => {
                folder = getItem('folder');
                folder.data.provider = 'dataverse';
                assert.equal(Fangorn.isInvalidDropFolder(folder), true);
            });
        });

        describe('isInvalidDropItem', () => {
            it('can be dropped if valid', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), false);
            });

            it('cannot be dropped if item has a nodeType', () => {
                folder = getItem('folder', 2);
                item = getItem('folder', 3);
                item.data.nodeType = 'project';
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), true);
            });

            it('cannot be dropped if item is an addonRoot', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.data.isAddonRoot = true;
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), true);
            });

            it('cannot be dropped if item and target are the same', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 2);
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), true);
            });

            it('cannot be dropped if the target is the current parent', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.parentID = 2;
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), true);
            });

            it('cannot be dropped if item provider is dataverse', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.data.provider = 'dataverse';
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), true);
            });

            it('cannot be dropped if item inProgress is true', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.inProgress = true;
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), true);
            });            

            it('can be dropped if folder and allowed to be folder', () => {
                folder = getItem('folder', 2);
                item = getItem('folder', 3);
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), false);
            });            

            it('cannot be dropped if folder and not allowed to be folder', () => {
                folder = getItem('folder', 2);
                item = getItem('folder', 3);
                assert.equal(Fangorn.isInvalidDropItem(folder, item, true, false), true);
            });

            it('can be dropped if mustBeIntra is true and same provider', () => {
                folder = getItem('folder', 2);
                folder.data.provider = 'github';
                item = getItem('file', 3);
                item.data.provider = 'github';
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, true), false);
            });            

            it('cannot be dropped if mustBeIntra is true and not same provider', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.data.provider = 'github';
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, true), true);
            });
        });

        describe('allowedToMove', () => {
            it('can move if valid', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                assert.equal(Fangorn.allowedToMove(folder, item, false), true);
            });

            it('cannot move if edit permisisons false', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.data.permissions.edit = false;
                assert.equal(Fangorn.allowedToMove(folder, item, false), false);
            });

            it('cannot move if mustBeIntra is true and not same provider', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.data.provider = 'google';
                assert.equal(Fangorn.allowedToMove(folder, item, true), false);
            });

            it('cannot move if mustBeIntra is true and not same node', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                folder.data.nodeId = 'abcde';
                item.data.nodeId = 'ebcde';
                assert.equal(Fangorn.allowedToMove(folder, item, true), false);
            });

            it('can move if mustBeIntra is true and same provider and same node', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                folder.data.nodeId = 'abcde';
                item.data.nodeId = 'abcde';
                assert.equal(Fangorn.allowedToMove(folder, item, true), true);
            });

            it('cannot move item from figshare if it is public', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.data.provider = 'figshare';
                item.data.extra = {'status': 'public'};
                assert.equal(Fangorn.allowedToMove(folder, item, false), false);
            });

            it('can move item from figshare if it is private', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.data.provider = 'figshare';
                item.data.extra = {'status': 'draft'};
                assert.equal(Fangorn.allowedToMove(folder, item, false), true);
            });
        });

        describe('getAllChildren', () => {
            it('returns no children when there are no children', () => {
                folder = getItem('folder', 2);
                assert.equal(Fangorn.getAllChildren(item).length, 0);
            });

            it('returns one child when there is only one child', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.children = [folder];
                assert.equal(Fangorn.getAllChildren(item).length, 1);
            });

            it('returns two children when child has a child', () => {
                folder = getItem('folder', 2);
                var folder2 = getItem('folder', 3);
                item = getItem('file', 4);
                folder2.children = [item];
                folder.children = [folder2];
                assert.equal(Fangorn.getAllChildren(folder).length, 2);
            });              
        });

        describe('folderContainsPreprint', () => {
            it('does not contain a preprint if no children', () => {
                folder = getItem('folder', 2);
                assert.equal(Fangorn.folderContainsPreprint(folder, 'abcdefg'), false);
            });

            it('does not contain a preprint if child is not a preprint', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.data.path = 'gfedcba';
                folder.children = [item];
                assert.equal(Fangorn.folderContainsPreprint(folder, 'abcdefg'), false);
            });

            it('does contain a preprint if child is a preprint', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.data.path = 'abcdefg';
                folder.children = [item];
                assert.equal(Fangorn.folderContainsPreprint(folder, 'abcdefg'), true);
            });

            it('does contain a preprint if nested child is a preprint', () => {
                folder = getItem('folder', 2);
                var folder2 = getItem('folder', 3);
                item = getItem('file', 4);
                item.data.path = 'abcdefg';
                folder2.children = [item];
                folder.children = [folder2];
                assert.equal(Fangorn.folderContainsPreprint(folder, 'abcdefg'), true);
            });           
        });

        describe('multiselectContainsPreprint', () => {
            it('does contain a preprint if one item is a preprint', () => {
                folder = getItem('folder', 2);
                folder.data.path = 'aaaaaaa';
                item = getItem('file', 3);
                item.data.path = 'abcdefg';
                assert.equal(Fangorn.multiselectContainsPreprint([folder, item], 'abcdefg'), true);
            });

            it('does not contain a preprint if no items are preprints', () => {
                folder = getItem('folder', 2);
                folder.data.path = 'aaaaaaa';
                item = getItem('file', 3);
                item.data.path = 'bbbbbbb';
                assert.equal(Fangorn.multiselectContainsPreprint([folder, item], 'abcdefg'), false);
            });                       
        });

        describe('showDeleteMultiple', () => {
            it('does not show multi delete if no edit permissions', () => {
                folder = getItem('folder', 2);
                folder.data.permissions.edit = false;
                item = getItem('file', 3);
                item.data.permissions.edit = false;
                assert.equal(Fangorn.showDeleteMultiple([folder, item]), false);
            });

            it('does show multi delete if edit permissions for at least one selected', () => {
                folder = getItem('folder', 2);
                folder.data.permissions.edit = false;
                item = getItem('file', 3);
                item.data.permissions.edit = true;
                assert.equal(Fangorn.showDeleteMultiple([folder, item]), true);
            });

            it('does show multi delete if edit permissions for all selected', () => {
                folder = getItem('folder', 2);
                folder.data.permissions.edit = true;
                item = getItem('file', 3);
                item.data.permissions.edit = true;
                assert.equal(Fangorn.showDeleteMultiple([folder, item]), true);
            });            
        });        
    });
});
