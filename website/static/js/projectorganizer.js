'use strict';

var Handlebars = require('handlebars');
var $ = require('jquery');
var HGrid = require('hgrid');
var bootbox = require('bootbox');
var Bloodhound = require('exports?Bloodhound!typeahead.js');
var moment = require('moment');
var Raven = require('raven-js');

require('../vendor/jquery-drag-drop/jquery.event.drag-2.2.js');
require('../vendor/jquery-drag-drop/jquery.event.drop-2.2.js');
require('../vendor/bower_components/hgrid/plugins/hgrid-draggable/hgrid-draggable.js');

var $osf = require('osfHelpers');

//
// Globals
//
// ReloadNextFolder semaphores
var reloadNewFolder = false;
var rnfPrevItem = '';
var rnfToReload = '';
// copyMode can be 'copy', 'move', 'forbidden', or null.
var copyMode = null;
var projectOrganizer = null;

$.ajaxSetup({ cache: false });

//
// Private Helper Functions
//
function setReloadNextFolder(prevItem, toReload){
    reloadNewFolder = true;
    rnfPrevItem = prevItem;
    rnfToReload = toReload;
}

function getItemParentNodeId(theHgrid, item) {
    var itemParentID = item.parentID;
    var itemParent = theHgrid.grid.getData().getItemById(itemParentID);
    return itemParent.node_id;
}

function addAlert(status, message, priority) {
    var $alertDiv = $('<div class = "alert alert-' + priority + '"><a href="#" class="close" data-dismiss="alert">&times;</a>' +
        '<strong>' + status + ':</strong> ' + message +
        '</div>');
    $('body').append($alertDiv);
}

function deleteMultiplePointersFromFolder(theHgrid, pointerIds, folderToDeleteFrom) {
    if(pointerIds.length > 0) {
        var folderNodeId = folderToDeleteFrom.node_id;
        var url = '/api/v1/folder/' + folderNodeId + '/pointers/';
        var postData = JSON.stringify({pointerIds: pointerIds});
        var reloadHgrid = function () {
            if (theHgrid !== null) {
                reloadFolder(theHgrid, folderToDeleteFrom);
            }
        };
        var deleteAction = $.ajax({
            type: 'DELETE',
            url: url,
            data: postData,
            contentType: 'application/json',
            dataType: 'json'
        });
        deleteAction.done(reloadHgrid);
        deleteAction.fail(function (jqxhr, textStatus, errorThrown){
            $osf.growl('Error:', textStatus + '. ' + errorThrown);

        });
    }
}

function setItemToExpand(item, callback) {
    var expandUrl = item.apiURL + 'expand/';
    var postAction = $osf.postJSON(expandUrl,{});
    postAction.done(function() {
        item.expand = false;
        if (typeof callback !== 'undefined') {
            callback();
        }
    }).fail($osf.handleJSONError);
}

function reloadFolder(hgrid, theItem, theParentNode) {
    var toReload = theItem;
    if(typeof theParentNode !== 'undefined' || theItem.kind !== 'folder') {
        toReload = theParentNode;
    }
    hgrid.reloadFolder(toReload);
    hgrid.grid.setSelectedRows([]);
    hgrid.grid.resetActiveCell();
    return toReload;
}
function canAcceptDrop(items, folder){
    // folder is the drop target.
    // items is an array of things to go into the drop target.

    if (folder.isSmartFolder || !folder.isFolder){
        return false;
    }


    // if the folder is contained by the item, return false

    var representativeItem = items[0];
    if (draggable.grid.folderContains(representativeItem.id, folder.id)){
        return false;
    }

    // If trying to drop on the folder it came from originally, return false
    var itemParentNodeId = getItemParentNodeId(draggable.grid, representativeItem);
    if (itemParentNodeId === folder.node_id){
        return false;
    }

    var hasComponents = false;
    var hasFolders = false;
    var copyable = true;
    var movable = true;
    var canDrop = true;

    items.forEach(function(item){
        hasComponents = hasComponents || item.isComponent;
        hasFolders = hasFolders || item.isFolder;
        copyable = copyable && item.permissions.copyable;
        movable = movable && item.permissions.movable;
    });


    if(hasComponents){
        canDrop = canDrop && folder.permissions.acceptsComponents;
    }
    if(hasFolders){
        canDrop = canDrop && folder.permissions.acceptsFolders;
    }
    if(copyMode === 'move'){
        canDrop = canDrop && folder.permissions.acceptsMoves && movable;
    }
    if(copyMode === 'copy'){
        canDrop = canDrop && folder.permissions.acceptsCopies && copyable;
    }
    return canDrop;
}

