/**
 * Handles Project Organizer on dashboard page of OSF.
 * For Treebeard and _item API's check: https://github.com/caneruguz/treebeard/wiki
 */
'use strict';

var Treebeard = require('treebeard');

// CSS
require('css/typeahead.css');
require('css/fangorn.css');
require('css/projectorganizer.css');

var $ = require('jquery');
var m = require('mithril');
var Fangorn = require('js/fangorn');
var bootbox = require('bootbox');
var Bloodhound = require('exports?Bloodhound!typeahead.js');
var moment = require('moment');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
var iconmap = require('js/iconmap');
var legendView = require('js/components/legend').view;
var Fangorn = require('js/fangorn');

var nodeCategories = require('json!built/nodeCategories.json');

// copyMode can be 'copy', 'move', 'forbidden', or null.
// This is set at draglogic and is used as global within this module
var copyMode = null;
// Initialize projectOrganizer object (separate from the ProjectOrganizer constructor at the end)
var projectOrganizer = {};

// Link ID's used to add existing project to folder
var linkName;
var linkID;

// Cross browser key codes for the Command key
var COMMAND_KEYS = [224, 17, 91, 93];
var ESCAPE_KEY = 27;
var ENTER_KEY = 13;

var projectOrganizerCategories = $.extend({}, {
    collection: 'Collections',
    smartCollection: 'Smart Collections',
    project: 'Project',
    link:  'Link'
}, nodeCategories);

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
    var tb = this;
    var preventSelect = function(e){
        e.stopImmediatePropagation();
    };
    var node = item.data; // Where actual data of the node is
    var css = ''; // Keep for future expandability -- Remove: item.data.isSmartFolder ? 'project-smart-folder smart-folder' : '';
    if (item.data.archiving) { // TODO check if this variable will be available
        return  m('span', {'class': 'registration-archiving'}, node.attributes.title + ' [Archiving]');
    } else if(node.links.html){
        return [ m('a.fg-file-links', { 'class' : css, href : node.links.html, onclick : preventSelect}, node.attributes.title),
            m('span', { ondblclick : function(){
                var linkObject = {
                    type : 'node',
                    data : node,
                    label : node.attributes.title
                };
                tb.options.updateFilesData(linkObject);
            }}, ' -Open')
        ];
    } else {
        return  m('span', { 'class' : css}, node.attributes.title);
    }
}

/**
 * Links for going to project pages on the action column
 * @param event Click event
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Column options
 * @this Treebeard.controller Check Treebeard API for methods available
 * @private
 */
