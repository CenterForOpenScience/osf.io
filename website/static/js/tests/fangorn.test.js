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
    describe('FangornMoveUnitTests', () => {
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
                'parentId': 1,
            };
        }

        describe('isInvalidDropFolder', () => {
            it('valid drop', () => {
                assert.equal(Fangorn.isInvalidDropFolder(getItem('folder')), false);
            });      

            it('invalid drop if no parent id', () => {
                folder = getItem('folder');
                folder.parentId = 0;
                assert.equal(Fangorn.isInvalidDropFolder(folder), true);
            });

            it('invalid drop if not folder', () => {
                assert.equal(Fangorn.isInvalidDropFolder(getItem()), true);
            });      

            it('invalid drop if file', () => {
                assert.equal(Fangorn.isInvalidDropFolder(getItem('file')), true);
            });                

            it('invalid drop if no edit permimssion', () => {
                folder = getItem('folder');
                folder.data.permissions.edit = false;
                assert.equal(Fangorn.isInvalidDropFolder(folder), true);
            });

            it('invalid drop if no provider', () => {
                folder = getItem('folder');
                folder.data.provider = null;
                assert.equal(Fangorn.isInvalidDropFolder(folder), true);
            });          

            it('invalid drop if status', () => {
                folder = getItem('folder');
                folder.data.status = true;
                assert.equal(Fangorn.isInvalidDropFolder(folder), true);
            });

            it('invalid drop if provider dataverse', () => {
                folder = getItem('folder');
                folder.data.provider = 'dataverse';
                assert.equal(Fangorn.isInvalidDropFolder(folder), true);
            });
        });

        describe('isInvalidFigshareDropFolder', () => {
            it('valid drop', () => {
                assert.equal(Fangorn.isInvalidFigshareDropFolder(getItem('folder')), false);
            });

            it('valid drop if figshare private', () => {
                folder = getItem('folder');
                folder.data.provider = 'figshare';
                folder.data.extra = {'status': 'private'};
                assert.equal(Fangorn.isInvalidFigshareDropFolder(folder), false);
            });

            it('invalid drop if figshare public', () => {
                folder = getItem('folder');
                folder.data.provider = 'figshare';
                folder.data.extra = {'status': 'public'};
                assert.equal(Fangorn.isInvalidFigshareDropFolder(folder), true);
            });
        });

        describe('isInvalidDropItem', () => {
            it('valid drop', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), false);
            });

            it('invalid drop if nodeType', () => {
                folder = getItem('folder', 2);
                item = getItem('folder', 3);
                item.data.nodeType = 'project';
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), true);
            });

            it('invalid drop if isAddonRoot', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.data.isAddonRoot = true;
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), true);
            });

            it('invalid drop if item.id same as folder.id', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 2);
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), true);
            });

            it('invalid drop if item.parentId same as folder.id', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.parentID = 2;
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), true);
            });

            it('invalid drop if provider dataverse', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.data.provider = 'dataverse';
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), true);
            });

            it('valid drop if can be folder and is folder', () => {
                folder = getItem('folder', 2);
                item = getItem('folder', 3);
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), false);
            });            

            it('invalid drop if cannot be folder and is folder', () => {
                folder = getItem('folder', 2);
                item = getItem('folder', 3);
                assert.equal(Fangorn.isInvalidDropItem(folder, item, true, false), true);
            });

            it('valid drop if mustBeIntra and same provider', () => {
                folder = getItem('folder', 2);
                folder.data.provider = 'github';
                item = getItem('file', 3);
                item.data.provider = 'github';
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, true), false);
            });            

            it('invalid drop if mustBeIntra and not same provider', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                item.data.provider = 'github';
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, true), true);
            });

            it('valid drop if figshare and private', () => {
                folder = getItem('folder', 2);
                item = getItem('folder', 3);
                item.data.provider = 'figshare';
                item.data.extra = {};
                item.data.extra.status = 'private';
                assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), false);
            });

            // it('invalid drop if figshare and public', () => {
            //     folder = getItem('folder', 2);
            //     item = getItem('folder', 3);
            //     item.data.provider = 'figshare';
            //     item.data.extra = {};
            //     item.data.extra.status = 'public';
            //     assert.equal(Fangorn.isInvalidDropItem(folder, item, false, false), true)
            // });            

        });

        describe('allowedToMove', () => {
            it('can move', () => {
                folder = getItem('folder', 2);
                item = getItem('file', 3);
                assert.equal(Fangorn.allowedToMove(folder, item, false), true);
            });
        });
    });
});
