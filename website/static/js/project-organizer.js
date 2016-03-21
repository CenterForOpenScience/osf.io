/**
 * Handles Project Organizer on dashboard page of OSF.
 * For Treebeard and _item API's check: https://github.com/caneruguz/treebeard/wiki
 */
'use strict';

var Treebeard = require('treebeard');

// CSS
require('css/typeahead.css');
require('css/fangorn.css');

var $ = require('jquery');
var m = require('mithril');
var moment = require('moment');
var $osf = require('js/osfHelpers');


var LinkObject;
var allProjectsCache;
var formatDataforPO;
var allTopLevelProjectsCache;

/**
 * Edits the template for the column titles.
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
        return [ m('a.fg-file-links', { 'class' : css, href : node.links.html, 'data-nodeID' : node.id, onclick : function(event) {
            preventSelect.call(this, event);
            $osf.trackClick('myProjects', 'projectOrganizer', 'navigate-to-specific-project');
        }}, node.attributes.title) ];
    } else {
        return  m('span', { 'class' : css, 'data-nodeID' : node.id }, node.attributes.title);
    }
}

/**
 * Contributors have first person's name and then number of contributors. This function returns the proper html
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @returns {Object} A Mithril virtual DOM template object
 * @private
 */
function _poContributors(item) {
    var contributorList = item.data.embeds.contributors.data;
    if (contributorList.length === 0) {
        return '';
    }

    return contributorList.map(function (person, index, arr) {
        var name;
        var familyName = person.embeds.users.data.attributes.family_name;
        var givenName = person.embeds.users.data.attributes.given_name;
        var fullName = person.embeds.users.data.attributes.full_name;
        if (familyName) {
            name = familyName;
        } else if(givenName){
            name = givenName;
        } else if(fullName){
            name = fullName;
        } else {
            name = 'A contributor';
        }
        var comma;
        if (index === 0) {
            comma = '';
        } else {
            comma = ', ';
        }
        if (index > 2) {
            return m('span');
        }
        if (index === 2) {
            return m('span', ' + ' + (arr.length - 2));
        }
        return m('span', comma + name);
    });
}

/**
 * Displays date modified
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @private
 */
function _poModified(item) {
    var node = item.data;
    var dateString = moment.utc(node.attributes.date_modified).fromNow();
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
    var mobile = window.innerWidth < 767; // true if mobile view
    var tb = this;
    var folderIcons = !tb.filterOn;
    var defaultColumns = [];

    if(this.isMultiselected(item.id)){
        item.css = 'fangorn-selected';
    } else {
        item.css = '';
    }

    defaultColumns.push({
        data : 'name',  // Data field name
        folderIcons : folderIcons,
        filter : true,
        css : 'po-draggable', // All projects are draggable since we separated collections from the grid
        custom : _poTitleColumn
    });

    if (!mobile) {
        defaultColumns.push({
            data : 'contributors',
            filter : true,
            custom : _poContributors
        }, {
            data : 'dateModified',
            filter : false,
            custom : _poModified
        });
    } else {
        defaultColumns.push({
            data : 'name',
            filter : false,
            custom : function (row){
                return m('.btn.btn-default.btn-sm[data-toggle="modal"][data-target="#infoModal"]', {
                }, m('i.fa.fa-ellipsis-h', {onclick: function() {
                    $osf.trackClick('myProjects', 'mobile', 'open-information-panel');
                }}));
            }
        });
    }

    return defaultColumns;
}

/**
 * Organizes the information for Column title row.
 * @returns {Array} An array of columns with pertinent column information
 * @private
 */