function _gotoEvent(event, item) {
    var tb = this;
    var node = item.data;
    if (COMMAND_KEYS.indexOf(tb.pressedKey) !== -1) {
        window.open(node.urls.html, '_blank');
    } else {
        window.open(node.urls.html, '_self');
    }
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


function triggerClickOnItem(item, force) {
    var row = $('.tb-row[data-id="' + item.id + '"]');
    if (force) {
        row.trigger('click');
    }

    if (row.hasClass(this.options.hoverClassMultiselect)) {
        row.trigger('click');
    }
}


/**
 * Contributors have first person's name and then number of contributors. This function returns the proper html
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @returns {Object} A Mithril virtual DOM template object
 * @private
 */
// TODO : May need refactor based on the api data
function _poContributors(item) {
    if (!item.data.contributors) {
        return '';
    }

    return item.data.contributors.map(function (person, index, arr) {
        var comma;
        if (index === 0) {
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
        return m('span', comma + person.name);
    });
}

/**
 * Displays who modified the data and when. i.e. "6 days ago, by Uguz"
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @private
 */
function _poModified(item) {
    var dateString = '';
    var node = item.data;
    dateString = moment.utc(node.attributes.date_modified).fromNow();
    return m('span', dateString);
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
        default_columns;
    if(this.isMultiselected(item.id)){
        item.css = 'fangorn-selected';
    } else {
        item.css = '';
    }

     default_columns = [{
        data : 'name',  // Data field name
        folderIcons : true,
        filter : true,
        css : 'po-draggable', // All projects are draggable since we separated collections from the grid
        custom : _poTitleColumn
    }, {
        data : 'contributors',
        filter : false,
        custom : _poContributors
    }, {
        data : 'dateModified',
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
        width : '50%',
        sort : true,
        sortType : 'text'
    }, {
        title : 'Contributors',
        width : '25%',
        sort : false
    }, {
        title : 'Modified',
        width : '25%',
        sort : false
    });
    return columns;
}

/**
 * Returns custom folder toggle icons for OSF
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {string} Returns a mithril template with m() function, or empty string.
 * @private
 */
function _poResolveToggle(item) {
    var toggleMinus = m('i.fa.fa-minus'),
        togglePlus = m('i.fa.fa-plus'),
        childrenCount = item.data.relationships.children.links.related.meta.count;
    if (item.kind === 'folder' && childrenCount > 0) {
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
    var node = item.data;
    return $osf.apiV2Url('nodes/' + node.uid + '/children', {});
}

/**
 * Hook to run after multiselect is run when an item is selected.
 * @param event Browser click event object
 * @param {Object} tree A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function _poMultiselect(event, tree) {
    var tb = this;
    filterRowsNotInParent.call(tb, tb.multiselected());
    var scrollToItem = false;
    //if (tb.toolbarMode() === 'search') {
    //    _dismissToolbar.call(tb);
    //    scrollToItem = true;
    //    // recursively open parents of the selected item but do not lazyload;
    //    Fangorn.Utils.openParentFolders.call(tb, tree);
    //}
    tb.options.updateSelected(tb.multiselected());
    if (tb.multiselected().length === 1) {
        // temporarily remove classes until mithril redraws raws with another hover.
        //tb.inputValue(tb.multiselected()[0].data.name);
        tb.select('#tb-tbody').removeClass('unselectable');
        //if (scrollToItem) {
        //    Fangorn.Utils.scrollToFile.call(tb, tb.multiselected()[0].id);
        //}
    } else if (tb.multiselected().length > 1) {
        tb.select('#tb-tbody').addClass('unselectable');
    }
    m.redraw();
}

/**
 * When multiple rows are selected remove those that are not in the parent
 * @param {Array} rows List of item objects
 * @returns {Array} newRows Returns the revised list of rows
 */
function filterRowsNotInParent(rows) {
    var tb = this;
    if (tb.multiselected().length < 2) {
        return tb.multiselected();
    }
    var i, newRows = [],
        originalRow = tb.find(tb.multiselected()[0].id),
        originalParent,
        currentItem;
    var changeColor = function() { $(this).css('background-color', ''); };
    if (typeof originalRow !== 'undefined') {
        originalParent = originalRow.parentID;
        for (i = 0; i < rows.length; i++) {
            currentItem = rows[i];
            if (currentItem.parentID === originalParent && currentItem.id !== -1) {
                newRows.push(rows[i]);
            } else {
                $('.tb-row[data-id="' + rows[i].id + '"]').stop().css('background-color', '#D18C93').animate({ backgroundColor: '#fff'}, 500, changeColor);
            }
        }
    }
    tb.multiselected(newRows);
    tb.highlightMultiselect();
    return newRows;
}

function _poIconView(item) {
    var componentIcons = iconmap.componentIcons;
    var projectIcons = iconmap.projectIcons;
    var node = item.data;
    function returnView(type, category) {
        var iconType = projectIcons[type];
        if (type === 'component' || type === 'registeredComponent') {
                iconType = componentIcons[category];
        } else if (type === 'project' || type === 'registeredProject') {
            iconType = projectIcons[category];
        }
        if (type === 'registeredComponent' || type === 'registeredProject') {
            iconType += ' po-icon-registered';
        } else {
            iconType += ' po-icon';
        }
        var template = m('span', { 'class' : iconType});
        return template;
    }
    if (node.attributes.category === 'project') {
        if (node.attributes.registration) {
            return returnView('registeredProject', node.attributes.category);
        } else {
            return returnView('project', node.attributes.category);
        }
    }
    return null;
}

/**
 * OSF-specific Treebeard options common to all addons.
 * For documentation visit: https://github.com/caneruguz/treebeard/wiki
 */
var tbOptions = {
    placement : 'dashboard',
    divID: 'projectOrganizer',
    rowHeight : 35,         // user can override or get from .tb-row height
    showTotal : 15,         // Actually this is calculated with div height, not needed. NEEDS CHECKING
    columnTitles : _poColumnTitles,
    resolveRows : _poResolveRows,
    showFilter : true,     // Gives the option to filter by showing the filter box.
    title : false,          // Title of the grid, boolean, string OR function that returns a string.
    allowMove : true,       // Turn moving on or off.
    moveClass : 'po-draggable',
    hoverClass : 'fangorn-hover',
    multiselect : true,
    hoverClassMultiselect : 'fangorn-selected',
    sortButtonSelector : {
        up : 'i.fa.fa-chevron-up',
        down : 'i.fa.fa-chevron-down'
    },
    sortDepth : 1,
    onload : function () {
        var tb = this,
            rowDiv = tb.select('.tb-row');
        rowDiv.first().trigger('click');
        $('.gridWrapper').on('mouseout', function () {
            tb.select('.tb-row').removeClass('po-hover');
        });
        m.render(document.getElementById('poFilter'), tb.options.filterTemplate.call(this));
    },
    ontogglefolder : function (item, event) {
        if (!item.open) {
            item.load = false;
        }
        $('[data-toggle="tooltip"]').tooltip();
    },
    onscrollcomplete : function () {
        $('[data-toggle="tooltip"]').tooltip();
    },
    onmultiselect : _poMultiselect,
    resolveIcon : _poIconView,
    resolveToggle : _poResolveToggle,
    resolveLazyloadUrl : _poResolveLazyLoad,
    resolveRefreshIcon : function () {
        return m('i.fa.fa-refresh.fa-spin');
    }, naturalScrollLimit : 0,
    removeIcon : function(){
        return m.trust('&times;');
    },
    headerTemplate : function(){ return ''; },
    xhrconfig : function(xhr) {
        xhr.withCredentials = true;
    },
    filterTemplate : function() {
        var tb = this;
        return m('input.pull-left.form-control[placeholder="' + tb.options.filterPlaceholder + '"][type="text"]', {
            style: 'width:100%;display:inline;',
            onkeyup: tb.filter,
            value: tb.filterText()
        });
    },
    lazyLoadPreprocess : function(value){
        var tb = this;
        value.data.map(function(item){
            item.kind = 'folder';
            item.uid = item.id;
            item.name = item.attributes.title;
            // TODO: Dummy data, remove this when api is ready
            item.contributors = [{
                id: '8q36f',
                name : 'Dummy User'
            }];
        });
        console.log('Lazyload processed', value.data);
        return value.data;
    }
};

var ProjectOrganizer = {
    controller : function (args) {
        var poOptions = $.extend(
            {
                updateSelected : args.updateSelected,
                updateFilesData : args.updateFilesData,
                filesData: args.filesData(),
                wrapperSelector : args.wrapperSelector
            },
            tbOptions
        );
        this.tb = new Treebeard(poOptions, true);
    },
    view : function (ctrl, args) {
        return m('.fb-project-organizer#projectOrganizer', ctrl.tb);
    }
};


module.exports = ProjectOrganizer;

