/**
 * Handles Project Organizer on dashboard page of OSF.
 * For Treebeard and _item API's check: https://github.com/caneruguz/treebeard/wiki
 */
'use strict';

var Treebeard = require('treebeard');

// CSS
require('../css/typeahead.css');
require('../css/fangorn.css');
require('../css/projectorganizer.css');

var Handlebars = require('handlebars');
var $ = require('jquery');
var m = require('mithril');
var bootbox = require('bootbox');
var Bloodhound = require('exports?Bloodhound!typeahead.js');
var moment = require('moment');
var Raven = require('raven-js');


var $osf = require('osfHelpers');

// copyMode can be 'copy', 'move', 'forbidden', or null.
// This is set at draglogic and is used as global within this module
var copyMode = null;

// Initialize projectOrganizer object (separate from the ProjectOrganizer constructor at the end)
var projectOrganizer = {};

// Templates load once
var detailTemplateSource = $('#project-detail-template').html();
var detailTemplate = Handlebars.compile(detailTemplateSource);

var multiItemDetailTemplateSource = $('#project-detail-multi-item-template').html();
var multiItemDetailTemplate = Handlebars.compile(multiItemDetailTemplateSource);
var multiItemDetailTemplateSourceNoAction = $('#project-detail-multi-item-no-action').html();
var multiItemDetailTemplateNoAction = Handlebars.compile(multiItemDetailTemplateSourceNoAction);


var $detailDiv = $('.project-details');

/**
 * Bloodhound is a typeahead suggestion engine. Searches here for public projects
 * @type {Bloodhound}
 */