function dragLogic(event, items, folder){
    var canCopy = true;
    var canMove = true;
    items.forEach(function (item) {
        canCopy = canCopy && item.permissions.copyable;
        canMove = canMove && item.permissions.movable;
    });

    // Check through possible move and copy options, and set the copyMode appropriately.
    if (!(canMove && canCopy && canAcceptDrop(items, folder))) {
        copyMode = 'forbidden';
    }
    else if (canMove && canCopy) {
        if (altKey) {
            copyMode = 'copy';
        } else {
            copyMode = 'move';
        }
    }
    if (!canMove && canCopy) {
        copyMode = 'copy';
    }
    if (!canCopy && canMove) {
        copyMode = 'move';
    }

    // Set the cursor to match the appropriate copy mode
    switch (copyMode) {
        case 'forbidden':
            $('.project-organizer-dand').css('cursor', 'not-allowed');
            break;
        case 'copy':
            $('.project-organizer-dand').css('cursor', 'copy');
            break;
        case 'move':
            $('.project-organizer-dand').css('cursor', 'move');
            break;
        default:
            $('.project-organizer-dand').css('cursor', 'default');
    }

}

function dropLogic(event, items, folder) {
    if (typeof folder !== 'undefined' && folder !== null) {
        var theFolderNodeID = folder.node_id;
        var getChildrenURL = folder.apiURL + 'get_folder_pointers/';
        var folderChildren;
        var sampleItem = items[0];
        var itemParentID = sampleItem.parentID;
        var itemParent = draggable.grid.grid.getData().getItemById(itemParentID);
        var itemParentNodeID = itemParent.node_id;
        if (itemParentNodeID !== theFolderNodeID) { // This shouldn't happen, but if it does, it's bad
            var getAction = $.getJSON(getChildrenURL, function (data) {
                // We can't add a pointer to a folder that already has those pointers, so cull those away
                folderChildren = data;
                var itemsToMove = [];
                var itemsNotToMove = [];
                items.forEach(function (item) {
                    if ($.inArray(item.node_id, folderChildren) === -1) { // pointer not in folder to be moved to
                        itemsToMove.push(item.node_id);
                    } else if (copyMode === 'move') { // Pointer is already in the folder and it's a move
//                              We  need to make sure not to delete the folder if the item is moved to the same folder.
//                              When we add the ability to reorganize within a folder, this will have to change.
                        itemsNotToMove.push(item.node_id);
                    }
                });

                var postInfo = {
                    'copy': {
                        'url': '/api/v1/project/' + theFolderNodeID + '/pointer/',
                        'json': {
                            nodeIds: itemsToMove
                        }
                    },
                    'move': {
                        'url': '/api/v1/pointers/move/',
                        'json': {
                            pointerIds: itemsToMove,
                            toNodeId: theFolderNodeID,
                            fromNodeId: itemParentNodeID
                        }
                    }
                };

                if (copyMode === 'copy' || copyMode === 'move') {
                    // Remove all the duplicated pointers
                    deleteMultiplePointersFromFolder(null, itemsNotToMove, itemParent);
                    setItemToExpand(folder, function () {
                        if (itemsToMove.length > 0) {
                            var url = postInfo[copyMode].url;
                            var postData = JSON.stringify(postInfo[copyMode].json);
                            var outerFolderID = whichIsContainer(draggable.grid, itemParentID, folder.id);

                            var postAction = $.ajax({
                                type: 'POST',
                                url: url,
                                data: postData,
                                contentType: 'application/json',
                                dataType: 'json'
                            });
                            postAction.always(function () {
                                    if (copyMode === 'move') {
                                        if (typeof outerFolderID === 'undefined' || outerFolderID === null) {
                                            itemParent = draggable.grid.grid.getData().getItemById(itemParentID);
                                            setReloadNextFolder(itemParentID, folder.id);
                                            draggable.grid.reloadFolder(itemParent);

                                        } else {
                                            var outerFolder = draggable.grid.grid.getData().getItemById(outerFolderID);
                                            reloadFolder(draggable.grid, outerFolder);
                                        }

                                    } else {
                                        reloadFolder(draggable.grid, folder);

                                    }
                                    copyMode = null;

                            });
                            postAction.fail(function (jqxhr, textStatus, errorThrown){
                                $osf.growl('Error:', textStatus + '. ' + errorThrown);
                            });
                        } else { // From:  if(itemsToMove.length > 0)
//                                folder.childrenCount = folder.children.length;
                                draggable.grid.refreshData();
                                reloadFolder(draggable.grid, itemParent);
                            }
                        });
                    } // From: if (copyMode === 'copy' || copyMode === 'move')
                });
                getAction.fail(function (jqxhr, textStatus, errorThrown){
                    $osf.growl('Error:', textStatus + '. ' + errorThrown);
                });
            } else {
                Raven.captureMessage('Project dashboard: Parent node (' + itemParentNodeID + ') == Folder Node (' + theFolderNodeID + ')');
            }
    } else {
        if (typeof folder === 'undefined') {
            Raven.captureMessage('onDrop folder is undefined.');
        }/* else {
            Raven.captureMessage('onDrop folder is null.');
        }*/
    }
    $('.project-organizer-dand').css('cursor', 'default');
}
  /**
  * Takes two element IDs and tries to determine if one contains the other. Returns the container or null if
  * they are not directly related. Items contain themselves.
  * @method whichIsContainer
  * @param hgrid {Object: Hgrid}
  * @param itemOneID {Number}
  * @param itemTwoID {Number}
  * @returns item ID or null
  */
