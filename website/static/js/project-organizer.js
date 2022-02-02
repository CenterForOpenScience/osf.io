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
var lodashGet = require('lodash.get');
var lodashFind = require('lodash.find');
var iconmap = require('js/iconmap');

var LinkObject;
var NodeFetcher;
var formatDataforPO;
var MOBILE_WIDTH = 767;

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
    var title = $osf.decodeText(node.attributes.title);
    var css = ''; // Keep for future expandability -- Remove: item.data.isSmartFolder ? 'project-smart-folder smart-folder' : '';
    var isMypreprintsCollection = tb.options.currentView().collection.data.nodeType === 'preprints';
    if (item.data.archiving) { // TODO check if this variable will be available
        return m('span', {'class': 'registration-archiving'}, title + ' [Archiving]');
    } else if (node.type === 'preprints' && isMypreprintsCollection){
        return [ m('a.fg-file-links', { 'class' : css, href : node.links.html, 'data-nodeID' : node.id, 'data-nodeTitle': title,'data-nodeType': node.type, onclick : function(event) {
            preventSelect.call(this, event);
            $osf.trackClick('myProjects', 'projectOrganizer', 'navigate-to-preprint');
        }}, title) ];
    } else if(node.links.html){
        return [ m('a.fg-file-links', { 'class' : css, href : node.links.html, 'data-nodeID' : node.id, 'data-nodeTitle': title, 'data-nodeType': node.type, onclick : function(event) {
            preventSelect.call(this, event);
            $osf.trackClick('myProjects', 'projectOrganizer', 'navigate-to-specific-project');
        }}, title) ];
    } else {
        return m('span', { 'class' : css, 'data-nodeID' : node.id, 'data-nodeTitle': title, 'data-nodeType': node.type}, title);
    }
}


/**
 * Contributors have first person's name and then number of contributors. This function returns the proper html
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @returns {Object} A Mithril virtual DOM template object
 * @private
 */