function _poColumnTitles() {
    var columns = [];
    var mobile = window.innerWidth < 767; // true if mobile view
    if(!mobile){
        columns.push({
            title: 'Name',
            width : '50%',
            sort : true,
            sortType : 'text'
        },{
            title : 'Contributors',
            width : '25%',
            sort : false
        }, {
            title : 'Modified',
            width : '25%',
            sort : false
        });
    } else {
        columns.push({
            title: 'Name',
            width : '90%',
            sort : true,
            sortType : 'text'
        },{
            title : '',
            width : '10%',
            sort : false
        });
    }

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
    var toggleMinus = m('i.fa.fa-minus');
    var togglePlus = m('i.fa.fa-plus');
    var childrenCount = item.data.relationships.children ? item.data.relationships.children.links.related.meta.count : 0;
    if (childrenCount > 0) {
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
    if(item.children.length > 0) {
        return false;
    }
    if(node.relationships.children){
        //return node.relationships.children.links.related.href;
        var urlPrefix = node.attributes.registration ? 'registrations' : 'nodes';
        return $osf.apiV2Url(urlPrefix + '/' + node.id + '/children/', {
            query : {
                'related_counts' : 'children',
                'embed' : 'contributors'
            }
        });
    }
    return false;
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
    tb.options.updateSelected(tb.multiselected());
    if (tb.multiselected().length === 1) {
        tb.select('#tb-tbody').removeClass('unselectable');
        if (event.currentTarget != null) {
            $osf.trackClick('myProjects', 'projectOrganizer', 'single-project-selected');
        }
    } else if (tb.multiselected().length > 1) {
        $osf.trackClick('myProjects', 'projectOrganizer', 'multiple-projects-selected');
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
                // The following row flashes a pastel red shade for a short time to denote that the row in question can't be multiselected with others
                $('.tb-row[data-id="' + rows[i].id + '"]').stop().css('background-color', '#D18C93').animate({ backgroundColor: '#fff'}, 500, changeColor);
            }
        }
    }
    tb.multiselected(newRows);
    tb.highlightMultiselect();
    return newRows;
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
        up : 'i.fa.fa-angle-up',
        down : 'i.fa.fa-angle-down'
    },
    sortDepth : 0,
    onload : function () {
        var tb = this,
            rowDiv = tb.select('.tb-row');
        rowDiv.first().trigger('click');
        $('.gridWrapper').on('mouseout', function () {
            tb.select('.tb-row').removeClass('po-hover');
        });
        m.render($(tb.options.dragContainment + ' .db-poFilter').get(0), tb.options.filterTemplate.call(this));
        tb.options.mpTreeData(tb.treeData);
        tb.options.mpBuildTree(tb.buildTree);
        tb.options.mpUpdateFolder(tb.updateFolder);
    },
    ontogglefolder : function (item, event) {
        $osf.trackClick('myProjects', 'projectOrganizer', 'expand-collapse-project-children');
        if (!item.open) {
            item.load = false;
        }
        $('[data-toggle="tooltip"]').tooltip();
    },
    onscrollcomplete : function () {
        $('[data-toggle="tooltip"]').tooltip();
    },
    onmultiselect : _poMultiselect,
    resolveIcon : function _poIconView(item) { // Project Organizer doesn't use icons
        return false;
    },
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
    ondblclickrow : function(item, event){
        var tb = this;
        $osf.trackClick('myProjects', 'projectOrganizer', 'double-click-project');
        var node = item.data;
        var linkObject = new LinkObject('node', node, node.attributes.title);
        // Get ancestors
        linkObject.ancestors = [];
        function getAncestors (item) {
            var parent = item.parent();
            if(parent && parent.id > tb.treeData.id) {
                linkObject.ancestors.unshift(parent);
                getAncestors(parent);
            }
        }
        getAncestors(item);
        tb.options.updateFilesData(linkObject);
    },
    hScroll : 300,
    filterTemplate : function() {
        var tb = this;
        function resetFilter () {
            $osf.trackClick('myProjects', 'filter', 'clear-search');
            tb.filterText('');
            tb.resetFilter.call(tb);
            tb.updateFolder(allTopLevelProjectsCache(), tb.treeData);
            $('.db-poFilter>input').val('');
        }
        var filter = $osf.debounce(tb.filter, 800);
        return [ m('input.form-control[placeholder="Search all my projects"][type="text"]', {
            style: 'display:inline;',
            onkeyup: function(event){
                var newEvent = $.extend({}, event); // because currentTarget changes with debounce.
                if ($(this).val().length === 1){
                    tb.updateFolder(allProjectsCache(), tb.treeData);
                    tb.options.showSidebar(false);
                    tb.options.resetUi();
                }
                if($(this).val().length === 0){
                    resetFilter();
                }
                if($(this).val().length > 1){
                    filter(newEvent);
                }
            },
            onchange: function(event) {
                tb.filterText(event.value);
                $osf.trackClick('myProjects', 'filter', 'search-projects');
            },
            value: tb.filterText()
        }),
        m('.filterReset', { onclick : resetFilter }, tb.options.removeIcon())];
    },
    hiddenFilterRows : ['tags'],
    lazyLoadOnLoad : function (tree, event) {
        var tb = this;
        function formatItems (arr) {
            var item;
            for(var i = 0; i < arr.length; i++){
                item = arr[i];
                formatDataforPO(item.data);
                if(item.children.length > 0){
                    formatItems(item.children);
                }
            }
        }
        formatItems(tree.children);
    }
};

var ProjectOrganizer = {
    controller : function (args) {
        LinkObject = args.LinkObject;
        formatDataforPO = args.formatDataforPO;
        var self = this;
        self.updateTB = function(){
            var poOptions = $.extend(
                {
                    divID : 'projectOrganizer',
                    dragOptions : {
                        containment : '#dashboard'
                    },
                    updateSelected : args.updateSelected,
                    updateFilesData : args.updateFilesData,
                    filesData: args.filesData(),
                    dragContainment : args.wrapperSelector,
                    resetUi : args.resetUi,
                    showSidebar : args.howSidebar,
                    loadValue : args.loadValue,
                    mpTreeData : args.treeData,
                    mpBuildTree : args.buildTree,
                    mpUpdateFolder : args.updateFolder
                },
                tbOptions
            );
            if (args.resolveToggle){
                poOptions.resolveToggle = args.resolveToggle;
            }
            var tb = new Treebeard(poOptions, true);
            return tb;
        };
        allProjectsCache = args.allProjects;
        allTopLevelProjectsCache = args.allTopLevelProjects;
        self.tb = self.updateTB();
    },
    view : function (ctrl, args) {
        return m('.fb-project-organizer#projectOrganizer', ctrl.tb );
    }
};


module.exports = ProjectOrganizer;