function whichIsContainer(hgrid, itemOneID, itemTwoID){
    var pathToOne = hgrid.getPathToRoot(itemOneID);
    var pathToTwo = hgrid.getPathToRoot(itemTwoID);
    if(pathToOne.indexOf(itemTwoID) > -1 ){
        return itemTwoID;
    } else if (pathToTwo.indexOf(itemOneID) > -1) {
        return itemOneID;
    } else {
        return null;
    }
}

function createProjectDetailHTMLFromTemplate(theItem) {
    var detailTemplateSource = $('#project-detail-template').html();
    Handlebars.registerHelper('commalist', function (items, options) {
        var out = '';

        for (var i = 0, l = items.length; i < l; i++) {
            out = out + options.fn(items[i]) + (i !== (l - 1) ? ', ' : '');
        }
        return out;
    });
    var detailTemplate = Handlebars.compile(detailTemplateSource);
    var detailTemplateContext = {
        theItem: theItem,
        multipleContributors: theItem.contributors.length > 1,
        parentIsSmartFolder: theItem.parentIsSmartFolder
    };
    var displayHTML = detailTemplate(detailTemplateContext);
    $('.project-details').html(displayHTML);
    addFormKeyBindings(theItem.node_id);

}

var altKey = false;
$(document).keydown(function (e) {
    if (e.altKey) {
        altKey = true;
    }
});
$(document).keyup(function (e) {
    if (!e.altKey) {
        altKey = false;
    }
});

function addFormKeyBindings(nodeID){
    $('#ptd-'+nodeID).keyup(function (e){
        /*if(e.which == 13){ //return
            // Find visible submit-button in this div and activate it
            $('#ptd-'+nodeID).find('.submit-button-'+nodeID).filter(':visible').click();
            return false;
        } else*/ if (e.which === 27) {//esc
            // Find visible cancel-button in this div and activate it
            $('#ptd-'+nodeID).find('.cancel-button-'+nodeID).filter(':visible').click();
            return false;
        }
    });
}

var collapseAllInHGrid = function (grid) {
    grid.collapseAll();
};

var expandAllInHGrid = function (grid) {
    grid.getData().forEach(function (item) {
        grid.expandItem(item);
    });
};

//
// HGrid Customization
//

