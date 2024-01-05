'use strict';

var $ = require('jquery');
var _ = require('js/rdmGettext')._;
var $osf = require('js/osfHelpers');
var Fangorn = require('js/fangorn').Fangorn;
var node = window.contextVars.node;

// Don't show dropped content if user drags outside grid
window.ondragover = function(e) { e.preventDefault(); };
window.ondrop = function(e) { e.preventDefault(); };

var nodeApiUrl = window.contextVars.node.urls.api;

var growled = false;

var expandFolder = function(tb, tree) {
    var child;
    var provider = '';

    // no storage and path argument are given.
    var directory = window.contextVars.directory;
    if (directory === undefined || directory.path === false) {
        return;
    }

    // the path argument does not exist.
    if (tb.fangornFolderArray[0] === '') {
        return;
    }

    for (var i = 0; i < tree.children.length; i++) {
        child = tree.children[i];
        provider = child.data.provider;
        if (node.id === child.data.nodeId &&
            directory.provider === child.data.provider &&
            tb.fangornFolderArray[tb.fangornFolderIndex] === child.data.name) {
            tb.fangornFolderIndex++;
            if (child.data.kind === 'folder') {
                if (tb.fangornFolderArray.length === tb.fangornFolderIndex) {
                    child.css = 'fangorn-selected';
                    tb.multiselected([child]);
                }
                tb.updateFolder(null, child);
            }
            return;
        }
    }

    /*
     * Growl if target path does not exist.
     */
    if (directory.provider === provider &&
        tb.fangornFolderIndex < tb.fangornFolderArray.length &&
        growled === false) {
        growled = true;
        $osf.growl('Error', _('Could not open the path'));
    }
};

$(document).ready(function(){
    $.ajax({
      url: nodeApiUrl + 'files/grid/'
    }).done(function(data) {
        new Fangorn({
            placement: 'project-files',
            divID: 'treeGrid',
            filesData: data.data,
            allowMove: !node.isRegistration,
            xhrconfig: $osf.setXHRAuthorization,
            ondataload: function () {
                var tb = this;
                Fangorn.DefaultOptions.ondataload.call(tb);
                tb.fangornFolderIndex = 0;
                tb.fangornFolderArray = [''];

                // no storage and materializedPath argument are given.
                var directory = window.contextVars.directory;
                if (directory === undefined || directory.materializedPath === false) {
                    return;
                }

                tb.fangornFolderArray = decodeURI(directory.materializedPath).split('/');
                if (tb.fangornFolderArray.length > 1) {
                    tb.fangornFolderArray.splice(0, 1);
                }

                /*
                 * Growl if target provider does not exist.
                 */
                var project;
                var storage;
                for (var i = 0; i < tb.treeData.children.length; i++) {
                    project = tb.treeData.children[i];
                    for (var j = 0; j < project.data.children.length; j++) {
                        storage = project.data.children[j];
                        if (directory.provider === storage.provider) {
                            return;
                        }
                    }
                }

                growled = true;
                $osf.growl('Error', _('Could not open the path'));
            },
            lazyLoadOnLoad: function(tree, event) {
                var tb = this;
                Fangorn.DefaultOptions.lazyLoadOnLoad.call(tb, tree, event);
                expandFolder(tb, tree);
                if (tree.depth > 1) {
                    Fangorn.Utils.orderFolder.call(this, tree);
                }
            }
        });
    });
});