function _poContributors(item) {
    var contributorList = lodashGet(item, 'data.embeds.contributors.data', []);

    if (contributorList.length === 0) {
        return '';
    }
    var totalContributors = lodashGet(item, 'data.embeds.contributors.meta.total');
    var isContributor = lodashFind(contributorList, ['id', window.contextVars.currentUser.id]);

    if (!isContributor) {
        // bibliographic contributors
        contributorList = contributorList.filter(function (contrib) {
            return contrib.attributes.bibliographic;
        });
        totalContributors = item.data.embeds.contributors.meta.total_bibliographic;
    }

    return contributorList.map(function (person, index, arr) {
        var names = $osf.extractContributorNamesFromAPIData(person);
        var name;
        var familyName = names.familyName;
        var givenName = names.givenName;
        var fullName = names.fullName;

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
            return m('span', ' + ' + (totalContributors - 2)); // We already show names of the two
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
    var mobile = window.innerWidth < MOBILE_WIDTH; // true if mobile view
    var tb = this;
    var defaultColumns = [];
    if(this.isMultiselected(item.id)){
        item.css = 'fangorn-selected';
    } else {
        item.css = '';
    }

    defaultColumns.push({
        data : 'name',  // Data field name
        folderIcons : true,
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
            data : 'sortDate',
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
    var mobile = window.innerWidth < MOBILE_WIDTH; // true if mobile view
    if(!mobile){
        columns.push({
            title: 'Name',
            width : '55%',
            sort : true,
            sortType : 'text'
        },{
            title : 'Contributors',
            width : '25%',
            sort : false
        }, {
            title : 'Modified',
            width : '20%',
            sort : true,
            sortType : 'date'
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
        if (event.currentTarget != null && event.target.className.indexOf('po-draggable') !== -1) {
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
    ondataload : function () {
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
        tb.options.mpMultiselected(tb.multiselected);
        tb.options.mpHighlightMultiselect(tb.highlightMultiselect);
        tb.options._onload(tb);
    },
    ontogglefolder : function (item, event) {
        var tb = this;
        $osf.trackClick('myProjects', 'projectOrganizer', 'expand-collapse-project-children');
        $('[data-toggle="tooltip"]').tooltip();
    },
    onscrollcomplete : function () {
        $('[data-toggle="tooltip"]').tooltip();
    },
    onmultiselect : _poMultiselect,
    resolveIcon : function _poIconView(item) { // Project Organizer doesn't use icons
        var iconType = item.data.type === 'preprints' ? 'preprint' : item.data.attributes.category;
        return m('i.' + iconmap.projectComponentIcons[iconType]);
    },
    resolveToggle : _poResolveToggle,
    resolveLazyloadUrl : function(item) {
    if (item.open || item.data.relationships.children.links.related.meta.count === item.children.length)
        return null;
      var tb = this;
      var deferred = $.Deferred();
      var key = this.options.currentView().collection.id;

      this.options.fetchers[key].getChildren(item.data.id)
        .then(function(children) {
          item.children = [];
          // HACK to use promises with TB
          var child, i;
          for (i = 0; i < children.length; i++) {
            child = tb.buildTree(children[i], item);
            item.add(child);
          }
          item.open = true;
          tb.flatten(tb.treeData.children, tb.visibleTop);
          item.open = false;
          return deferred.resolve(null);
        });
      return deferred;
    },
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
        function getAncestors (item) {
            var parent = item.parent();
            if(parent && parent.id > tb.treeData.id) {
                linkObject.ancestors.unshift(parent);
                getAncestors(parent);
            }
        }
        var node = item.data;
        var linkObject = new LinkObject('node', node, node.attributes.title);
        if (item.data.type !== 'preprints') {
            tb.options.fetchers[linkObject.id] = new NodeFetcher(item.data.types, item.data.relationships.children.links.related.href + '?related_counts=children&embed=contributors');
            tb.options.fetchers[linkObject.id].on(['page', 'done'], tb.options.onPageLoad);

            // Get ancestors
            linkObject.ancestors = [];
            getAncestors(item);
            tb.options.updateFilesData(linkObject);
        }
    },
    hScroll : 'auto',
    filterTemplate : function() {
        var tb = this;
        var mobile = window.innerWidth < MOBILE_WIDTH; // true if mobile view
        function resetFilter () {
            $osf.trackClick('myProjects', 'filter', 'clear-search');
            tb.filterText('');
            tb.resetFilter.call(tb);
            $('.db-poFilter>input').val('');
        }
        return [ m('input.form-control[placeholder="Filter loaded resources"][type="text"]', {
            style: 'display:inline;',
            onkeyup: function(event) {
                tb.options.showSidebar(false);
                if ($(this).val().length === 0) {
                    resetFilter();
                } else {
                    tb.filterText(event.target.value);
                    tb.filter(event);
                }
            },
            onchange: function(event) {
                tb.filterText(event.target.value);
                $osf.trackClick('myProjects', 'filter', 'search-projects');
            },
            value: tb.filterText()
        }),
        m('.filterReset', { onclick : resetFilter }, tb.options.removeIcon())];
    },
    hiddenFilterRows : ['tags', 'contributors'],
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
        NodeFetcher  = args.NodeFetcher;
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
                    filesData: args.filesData,
                    dragContainment : args.wrapperSelector,
                    resetUi : args.resetUi,
                    showSidebar : args.showSidebar,
                    loadValue : args.loadValue,
                    mpTreeData : args.treeData,
                    mpBuildTree : args.buildTree,
                    mpUpdateFolder : args.updateFolder,
                    currentView: args.currentView,
                    onPageLoad : args.onPageLoad,
                    fetchers : args.fetchers,
                    _onload: args._onload,
                    mpMultiselected : args.multiselected,
                    mpHighlightMultiselect : args.highlightMultiselect
                },
                tbOptions
            );
            if (args.resolveToggle){
                poOptions.resolveToggle = args.resolveToggle;
            }
            var tb = new Treebeard(poOptions, true);
            return tb;
        };
        self.tb = self.updateTB();
    },
    view : function (ctrl, args) {
        return m('.fb-project-organizer#projectOrganizer', ctrl.tb );
    }
};


module.exports = ProjectOrganizer;