HGrid.Actions['visitPage'] = {
    on: 'click',
    callback: function(event, item) {
        var url = item.urls.fetch;
        window.location = url;
    }
};
HGrid.Actions['showProjectDetails'] =  {
    on: 'click',
    callback: function(evt, item) {

        projectOrganizer.myProjects.initialize();
        projectOrganizer.publicProjects.initialize();
        // injecting error into search results from https://github.com/twitter/typeahead.js/issues/747

        var mySourceWithEmptySelectable = function(q, cb) {
          var emptyMyProjects = [{ error: 'There are no matching projects to which you contribute.' }];
          projectOrganizer.myProjects.get(q, injectEmptySelectable);

          function injectEmptySelectable(suggestions) {
            if (suggestions.length === 0) {
              cb(emptyMyProjects);
            }

            else {
              cb(suggestions);
            }
          }
        };

        var publicSourceWithEmptySelectable = function(q, cb) {
          var emptyPublicProjects = { error: 'There are no matching public projects.' };
          projectOrganizer.publicProjects.get(q, injectEmptySelectable);

          function injectEmptySelectable(suggestions) {
            if (suggestions.length === 0) {
              cb([emptyPublicProjects]);
            }

            else {
              cb(suggestions);
            }
          }

        };

        var linkName;
        var linkID;
        var theItem = item;

        var theParentNode = projectOrganizer.grid.grid.getData().getItemById(theItem.parentID);
        if (typeof theParentNode === 'undefined') {
            theParentNode = theItem;
            theItem.parentIsSmartFolder = true;
        }
        theItem.parentNode = theParentNode;

            var theParentNodeID = theParentNode.node_id;
            theItem.parentIsSmartFolder = theParentNode.isSmartFolder;
            theItem.parentNodeID = theParentNodeID;


        if (!theItem.isSmartFolder) {
            createProjectDetailHTMLFromTemplate(theItem);
            $('#findNode' + theItem.node_id).hide();
            $('#findNode' + theItem.node_id + ' .typeahead').typeahead({
                    highlight: true
                },
                {
                    name: 'my-projects',
                    displayKey: function (data) {
                        return data.name;
                    },
                    source: mySourceWithEmptySelectable,
                    templates: {
                        header: function () {
                            return '<h3 class="category">My Projects</h3>';
                        },
                        suggestion: function (data) {
                            if(typeof data.name !== 'undefined') {
                                return '<p>' + data.name + '</p>';
                            } else {
                                return '<p>' + data.error + '</p>';
                            }
                        }
                    }
                },
                {
                    name: 'public-projects',
                    displayKey: function (data) {
                        return data.name;
                    },
                    source: publicSourceWithEmptySelectable,
                    templates: {
                        header: function () {
                            return '<h3 class="category">Public Projects</h3>';
                        },
                        suggestion: function (data) {
                            if(typeof data.name !== 'undefined') {
                                return '<p>' + data.name + '</p>';
                            } else {
                                return '<p>' + data.error + '</p>';
                            }
                        }
                    }
                });


            $('#input' + theItem.node_id).bind('keyup', function (event) {
                var key = event.keyCode || event.which;
                var buttonEnabled = (typeof $('#add-link-' + theItem.node_id).prop('disabled') !== 'undefined');

                if (key === 13) {
                    if (buttonEnabled) {
                        $('#add-link-' + theItem.node_id).click(); //submits if the control is active
                    }
                }
                else {
                    $('#add-link-warn-' + theItem.node_id).text('');
                    $('#add-link-' + theItem.node_id).attr('disabled', 'disabled');
                    linkName = '';
                    linkID = '';
                }
            });
            $('#input' + theItem.node_id).bind('typeahead:selected', function (obj, datum, name) {
                var getChildrenURL = theItem.apiURL + 'get_folder_pointers/';
                var children;
                $.getJSON(getChildrenURL, function (data) {
                    children = data;
                    if (children.indexOf(datum.node_id) === -1) {
                        $('#add-link-' + theItem.node_id).removeAttr('disabled');
                        linkName = datum.name;
                        linkID = datum.node_id;
                    } else {
                        $('#add-link-warn-' + theItem.node_id).text('This project is already in the folder');
                    }
                }).fail($osf.handleJSONError);

            });
            $('#close-' + theItem.node_id).click(function () {
                $('.project-details').hide();
                return false;
            });
            $('#add-link-' + theItem.node_id).click(function () {
                var url = '/api/v1/pointer/';
                var postData = JSON.stringify(
                    {
                        pointerID: linkID,
                        toNodeID: theItem.node_id
                    });
                setItemToExpand(theItem, function() {
                    var postAction = $.ajax({
                        type: 'POST',
                        url: url,
                        data: postData,
                        contentType: 'application/json',
                        dataType: 'json'
                    });
                    postAction.done(function () {
                        reloadFolder(projectOrganizer.grid, theItem, theParentNode);
                    });
                });
                return false;
            });

            $('#remove-link-' + theItem.node_id).click(function () {
                var url = '/api/v1/folder/' + theParentNodeID + '/pointer/' + theItem.node_id;
                var deleteAction = $.ajax({
                    type: 'DELETE',
                    url: url,
                    contentType: 'application/json',
                    dataType: 'json'
                });
                deleteAction.done(function () {
                    reloadFolder(projectOrganizer.grid, theParentNode);
                });
            });
            $('#delete-folder-' + theItem.node_id).click(function () {
                bootbox.confirm({
                    title: 'Delete this folder?',
                    message: 'Are you sure you want to delete this folder? This will also delete any folders ' +
                        'inside this one. You will not delete any projects in this folder.',
                    callback: function(result) {
                        if (result !== null && result) {
                            var url = '/api/v1/folder/'+ theItem.node_id;
                            var deleteAction = $.ajax({
                                type: 'DELETE',
                                url: url,
                                contentType: 'application/json',
                                dataType: 'json'
                            });
                            deleteAction.done(function () {
                                reloadFolder(projectOrganizer.grid, theParentNode);
                            });
                        }
                    }
                });
            });
            $('#add-folder-' + theItem.node_id).click(function () {
                $('#buttons' + theItem.node_id).hide();
                $('#rnc-' + theItem.node_id).hide();
                $('#findNode' + theItem.node_id).hide();
                $('#afc-' + theItem.node_id).show();
            });
            $('#add-folder-input' + theItem.node_id).bind('keyup', function () {
                var contents = $.trim($(this).val());
                if (contents === '') {
                    $('#add-folder-button' + theItem.node_id).attr('disabled', 'disabled');
                } else {
                    $('#add-folder-button' + theItem.node_id).removeAttr('disabled');
                }
            });

            $('#add-folder-button' + theItem.node_id).click(function () {
                var url = '/api/v1/folder/';
                var postData = {
                    node_id: theItem.node_id,
                    title: $.trim($('#add-folder-input' + theItem.node_id).val())
                };
                setItemToExpand(theItem, function() {
                    var putAction = $osf.putJSON(url, postData);
                    putAction.done(function () {
                        reloadFolder(projectOrganizer.grid, theItem, theParentNode);
                    }).fail($osf.handleJSONError);

                });
                return false;
            });
            $('#rename-node-' + theItem.node_id).click(function () {
                $('#buttons' + theItem.node_id).hide();
                $('#afc-' + theItem.node_id).hide();
                $('#findNode' + theItem.node_id).hide();
                $('#nc-' + theItem.node_id).hide();
                $('#rnc-' + theItem.node_id).show();
            });
            $('#rename-node-input' + theItem.node_id).bind('keyup', function () {
                var contents = $.trim($(this).val());
                if (contents === '' || contents === theItem.name) {
                    $('#rename-node-button' + theItem.node_id).attr('disabled', 'disabled');
                } else {
                    $('#rename-node-button' + theItem.node_id).removeAttr('disabled');
                }
            });

            $('#rename-node-button' + theItem.node_id).click(function () {
                var url = theItem.apiURL + 'edit/';
                var postData = {
                    name: 'title',
                    value: $.trim($('#rename-node-input' + theItem.node_id).val())
                };
                var postAction = $osf.postJSON(url, postData);
                postAction.done(function () {
                        reloadFolder(projectOrganizer.grid, theParentNode);
                    }).fail($osf.handleJSONError);
                return false;
            });
            $('.cancel-button-' + theItem.node_id).click(function() {
                $('#afc-' + theItem.node_id).hide();
                $('#rnc-' + theItem.node_id).hide();
                $('#findNode' + theItem.node_id).hide();
                $('#nc-' + theItem.node_id).show();
                $('#buttons' + theItem.node_id).show();

            });

            $('#add-item-' + theItem.node_id).click(function () {
                $('#buttons' + theItem.node_id).hide();
                $('#afc-' + theItem.node_id).hide();
                $('#rnc-' + theItem.node_id).hide();
                $('#findNode' + theItem.node_id).show();
            });

            $('.project-details').toggle();
        } else {
            $('.project-details').hide();
        }

    }
};

