/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var assert = require('chai').assert;
var Raven = require('raven-js');
var $ = require('jquery');
var ProjectOrganizer = require('js/project-organizer');

// TODO: These tests are about moving projects around but new PO separates the collections and these are not relevant. Check and remove files.
// Add sinon asserts to chai.assert, so we can do assert.calledWith instead of sinon.assert.calledWith
//sinon.assert.expose(assert, {prefix: ''});


//describe('ProjectOrganizer', () => {
//    var returnTrue = function() {
//        return true;
//    };
//
//    var returnFalse = function() {
//        return false;
//    };
//
//    var parentIsFolder = function(){
//        return {
//            data: {
//                node_id: 'normalFolder'
//            }
//        };
//    };
//
//    var parentIsNotFolder = function(){
//        return {
//            data: {
//                node_id: 'noParent'
//            }
//        };
//    };
//    var parent = {
//        name: 'Parent',
//        isAncestor: returnTrue
//    };
//
//    var child = {
//        name: 'Child',
//        isAncestor: returnFalse
//    };
//
//
//    describe('whichIsContainer', () => {
//        it('says children are contained in parents', () => {
//            var ancestor = ProjectOrganizer._whichIsContainer(parent, child);
//            assert.equal(ancestor.name, 'Parent');
//        });
//
//        it('says parents contain children', () => {
//            var ancestor = ProjectOrganizer._whichIsContainer(child, parent);
//            assert.equal(ancestor.name, 'Parent');
//        });
//        it('says nothing if both contain each other', () => {
//            var ancestor = ProjectOrganizer._whichIsContainer(parent, parent);
//            assert.equal(ancestor, null);
//        });
//        it('says nothing if neither contains the other', () => {
//            var ancestor = ProjectOrganizer._whichIsContainer(child, child);
//            assert.equal(ancestor, null);
//        });
//    });
//
//    describe('canAcceptDrop', () => {
//
//        // Most permissive, not a component, not a folder, not a smart folder
//        var defaultItem = {
//            isAncestor: returnFalse,
//            id: 'defaultItem',
//            parent: parentIsNotFolder,
//            data: {
//                    isFolder: false,
//                    isSmartFolder: false,
//                    isComponent: false,
//                    node_id: 'defaultItem',
//                    permissions: {
//                        copyable: true,
//                        movable: true
//                    }
//                }
//            };
//
//        // Most permissive, folder, not a smart folder
//        var defaultFolder = {
//            isAncestor: returnFalse,
//            id: 'defaultFolder',
//            parent: parentIsNotFolder,
//            data: {
//                    isFolder: true,
//                    isSmartFolder: false,
//                    node_id: 'defaultFolder',
//                    permissions: {
//                        acceptsComponents: true,
//                        acceptsFolders: true,
//                        acceptsMoves: true,
//                        acceptsCopies: true,
//                        copyable: true,
//                        movable: true
//                    }
//                }
//            };
//
//        var canCopyOrMoveItem = $.extend({}, defaultItem);
//        var cannotCopyOrMoveItem = $.extend(true, {}, defaultItem, {
//            data: {
//                permissions: {
//                    copyable: false,
//                    movable: false
//                }
//            }
//        });
//
//
//        it('rejects non-folders', () => {
//            var result = ProjectOrganizer._canAcceptDrop([canCopyOrMoveItem], cannotCopyOrMoveItem);
//            assert.equal(result, false);
//        });
//
//        it('rejects smart folders', () => {
//            var smartFolder = $.extend(true, {}, defaultFolder, {data: {isSmartFolder: true}});
//            var result = ProjectOrganizer._canAcceptDrop([canCopyOrMoveItem], smartFolder);
//            assert.isFalse(result);
//        });
//
//        it('rejects if target is contained by dropped items', () => {
//
//            var parentItem = $.extend({}, defaultItem, {
//                isAncestor: returnTrue
//            });
//
//            var result = ProjectOrganizer._canAcceptDrop([parentItem], defaultFolder);
//            assert.isFalse(result);
//        });
//
//        it('rejects dropping on its source folder', () => {
//            var result = ProjectOrganizer._canAcceptDrop([defaultFolder], defaultFolder);
//            assert.isFalse(result);
//        });
//
//        it('rejects components if target does not accept components', () => {
//            var component = $.extend(true, {}, defaultItem, {
//                data: { isComponent: true }
//            });
//
//            var noComponentFolder = $.extend(true, {}, defaultFolder, {
//                data: {permissions: {acceptsComponents: false}}
//            });
//
//            var result = ProjectOrganizer._canAcceptDrop([component], noComponentFolder);
//            assert.isFalse(result);
//        });
//
//        it('accepts components if target accepts components', () => {
//            var copyMode = 'copy';
//
//            var component = $.extend(true, {}, defaultItem, {
//                data: { isComponent: true }
//            });
//
//            var result = ProjectOrganizer._canAcceptDrop([component], defaultFolder, copyMode);
//            assert.isTrue(result);
//        });
//
//        it('rejects folders if target does not accept folders', () => {
//            var copyMode = 'move';
//
//            var folderDoesNotAcceptFolders = $.extend(true, {}, defaultFolder, {
//                data: {permissions: {acceptsFolders: false}}
//            });
//
//            var result = ProjectOrganizer._canAcceptDrop([defaultFolder], folderDoesNotAcceptFolders, copyMode);
//            assert.isFalse(result);
//        });
//
//        it('rejects any folder if target does not accept folders', () => {
//            var copyMode = 'move';
//            var folderDoesNotAcceptFolders = $.extend(true, {}, defaultFolder, {
//                data: {permissions: {acceptsFolders: false}}
//            });
//
//            var result = ProjectOrganizer._canAcceptDrop([defaultItem, defaultFolder, defaultItem], folderDoesNotAcceptFolders, copyMode);
//            assert.isFalse(result);
//        });
//
//
//        it('accepts folders if target accepts folders', () => {
//            var copyMode = 'move';
//            var normalMovableFolder = $.extend(true, {}, defaultFolder, {
//                id: 'normalMovableFolder',
//                data: {node_id: 'normalMovableFolder'}
//            });
//
//            var result = ProjectOrganizer._canAcceptDrop([normalMovableFolder], defaultFolder, copyMode);
//            assert.isTrue(result);
//        });
//
//        it('rejects if copyMode is move and target does not accept move', () => {
//            var copyMode = 'move';
//            var folderDoesNotAcceptMoves = $.extend(true, {}, defaultFolder, {
//                data: { permissions: {acceptsMoves: false}}
//            });
//
//            var result = ProjectOrganizer._canAcceptDrop([defaultItem], folderDoesNotAcceptMoves, copyMode);
//            assert.isFalse(result);
//        });
//
//        it('accepts if copyMode is move and target accepts move', () => {
//            var copyMode = 'move';
//
//            var result = ProjectOrganizer._canAcceptDrop([defaultItem], defaultFolder, copyMode);
//            assert.equal(result, true);
//        });
//
//        it('rejects if copyMode is copy and target does not accept copy', () => {
//            var copyMode = 'copy';
//            var folderDoesNotAcceptCopies = $.extend(true, {}, defaultFolder, {
//                data: { permissions: {acceptsCopies: false}}
//            });
//
//            var result = ProjectOrganizer._canAcceptDrop([defaultItem], folderDoesNotAcceptCopies, copyMode);
//            assert.isFalse(result);
//        });
//
//        it('accepts if copyMode is copy and target accepts copy', () => {
//            var copyMode = 'copy';
//
//            var result = ProjectOrganizer._canAcceptDrop([defaultItem], defaultFolder, copyMode);
//            assert.isTrue(result);
//
//        });
//
//
//    });
//});