projectOrganizer.publicProjects = new Bloodhound({
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

/**
 * Bloodhound is a typeahead suggestion engine. Searches here for users projects
 * @type {Bloodhound}
 */
projectOrganizer.myProjects = new Bloodhound({
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

/**
 * Edits the template for the column titles.
 * Used here to make smart folder italicized
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller Check Treebeard API for methods available
 * @private
 */
function _poTitleColumn(item) {
    var css = item.data.isSmartFolder ? 'project-smart-folder smart-folder' : '';
    return m('span', { 'class' : css }, item.data.name);
}

/**
 * Links for going to project pages on the action column
 * @param event Click event
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Column options
 * @this Treebeard.controller Check Treebeard API for methods available
 * @private
 */
function _gotoEvent(event, item, col) {
    window.location = item.data.urls.fetch;
}

/**
 * Watching for escape key press
 * @param {String} nodeID Unique ID of the node
 */
function addFormKeyBindings(nodeID) {
    $('#ptd-' + nodeID).keyup(function (e) {
        if (e.which === 27) {
            $('#ptd-' + nodeID).find('.cancel-button-' + nodeID).filter(':visible').click();
            return false;
        }
    });
}

/**
 * The project detail popup is populated based on the row that it was clicked from
 * @param {Object} theItem Only the item.data portion of A Treebeard _item object for the row involved.
 */
function createProjectDetailHTMLFromTemplate(theItem) {
    var detailTemplateContext = {
        theItem: theItem,
        parentIsSmartFolder: theItem.parentIsSmartFolder
    };
    var displayHTML = detailTemplate(detailTemplateContext);
    $detailDiv.html(displayHTML);
    addFormKeyBindings(theItem.node_id);
}

function createBlankProjectDetail(message) {
    var text = message || 'Select a row to view further actions.';
    $detailDiv.html('<div class="row text-muted "> <div class="col-xs-8"> <i class="text-center po-placeholder"> ' + text + ' </i> </div> <div class="col-xs-4"><i class="po-placeholder pull-right"> No Actions </i> </div>');
}

function triggerClickOnItem(item, force) {
    var row = $('.tb-row[data-id="'+ item.id+'"]');
    if (force){
        row.trigger('click');
    }

    if(row.hasClass(this.options.hoverClassMultiselect)){
        row.trigger('click');
    }
}

/**
 * Saves the expand state of a folder so that it can be loaded based on that state
 * @param {Object} item Node data
 * @param {Function} callback
 */
function saveExpandState(item, callback) {
    var collapseUrl,
        postAction,
        expandUrl;
    if (!item.apiURL) {
        return;
    }
    if (item.expand) {
        // turn to false
        collapseUrl = item.apiURL + 'collapse/';
        postAction = $osf.postJSON(collapseUrl, {});
        postAction.done(function () {
            item.expand = false;
            if (typeof callback !== 'undefined') {
                callback();
            }
        }).fail($osf.handleJSONError);
    } else {
        // turn to true
        expandUrl = item.apiURL + 'expand/';
        postAction = $osf.postJSON(expandUrl, {});
        postAction.done(function () {
            item.expand = false;
            if (typeof callback !== 'undefined') {
                callback();
            }
        }).fail($osf.handleJSONError);
    }
}

/**
 * Takes care of all instances of showing any project detail and action. It's the box that appears on clicks
 * @param event Browser event object
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Column information for the column where click happened.
 * @this Treebeard.controller.
 * @private
 */
function _showProjectDetails(event, item, col) {
    event.stopImmediatePropagation();
    var treebeard = this,
        mySourceWithEmptySelectable,
        publicSourceWithEmptySelectable,
        linkName,
        linkID,
        theItem = item.data,
        theParentNode,
        theParentNodeID;
    projectOrganizer.myProjects.initialize();
    projectOrganizer.publicProjects.initialize();
    // injecting error into search results from https://github.com/twitter/typeahead.js/issues/747
    mySourceWithEmptySelectable = function (q, cb) {
        var emptyMyProjects = [{ error: 'There are no matching projects to which you contribute.' }];
        projectOrganizer.myProjects.get(q, injectEmptySelectable);
        function injectEmptySelectable(suggestions) {
            if (suggestions.length === 0) {
                cb(emptyMyProjects);
            } else {
                cb(suggestions);
            }
        }
    };
    publicSourceWithEmptySelectable = function (q, cb) {
        var emptyPublicProjects = { error: 'There are no matching public projects.' };
        projectOrganizer.publicProjects.get(q, injectEmptySelectable);
        function injectEmptySelectable(suggestions) {
            if (suggestions.length === 0) {
                cb([emptyPublicProjects]);
            } else {
                cb(suggestions);
            }
        }
    };

    theParentNode = item.parent();
    if (theParentNode === 'undefined') {
        theParentNode = theItem;
        theItem.parentIsSmartFolder = true;
    }
    theItem.parentNode = theParentNode;
    theParentNodeID = theParentNode.data.node_id;
    theItem.parentIsSmartFolder = theParentNode.data.isSmartFolder;
    theItem.parentNodeID = theParentNodeID;
    if (!theItem.isSmartFolder) {
        createProjectDetailHTMLFromTemplate(theItem);
        $('#findNode' + theItem.node_id).hide();
        $('#findNode' + theItem.node_id + ' .typeahead').typeahead({
            highlight: true
        }, {
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
                    if (typeof data.name !== 'undefined') {
                        return '<p>' + data.name + '</p>';
                    }
                    return '<p>' + data.error + '</p>';
                }
            }
        }, {
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
                    if (typeof data.name !== 'undefined') {
                        return '<p>' + data.name + '</p>';
                    }
                    return '<p>' + data.error + '</p>';
                }
            }
        });
        $('#input' + theItem.node_id).bind('keyup', function (event) {
            var key = event.keyCode || event.which,
                buttonEnabled = (typeof $('#add-link-' + theItem.node_id).prop('disabled') !== 'undefined');

            if (key === 13) {
                if (buttonEnabled) {
                    $('#add-link-' + theItem.node_id).click(); //submits if the control is active
                }
            } else {
                $('#add-link-warn-' + theItem.node_id).text('');
                $('#add-link-' + theItem.node_id).attr('disabled', 'disabled');
                linkName = '';
                linkID = '';
            }
        });
        $('#input' + theItem.node_id).bind('typeahead:selected', function (obj, datum, name) {
            var getChildrenURL = theItem.apiURL + 'get_folder_pointers/',
                children;
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
            createBlankProjectDetail();
            return false;
        });
        $('#add-link-' + theItem.node_id).click(function () {
            var url = '/api/v1/pointer/',
                postData = JSON.stringify({
                    pointerID: linkID,
                    toNodeID: theItem.node_id
                });
            theItem.expand = false;
            saveExpandState(theItem, function () {
                var tb = treebeard,
                    postAction = $.ajax({
                        type: 'POST',
                        url: url,
                        data: postData,
                        contentType: 'application/json',
                        dataType: 'json'
                    });
                postAction.done(function () {
                    tb.updateFolder(null, item);
                });
            });
            triggerClickOnItem.call(treebeard, item);
            return false;
        });
        $('#remove-link-' + theItem.node_id).click(function () {
            var url = '/api/v1/folder/' + theParentNodeID + '/pointer/' + theItem.node_id,
                deleteAction = $.ajax({
                    type: 'DELETE',
                    url: url,
                    contentType: 'application/json',
                    dataType: 'json'
                });
            deleteAction.done(function () {
                treebeard.updateFolder(null, theParentNode);
                createBlankProjectDetail();

            });
        });
        $('#delete-folder-' + theItem.node_id).click(function () {
            bootbox.confirm({
                title: 'Delete this folder?',
                message: 'Are you sure you want to delete this folder? This will also delete any folders ' +
                    'inside this one. You will not delete any projects in this folder.',
                callback: function (result) {
                    if (result !== null && result) {
                        var url = '/api/v1/folder/' + theItem.node_id,
                            deleteAction = $.ajax({
                                type: 'DELETE',
                                url: url,
                                contentType: 'application/json',
                                dataType: 'json'
                            });
                        deleteAction.done(function () {
                            treebeard.updateFolder(null, item.parent());
                            createBlankProjectDetail();
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
            $('#add-folder-input' + theItem.node_id).focus();
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
            var url = '/api/v1/folder/',
                postData = {
                    node_id: theItem.node_id,
                    title: $.trim($('#add-folder-input' + theItem.node_id).val())
                };
            theItem.expand = false;
            saveExpandState(theItem, function () {
                var putAction = $osf.putJSON(url, postData);
                putAction.done(function () {
                    //var icon = $('.tb-row[data-id="' + item.id + '"]').find('.tb-toggle-icon'),
                    //    iconTemplate = treebeard.options.resolveToggle.call(treebeard, item);
                    //if (icon.get(0)) {
                    //    m.render(icon.get(0), iconTemplate);
                    //}
                    treebeard.updateFolder(null, item);
                    triggerClickOnItem.call(treebeard, item);
                }).fail($osf.handleJSONError);

            });
            return false;
        });
        $('#rename-node-' + theItem.node_id).click(function () {
            $('#buttons' + theItem.node_id).hide();
            $('#afc-' + theItem.node_id).hide();
            $('#findNode' + theItem.node_id).hide();
            $('#nc-' + theItem.node_id).hide();
            $('#rnc-' + theItem.node_id).css({'display':'inline-block', 'width' : '100%'});
            $('#rename-node-input' + theItem.node_id).focus();
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
            var url = theItem.apiURL + 'edit/',
                postAction,
                postData = {
                    name: 'title',
                    value: $.trim($('#rename-node-input' + theItem.node_id).val())
                };
            postAction = $osf.postJSON(url, postData);
            postAction.done(function () {
                treebeard.updateFolder(null, treebeard.find(1));
                // Also update every
            }).fail($osf.handleJSONError);
            return false;
        });
        $('.cancel-button-' + theItem.node_id).click(function () {
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
            $('#input' + theItem.node_id).focus();
        });
    } else {
        createBlankProjectDetail(theItem.name);
    }
}

/**
 * Project Organizer actions, has info and go to project
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Column information for the column where click happened.
 * @returns {Array} An array of buttons in mithril view format using mithril's m()
 * @private
 */
function _poActionColumn(item, col) {
    var self = this,
        buttons = [],
        url = item.data.urls.fetch;
    if (!item.data.isSmartFolder) {
        if (url !== null) {
            buttons.push({
                'name' : '',
                'icon' : 'icon-chevron-right',
                'css' : 'project-organizer-icon-visit fangorn-clickable btn btn-info btn-xs',
                'onclick' : _gotoEvent
            });
        }
    }
    // Build the template for icons
    return buttons.map(function (btn) {
        return m('span', { 'data-col' : item.id }, [ m('i',
            { 'class' : btn.css, 'data-toggle' : 'tooltip', title : 'Go to page', 'data-placement': 'bottom','style' : btn.style, 'onclick' : function (event) {  btn.onclick.call(self, event, item, col); } },
            [ m('span', { 'class' : btn.icon}, btn.name) ])
            ]);
    });
}

/**
 * Contributors have first person's name and then number of contributors. This functio nreturns the proper html
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @returns {Object} A Mithril virtual DOM template object
 * @private
 */
function _poContributors(item) {
    if (!item.data.contributors) {
        return '';
    }

    return item.data.contributors.map(function (person, index, arr) {
        var comma;
        if(index === 0) {
            comma = '';
        } else {
            comma = ', ';
        }
        if (index > 2) {
            return;
        }
        if (index === 2) {
            return m('span', ' + ' + (arr.length - 2));
        }
        return m('span', comma + person.name );
    });
}

/**
 * Displays who modified the data and when. i.e. "6 days ago, by Uguz"
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @private
 */
function _poModified(item) {
    var personString,
        dateString;
    if (item.data.modifiedDelta === 0) {
        return m('span');
    }
    dateString = moment.utc(item.data.dateModified).fromNow();
    if (item.data.modifiedBy !== '') {
        personString = item.data.modifiedBy.toString();
    }
    return m('span', dateString + ', by ' + personString);
}

/**
 * Organizes all the row displays based on what that item requires.
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @returns {Array} An array of columns as col objects
 * @this Treebeard.controller Check Treebeard API For available methods
 * @private
 */
function _poResolveRows(item) {
    var css = '',
        draggable = false,
        default_columns;
    if (item.data.permissions) {
        draggable = item.data.permissions.movable || item.data.permissions.copyable;
    }
    if (draggable) {
        css = 'po-draggable';
    }
    item.css = '';
    default_columns = [{
        data : 'name',  // Data field name
        folderIcons : true,
        filter : true,
        css : css,
        custom : _poTitleColumn
    }, {
        sortInclude : false,
        custom : _poActionColumn
    }, {
        filter : true,
        custom : _poContributors
    }, {
        filter : false,
        custom : _poModified
    }];
    return default_columns;
}

/**
 * Organizes the information for Column title row.
 * @returns {Array} An array of columns with pertinent column information
 * @private
 */
function _poColumnTitles() {
    var columns = [];
    columns.push({
        title: 'Name',
        width : '45%',
        sort : false
    }, {
        title : 'Actions',
        width : '10%',
        sort : false
    }, {
        title : 'Contributors',
        width : '20%',
        sort : false
    }, {
        title : 'Modified',
        width : '25%',
        sort : false
    });
    return columns;
}

/**
 * Checks if folder toggle is permitted (i.e. contents are private)
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {boolean}
 * @private
 */
function _poToggleCheck(item) {
    if (item.data.permissions.view) {
        return true;
    }
    item.notify.update('Not allowed: Private folder', 'warning', 1, undefined);
    return false;
}

/**
 * Returns custom icons for OSF depending on the type of item
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {Object}  Returns a mithril template with the m() function.
 * @private
 */
function _poResolveIcon(item) {
    var viewLink,
        icons = {
            folder : 'project-organizer-icon-folder',
            smartFolder : 'project-organizer-icon-smart-folder',
            project : 'project-organizer-icon-project',
            registration :  'project-organizer-icon-reg-project',
            component :  'project-organizer-icon-component',
            registeredComponent :  'project-organizer-icon-reg-component',
            link :  'project-organizer-icon-pointer'
        };
    viewLink = item.data.urls.fetch;
    function returnView(type) {
        var template = m('span', { 'class' : icons[type]});
        if (viewLink) {
            return m('a', { href : viewLink}, template);
        }
        return template;
    }
    if (item.data.isSmartFolder) {
        return returnView('smartFolder');
    }
    if (item.data.isFolder) {
        return returnView('folder');
    }
    if(item.data.isPointer && !item.parent().data.isFolder){
        return returnView('link');
    }
    if (item.data.isProject) {
        if (item.data.isRegistration) {
            return returnView('registration');
        } else {
            return returnView('project');
        }
    }

    if (item.data.isComponent) {
        if (item.data.isRegistration) {
            return returnView('registeredComponent');
        }else {
            return returnView('component');
        }
    }

    if (item.data.isPointer) {
        return returnView('link');
    }
    return returnView('folder');
}

/**
 * Returns custom folder toggle icons for OSF
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {string} Returns a mithril template with m() function, or empty string.
 * @private
 */
function _poResolveToggle(item) {
    var toggleMinus = m('i.icon-minus'),
        togglePlus = m('i.icon-plus'),
        childrenCount = item.data.childrenCount || item.children.length;
    if (item.kind === 'folder' && childrenCount > 0 && item.depth > 1) {
        if (item.open) {
            return toggleMinus;
        }
        return togglePlus;
    }
    return '';
}

/**
 * Resolves lazy load url for fetching children
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {String|Boolean} Returns the fetch URL in string or false if there is no url.
 * @private
 */
function _poResolveLazyLoad(item) {

    return '/api/v1/dashboard/' + item.data.node_id;
}

/**
 * Hook to run after lazyloading has successfully loaded
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function expandStateLoad(item) {
    var tb = this,
        i;
    if(item.children.length === 0 && item.data.childrenCount > 0){
        item.data.childrenCount = 0;
        tb.updateFolder(null, item);
    }
    if (item.children.length > 0 && item.depth > 0) {
        for (i = 0; i < item.children.length; i++) {
            if (item.children[i].data.expand) {
                tb.updateFolder(null, item.children[i]);
            }
            if(tb.multiselected[0] && item.children[i].data.node_id === tb.multiselected[0].data.node_id) {
                triggerClickOnItem.call(tb, item.children[i], true);
            }
        }
    }
    _cleanupMithril();
}

/**
 * Loads the children of an item that need to be expanded. Unique to Projectorganizer
 * @private
 */
function _poLoadOpenChildren() {
    var tb = this;
    this.treeData.children.map(function (item) {
        if (item.data.expand) {
            tb.updateFolder(null, item);
        }
    });
}

/**
 * Hook to run after multiselect is run when an item is selected.
 * @param event Browser click event object
 * @param {Object} tree A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function _poMultiselect(event, tree) {
    var tb = this,
        selectedRows = filterRowsNotInParent.call(tb, tb.multiselected),
        someItemsAreFolders,
        pointerIds;
    if (selectedRows.length > 1) {
        someItemsAreFolders = false;
        pointerIds = [];
        selectedRows.forEach(function (item) {
            var thisItem = item.data;
            someItemsAreFolders = someItemsAreFolders ||
                                  thisItem.isFolder ||
                                  thisItem.isSmartFolder ||
                                  thisItem.parentIsSmartFolder ||
                                  !thisItem.permissions.movable;
            pointerIds.push(thisItem.node_id);
        });
        var detailTemplateContext;
        if(!selectedRows[0].parent().data.isFolder){
            detailTemplateContext = {
                itemsCount: selectedRows.length
            };
            var theParentNode = selectedRows[0].parent();
            var displayHTML = multiItemDetailTemplateNoAction(detailTemplateContext);
            $detailDiv.html(displayHTML).show();
        } else {
            if (!someItemsAreFolders) {
                detailTemplateContext = {
                    multipleItems: true,
                    itemsCount: selectedRows.length
                };
                var theParentNode = selectedRows[0].parent();
                var displayHTML = multiItemDetailTemplate(detailTemplateContext);
                $detailDiv.html(displayHTML).show();
                $('#remove-links-multiple').click(function () {
                    deleteMultiplePointersFromFolder.call(tb, pointerIds, theParentNode);
                    createBlankProjectDetail();
                });
                $('#close-multi-select').click(function () {
                    createBlankProjectDetail();
                    return false;
                });
            } else {
                detailTemplateContext = {
                    itemsCount: selectedRows.length
                };
                var theParentNode = selectedRows[0].parent();
                var displayHTML = multiItemDetailTemplateNoAction(detailTemplateContext);
                $detailDiv.html(displayHTML).show();
            }
        }
    } else {
        _showProjectDetails.call(tb, event, tb.multiselected[0]);
    }
}



/**
 * Deletes pointers based on their ids from the folder specified
 * @param {String} pointerIds Unique node ids
 * @param folderToDeleteFrom  What it says
 */
function deleteMultiplePointersFromFolder(pointerIds, folderToDeleteFrom) {
    var tb = this,
        folderNodeId,
        url,
        postData,
        deleteAction;
    if (pointerIds.length > 0) {
        folderNodeId = folderToDeleteFrom.data.node_id;
        url = '/api/v1/folder/' + folderNodeId + '/pointers/';
        postData = JSON.stringify({pointerIds: pointerIds});
        deleteAction = $.ajax({
            type: 'DELETE',
            url: url,
            data: postData,
            contentType: 'application/json',
            dataType: 'json'
        });
        deleteAction.done(function () {
            tb.updateFolder(null, folderToDeleteFrom);
        });
        deleteAction.fail(function (jqxhr, textStatus, errorThrown) {
            $osf.growl('Error:', textStatus + '. ' + errorThrown);
        });
    }
}

/**
 * When multiple rows are selected remove those that are not in the parent
 * @param {Array} rows List of item objects
 * @returns {Array} newRows Returns the revised list of rows
 */
function filterRowsNotInParent(rows) {
    if (this.multiselected.length < 2) {
        return this.multiselected;
    }
    var i, newRows = [],
        originalRow = this.find(this.multiselected[0].id),
        originalParent,
        currentItem;
    if (typeof originalRow !== "undefined") {
        originalParent = originalRow.parentID;
        for (i = 0; i < rows.length; i++) {
            currentItem = rows[i];
            if (currentItem.parentID === originalParent && currentItem.id !== -1) {
                newRows.push(rows[i]);
            }
        }
    }
    this.multiselected = newRows;
    this.highlightMultiselect();
    return newRows;
}

/**
 * Hook for the drag start event on jquery
 * @param event jQuery UI drggable event object
 * @param ui jQuery UI draggable ui object
 * @private
 */
function _poDragStart(event, ui) {
    var itemID = $(event.target).attr('data-id'),
        item = this.find(itemID);
    if (this.multiselected.length < 2) {
        this.multiselected = [item];
    }
    createBlankProjectDetail();
}

/**
 * Hook for the drop event of jQuery UI droppable
 * @param event jQuery UI droppable event object
 * @param ui jQuery UI droppable ui object
 * @private
 */
function _poDrop(event, ui) {
    var items = this.multiselected.length === 0 ? [this.find(this.selected)] : this.multiselected,
        folder = this.find($(event.target).attr('data-id'));
    dropLogic.call(this, event, items, folder);
}

/**
 * Hook for the over event of jQuery UI droppable
 * @param event jQuery UI droppable event object
 * @param ui jQuery UI droppable ui object
 * @private
 */
function _poOver(event, ui) {
    var items = this.multiselected.length === 0 ? [this.find(this.selected)] : this.multiselected,
        folder = this.find($(event.target).attr('data-id')),
        dragState = dragLogic.call(this, event, items, ui);
    $('.tb-row').removeClass('tb-h-success po-hover');
    if (dragState !== 'forbidden') {
        $('.tb-row[data-id="' + folder.id + '"]').addClass('tb-h-success');
    } else {
        $('.tb-row[data-id="' + folder.id + '"]').addClass('po-hover');
    }
}

// Sets the state of the alt key by listening for key presses in the document.
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

/**
 * Sets the copy state based on which item is being dragged on which other item
 * @param {Object} event Browser drag event
 * @param {Array} items List of items being dragged at the time. Each item is a _item object
 * @param {Object} ui jQuery UI draggable drag ui object
 * @returns {String} copyMode One of the copy states, from 'copy', 'move', 'forbidden'
 */
function dragLogic(event, items, ui) {
    var canCopy = true,
        canMove = true,
        folder = this.find($(event.target).attr('data-id')),
        isSelf = false,
        dragGhost = $('.tb-drag-ghost');
    items.forEach(function (item) {
        if (!isSelf) {
            isSelf = item.id === folder.id;
        }
        canCopy = canCopy && item.data.permissions.copyable;
        canMove = canMove && item.data.permissions.movable;
    });
    if (canAcceptDrop(items, folder) && (canMove || canCopy)) {
        if (canMove && canCopy) {
            if (altKey) {
                copyMode = 'copy';
            } else {
                copyMode = 'move';
            }
        }
        if (canMove && !canCopy) {
            copyMode = 'move';
        }
        if (canCopy && !canMove) {
            copyMode = 'copy';
        }
    } else {
        copyMode = 'forbidden';
    }
    if (isSelf) {
        copyMode = 'forbidden';
    }
    // Set the cursor to match the appropriate copy mode
    // Remember that Treebeard is using tb-drag-ghost instead of ui.helper

    switch (copyMode) {
    case 'forbidden':
        dragGhost.css('cursor', 'not-allowed');
        break;
    case 'copy':
        dragGhost.css('cursor', 'copy');
        break;
    case 'move':
        dragGhost.css('cursor', 'move');
        break;
    default:
        dragGhost.css('cursor', 'default');
    }
    return copyMode;
}

/**
 * Checks if the folder can accept the items dropped on it
 * @param {Array} items List of items being dragged at the time. Each item is a _item object
 * @param {Object} folder Folder information as _item object, the drop target
 * @returns {boolean} canDrop Whether drop can happen
 */
function canAcceptDrop(items, folder) {
    var representativeItem,
        itemParentNodeId,
        hasComponents,
        hasFolders,
        copyable,
        movable,
        canDrop;
    if (folder.data.isSmartFolder || !folder.data.isFolder) {
        return false;
    }
    // if the folder is contained by the item, return false
    representativeItem = items[0];
    if (representativeItem.isAncestor(folder) || representativeItem.id === folder.id) {
        return false;
    }
    // If trying to drop on the folder it came from originally, return false
    itemParentNodeId = representativeItem.parent().data.node_id;
    if (itemParentNodeId === folder.data.node_id) {
        return false;
    }
    hasComponents = false;
    hasFolders = false;
    copyable = true;
    movable = true;
    canDrop = true;
    items.forEach(function (item) {
        hasComponents = hasComponents || item.data.isComponent;
        hasFolders = hasFolders || item.data.isFolder;
        copyable = copyable && item.data.permissions.copyable;
        movable = movable && item.data.permissions.movable;
    });
    if (hasComponents) {
        canDrop = canDrop && folder.data.permissions.acceptsComponents;
    }
    if (hasFolders) {
        canDrop = canDrop && folder.data.permissions.acceptsFolders;
    }
    if (copyMode === 'move') {
        canDrop = canDrop && folder.data.permissions.acceptsMoves && movable;
    }
    if (copyMode === 'copy') {
        canDrop = canDrop && folder.data.permissions.acceptsCopies && copyable;
    }
    return canDrop;
}

/**
 * Where the drop actions happen
 * @param event jQuery UI drop event
 * @param {Array} items List of items being dragged at the time. Each item is a _item object
 * @param {Object} folder Folder information as _item object
 */
function dropLogic(event, items, folder) {
    var tb = this,
        theFolderNodeID,
        getChildrenURL,
        folderChildren,
        sampleItem,
        itemParent,
        itemParentNodeID,
        getAction;
    if (typeof folder !== 'undefined' && !folder.data.isSmartFolder && folder !== null && folder.data.isFolder) {
        theFolderNodeID = folder.data.node_id;
        getChildrenURL = folder.data.apiURL + 'get_folder_pointers/';
        sampleItem = items[0];
        itemParent = sampleItem.parent();
        itemParentNodeID = itemParent.data.node_id;
        if (itemParentNodeID !== theFolderNodeID) { // This shouldn't happen, but if it does, it's bad
            getAction = $.getJSON(getChildrenURL, function (data) {
                folderChildren = data;
                var itemsToMove = [],
                    itemsNotToMove = [],
                    postInfo;
                items.forEach(function (item) {
                    if ($.inArray(item.data.node_id, folderChildren) === -1) { // pointer not in folder to be moved to
                        itemsToMove.push(item.data.node_id);
                    } else if (copyMode === 'move') { // Pointer is already in the folder and it's a move
                                // We  need to make sure not to delete the folder if the item is moved to the same folder.
                                // When we add the ability to reorganize within a folder, this will have to change.
                        itemsNotToMove.push(item.data.node_id);
                    }
                });
                postInfo = {
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
                    deleteMultiplePointersFromFolder.call(tb, itemsNotToMove, itemParent);
                    if (itemsToMove.length > 0) {
                        var url = postInfo[copyMode]['url'],
                            postData = JSON.stringify(postInfo[copyMode]['json']),
                            outerFolder = whichIsContainer.call(tb, itemParent, folder),
                            postAction = $.ajax({
                                type: 'POST',
                                url: url,
                                data: postData,
                                contentType: 'application/json',
                                dataType: 'json'
                            });
                        postAction.always(function (result) {
                            if (copyMode === 'move') {
                                if (!outerFolder) {
                                    tb.updateFolder(null, itemParent);
                                    tb.updateFolder(null, folder);
                                } else {
                                    // if item is closed folder save expand state to be open
                                    if(!folder.data.expand){
                                        saveExpandState(folder.data, function(){
                                            tb.updateFolder(null, outerFolder);
                                        });
                                    } else {
                                        tb.updateFolder(null, outerFolder);
                                    }
                                }
                            } else {
                                tb.updateFolder(null, folder);
                            }
                        });
                        postAction.fail(function (jqxhr, textStatus, errorThrown) {
                            $osf.growl('Error:', textStatus + '. ' + errorThrown);
                        });
                    }
                }
            });
            getAction.fail(function (jqxhr, textStatus, errorThrown) {
                $osf.growl('Error:', textStatus + '. ' + errorThrown);
            });
        } else {
            Raven.captureMessage('Project dashboard: Parent node (' + itemParentNodeID + ') == Folder Node (' + theFolderNodeID + ')');
        }
    } else {
        if (typeof folder === 'undefined') {
            Raven.captureMessage('onDrop folder is undefined.');
        }
    }
    $('.project-organizer-dand').css('cursor', 'default');
}

/**
 * Checks if one of the items being moved contains the other. To check for adding parents to children
 * @param {Object} itemOne Treebeard _item object, has the _item API
 * @param {Object} itemTwo Treebeard _item object, has the _item API
 * @returns {null|Object} Returns object if one is containing the other. Null if neither or both
 */
function whichIsContainer(itemOne, itemTwo) {
    var isOneAncestor = itemOne.isAncestor(itemTwo),
        isTwoAncestor = itemTwo.isAncestor(itemOne);
    if (isOneAncestor && isTwoAncestor) {
        return null;
    }
    if (isOneAncestor) {
        return itemOne;
    }
    if (isTwoAncestor) {
        return itemTwo;
    }
    return null;
}

function _cleanupMithril() {
    // Clean up Mithril related redraw issues
    $('.tb-toggle-icon').each(function(){
        var children = $(this).children('i');
        if (children.length > 1) {
            children.last().remove();
        }
    });
}

//
/**
 * OSF-specific Treebeard options common to all addons.
 * For documentation visit: https://github.com/caneruguz/treebeard/wiki
 */
var tbOptions = {
    rowHeight : 27,         // user can override or get from .tb-row height
    showTotal : 15,         // Actually this is calculated with div height, not needed. NEEDS CHECKING
    paginate : false,       // Whether the applet starts with pagination or not.
    paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
    uploads : false,         // Turns dropzone on/off.
    columnTitles : _poColumnTitles,
    resolveRows : _poResolveRows,
    showFilter : false,     // Gives the option to filter by showing the filter box.
    title : false,          // Title of the grid, boolean, string OR function that returns a string.
    allowMove : true,       // Turn moving on or off.
    moveClass : 'po-draggable',
    hoverClass : 'po-hover',
    hoverClassMultiselect : 'po-hover-multiselect',
    togglecheck : _poToggleCheck,
    sortButtonSelector : {
        up : 'i.icon-chevron-up',
        down : 'i.icon-chevron-down'
    },
    dragOptions : {},
    dropOptions : {},
    dragEvents : {
        start : _poDragStart
    },
    dropEvents : {
        drop : _poDrop,
        over : _poOver
    },
    onload : function () {
        var tb = this,
            rowDiv = $('.tb-row');
        _poLoadOpenChildren.call(tb);
       rowDiv.first().trigger('click');

        $('.gridWrapper').on('mouseout', function(){
            rowDiv.removeClass('po-hover');
        });


    },
    createcheck : function (item, parent) {
        return true;
    },
    deletecheck : function (item) {
        return true;
    },
    ontogglefolder : function (item, event) {
        if (event) {
            saveExpandState(item.data);
        }
        if (!item.open) {
            item.load = false;
        }
        $('[data-toggle="tooltip"]').tooltip();
    },
    onscrollcomplete : function(){
        $('[data-toggle="tooltip"]').tooltip();
        _cleanupMithril();
    },
    onmultiselect : _poMultiselect,
    resolveIcon : _poResolveIcon,
    resolveToggle : _poResolveToggle,
    resolveLazyloadUrl : _poResolveLazyLoad,
    lazyLoadOnLoad : expandStateLoad
};

/**
 * Initialize Project organizer in the fashion of Fangorn. Prepeares an option object within ProjectOrganizer
 * @param options Treebeard type options to be extended with Treebeard default options.
 * @constructor
 */
function ProjectOrganizer(options) {
    this.options = $.extend({}, tbOptions, options);
    this.grid = null; // Set by _initGrid
    this.init();
}

/**
 * Project organizer prototype object with init functions set to Treebeard.
 * @type {{constructor: ProjectOrganizer, init: Function, _initGrid: Function}}
 */
ProjectOrganizer.prototype = {
    constructor: ProjectOrganizer,
    init: function () {
        this._initGrid();
    },
    _initGrid: function () {
        this.grid = new Treebeard(this.options);
        return this.grid;
    }
};

module.exports = ProjectOrganizer;