ProjectOrganizer.Html = $.extend({}, HGrid.Html);
ProjectOrganizer.Col = {};
ProjectOrganizer.Col.Name = $.extend({}, HGrid.Col.Name);

var iconButtons = function (row) {
    var url = row.urls.fetch;
    if (!row.isSmartFolder) {
        var buttonDefs = [
            {
                text: '<i class="project-organizer-info-icon" title=""></i>',
                action: 'showProjectDetails',
                cssClass: 'project-organizer-icon-info',
                attributes:'data-placement="right" data-toggle="tooltip" data-original-title="Info"'
            }
        ];
        if (url !== null) {
            buttonDefs.push({
                text: '<i class="project-organizer-visit-icon" title="" ></i>',
                action: 'visitPage',
                cssClass: 'project-organizer-icon-visit',
                attributes:'data-placement="right" data-toggle="tooltip" data-original-title="Go to page"'
            });
        }
        return HGrid.Fmt.buttons(buttonDefs);
    }

};

var dateModifiedColumn = {
    id: 'date-modified',
    text: 'Modified',
    // Using a function that receives `row` containing all the item information
    itemView: function (row) {
        if (row.modifiedDelta === 0) {
            return '';
        }
        var returnString = moment.utc(row.dateModified).fromNow();
        if (row.modifiedBy !== '') {
            returnString +=  ', ' + row.modifiedBy.toString();
        }
        return returnString;
    },
    folderView: function (row) {
        if (row.modifiedDelta === 0) {
            return '';
        }
        return moment.utc(row.dateModified).fromNow() + ', ' + row.modifiedBy.toString();
    },
    sortable: false,
    selectable: true,
    behavior: 'move',
    width: 40
};

var contributorsColumn = {
    id: 'contributors',
    text: 'Contributors',
    // Using a function that receives `row` containing all the item information
    itemView: function (row) {
        var contributorCount = row.contributors.length;
        if (contributorCount === 0) {
            return '';
        }
        var contributorString = row.contributors[0].name.toString();
        if (contributorCount > 1) {
            contributorString += ' +' + (contributorCount - 1);
        }
        return contributorString;
    },
    folderView: function (row) {
        var contributorCount = row.contributors.length;
        if (contributorCount === 0) {
            return '';
        }
        var contributorString = row.contributors[0].name.toString();
        if (contributorCount > 1) {
            contributorString += ' +' + (contributorCount - 1);
        }
        return contributorString;
    },
    sortable: false,
    selectable: true,
    behavior: 'move',
    width: 30
};

ProjectOrganizer.Col.Name.selectable = true;
ProjectOrganizer.Col.Name.sortable = false;
ProjectOrganizer.Col.Name.behavior = 'move';
ProjectOrganizer.Col.Name.indent = 20;
ProjectOrganizer.Col.Name.showExpander = function(row, args) {
    return (row.childrenCount > 0 &&
            !row._processing && !row.isDashboard);
};
ProjectOrganizer.Col.Name.itemView = function (row) {
    var name = row.name.toString();

    var url = row.urls.fetch;
    var linkString = name;
    var extraClass = '';
    var nodeLink = '';
    var nodeLinkEnd = '';
    if (url != null) {
        nodeLink = '<a href=' + url + '>';
        nodeLinkEnd = '</a>';
    }


    var type = row.type;

    if (row.isSmartFolder) {
        extraClass += ' smart-folder';
    }

    var regType = '';
    if(row.isRegistration){
        regType = 'reg-';
        extraClass += ' registration';
    }
    return nodeLink + "<span class='project-organizer-icon-" + regType + type + "'></span>" + nodeLinkEnd +
        "<span class='project-" + type + extraClass + "'>" + linkString + "</span>";
};
ProjectOrganizer.Col.Name.folderView = ProjectOrganizer.Col.Name.itemView;


//
// Hgrid Init
//

var hgridInit = function () {
    var self = this;
    self.gridData = self.grid.grid.getData();
    self.myProjects = [];
    self.grid.registerPlugin(draggable);
    // Expand/collapse All functions
    $('.pg-expand-all').click(function () {
        expandAllInHGrid(self.grid);
    });
    $('.pg-collapse-all').click(function () {
        collapseAllInHGrid(self.grid);
    });

    // This useful function found on StackOverflow http://stackoverflow.com/a/7385673
    // Used to hide the detail card when you click outside of it onto its containing div
    $(document).click(function (e) {
        var container = $('#project-grid');
        var altContainer = $('.project-details');
        var gridBackground = $('.grid-canvas');
        var gridHeader = $('.slick-header-column');

        if ((!container.is(e.target) && !altContainer.is(e.target) // if the target of the click isn't the container...
            && container.has(e.target).length === 0 && altContainer.has(e.target).length === 0) // ... nor a descendant of the container
            || gridBackground.is(e.target) || gridHeader.is(e.target)) // or the target of the click is the background of the hgrid div
        {
            self.grid.grid.setSelectedRows([]);
            self.grid.grid.resetActiveCell();
        }
    });


    self.publicProjects = new Bloodhound({
        datumTokenizer: function (d) {
            return Bloodhound.tokenizers.whitespace(d.name);
        },
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: '/api/v1/search/projects/?term=%QUERY&maxResults=20&includePublic=yes&includeContributed=no',
            filter: function (projects) {
                return $.map(projects, function (project) {
                    return {
                        name: project.value,
                        node_id: project.id,
                        category: project.category
                    };
                });
            },
            limit: 10
        }

    });

    self.myProjects = new Bloodhound({
        datumTokenizer: function (d) {
            return Bloodhound.tokenizers.whitespace(d.name);
        },
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: '/api/v1/search/projects/?term=%QUERY&maxResults=20&includePublic=no&includeContributed=yes',
            filter: function (projects) {
                return $.map(projects, function (project) {
                    return {
                        name: project.value,
                        node_id: project.id,
                        category: project.category
                    };
                });
            },
            limit: 10
        }
    });

    //
    // When the selection changes, create the div that holds the detail information for the project including
    // whichever action buttons will work with that type of node. This is what will be changed by moving
    // to Knockout.js
    //


    self.grid.grid.onSelectedRowsChanged.subscribe(function (e, args) {
        var selectedRows = self.grid.grid.getSelectedRows();
        if(selectedRows.length > 1) {
            var someItemsAreFolders = false;
            var pointerIds = [];

            selectedRows.forEach(function(item){
                var thisItem = self.grid.grid.getDataItem(item);
                someItemsAreFolders = someItemsAreFolders ||
                                      thisItem.isFolder ||
                                      thisItem.isSmartFolder ||
                                      thisItem.parentIsSmartFolder;
                pointerIds.push(thisItem.node_id);
            });

            if(!someItemsAreFolders) {
                var multiItemDetailTemplateSource = $('#project-detail-multi-item-template').html();
                var detailTemplate = Handlebars.compile(multiItemDetailTemplateSource);
                var detailTemplateContext = {
                    multipleItems: true,
                    itemsCount: selectedRows.length
                };
                var sampleItem = self.grid.grid.getDataItem(selectedRows[0]);
                var theParentNode = self.grid.grid.getData().getItemById(sampleItem.parentID);
                var displayHTML = detailTemplate(detailTemplateContext);
                $('.project-details').html(displayHTML);
                $('.project-details').show();
                $('#remove-links-multiple').click(function(){
                    deleteMultiplePointersFromFolder(self.grid, pointerIds, theParentNode);
                });
                $('#close-multi-select').click(function () {
                    $('.project-details').hide();
                    return false;
                });

            } else {
                $('.project-details').hide();
            }
        } else {
                $('.project-details').hide();
            }


    }); // end onSelectedRowsChanged

    // Disable right clicking within the grid
    // Fixes https://github.com/CenterForOpenScience/openscienceframework.org/issues/945
    self.grid.element[0].oncontextmenu = function() {
        return false;
    };

};


var draggable = new HGrid.Draggable({
    onBeforeDrag: function(){
        $('.project-details').hide();
    },
    onDrag: function (event, items, folder) {

        dragLogic(event, items, folder);
    },
    onDrop: function (event, items, folder) {
        dropLogic(event, items, folder);
    },
    canDrag: function (item) {
        return item.permissions.copyable || item.permissions.movable;
    },
    acceptDrop: function (item, folder, done) {
        done();
    },
    canAcceptDrop: function(items, folder) {
        return canAcceptDrop(items, folder);
    },
    enableMove: false,
    rowMoveManagerOptions: {proxyClass: 'project-organizer-dand'}
});


//
// Public methods
//

function ProjectOrganizer(selector, options) {
    var self = this;
    projectOrganizer = self;
    var baseHGridOptions = {
        width: '98%',
        height: '600',
        columns: [
            ProjectOrganizer.Col.Name,
            {
                text: 'Action',
                itemView: iconButtons,
                folderView: iconButtons,
                width: 10
            },
            contributorsColumn,
            dateModifiedColumn
        ],
        slickgridOptions: {
            editable: true,
            enableAddRow: false,
            enableCellNavigation: true,
            multiSelect: true,
            forceFitColumns: true,
            autoEdit: false,
            addExtraRowsAtEnd: 1
        },
        data: '/api/v1/dashboard/',  // Where to get the initial data
        fetchUrl: function (folder) {
            return '/api/v1/dashboard/' + folder.node_id;
        },
        fetchSuccess: function(newData, item){

            if(reloadNewFolder) {
                reloadNewFolder = false;
                var toReloadItem = draggable.grid.grid.getData().getItemById(rnfToReload);
                if (rnfPrevItem !== rnfToReload && typeof toReloadItem !== 'undefined') {
                    draggable.grid.reloadFolder(toReloadItem);
                }
                draggable.grid.grid.setSelectedRows([]);
                draggable.grid.grid.resetActiveCell();
            }
            if(typeof newData.data !== 'undefined' ) {
                item.childrenCount = newData.data.length;
            } else {
                return false;
            }

            var row = draggable.grid.getDataView().getRowById(item.id);
            draggable.grid.grid.invalidateRow(row);
            draggable.grid.grid.render();
            self.options.success.call();
        },
        fetchError: function(error) {
            if($('.modal-dialog').length === 0) {
                $osf.growl('Error:', error);
            }
        },
        getExpandState: function(folder) {
            return folder.expand;
        },
        onExpand: function(event, item) {
            var self = this;
            item.expand = false;
            self.emptyFolder(item);
            if(typeof event !== 'undefined' && typeof item.apiURL !== 'undefined' && item.type !== 'pointer') {
                setItemToExpand(item);
            }
        },
        onCollapse: function(event, item) {
            item.expand = false;
            if (typeof event !== 'undefined' && typeof item.apiURL !== 'undefined' && item.type !== 'pointer') {
                var collapseUrl = item.apiURL + 'collapse/';
                var postAction = $osf.postJSON(collapseUrl, {});
                postAction.done(function() {
                    item.expand = false;
                    if (item._node._load_status === HGrid.LOADING_FINISHED) {
                        draggable.grid.resetLoadedState(item);
                    }
                }).fail($osf.handleJSONError);
            } else if(typeof event !== 'undefined') {
                if (item._node._load_status === HGrid.LOADING_FINISHED) {
                    draggable.grid.resetLoadedState(item);
                }
            }
        },

        init: hgridInit.bind(self)
    };

    var defaultOptions = {
        success: function() {}
    };

    self.selector = selector;
    self.options = $.extend(defaultOptions, options);
    self.hgridOptions = baseHGridOptions;

    self.init(self);
    self.altKey = false;
}

ProjectOrganizer.prototype.init = function () {
    var self = this;
    self.grid = new HGrid(self.selector, self.hgridOptions);
};

ProjectOrganizer.prototype.getGrid = function() {
    return this.grid;
};

module.exports = ProjectOrganizer;
