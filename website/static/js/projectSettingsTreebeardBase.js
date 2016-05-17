/**
 * Treebeard base for project settings
 * Currently used for wiki and notification settings
 */

'use strict';

var m = require('mithril');
var Fangorn = require('js/fangorn');


function resolveToggle(item) {
    var toggleMinus = m('i.fa.fa-minus', ' '),
        togglePlus = m('i.fa.fa-plus', ' ');

    if (item.children.length > 0) {
        if (item.open) {
            return toggleMinus;
        }
        return togglePlus;
    }
    item.open = true;
    return '';
}

/**
 * take treebeard tree structure of nodes and get a dictionary of parent node and all its
 * children
 */
function getNodesOriginal(nodeTree, nodesOriginal) {
    var i;
    var j;
    var adminContributors = [];
    var registeredContributors = [];
    var nodeId = nodeTree.node.id;
    for (i=0; i < nodeTree.node.contributors.length; i++) {
        if (nodeTree.node.contributors[i].is_admin) {
            adminContributors.push(nodeTree.node.contributors[i].id);
        }
        if (nodeTree.node.contributors[i].is_confirmed) {
            registeredContributors.push(nodeTree.node.contributors[i].id);
        }
    }
    var nodeInstitutions = [];
    for (i=0; i < nodeTree.node.affiliated_institutions.length; i++) {
            nodeInstitutions.push(nodeTree.node.affiliated_institutions[i].id);
    }

    nodesOriginal[nodeId] = {
        isPublic: nodeTree.node.is_public,
        id: nodeTree.node.id,
        title: nodeTree.node.title,
        contributors: nodeTree.node.contributors,
        isAdmin: nodeTree.node.is_admin,
        visibleContributors: nodeTree.node.visible_contributors,
        adminContributors: adminContributors,
        registeredContributors: registeredContributors,
        canWrite: nodeTree.node.can_write,
        institutions: nodeInstitutions,
        changed: false,
        checked: false,
        enabled: true
    };

    if (nodeTree.children) {
        for (j in nodeTree.children) {
            nodesOriginal = getNodesOriginal(nodeTree.children[j], nodesOriginal);
        }
    }
    return nodesOriginal;
}

module.exports = {
    defaults: {
        rowHeight : 33,         // user can override or get from .tb-row height
        resolveToggle: resolveToggle,
        paginate : false,       // Whether the applet starts with pagination or not.
        paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
        uploads : false,         // Turns dropzone on/off.
        resolveIcon : Fangorn.Utils.resolveIconView,
        hideColumnTitles: true,
        columnTitles : function columnTitles(item, col) {
            return [
                {
                    title: 'Project',
                    width: '60%',
                    sortType : 'text',
                    sort : false
                },
                {
                    title: 'Editing Toggle',
                    width : '40%',
                    sort : false

                }
            ];
        },
        ontogglefolder : function (item){
            var containerHeight = this.select('#tb-tbody').height();
            this.options.showTotal = Math.floor(containerHeight / this.options.rowHeight) + 1;
            this.redraw();
        },
        sortButtonSelector : {
            up : 'i.fa.fa-chevron-up',
            down : 'i.fa.fa-chevron-down'
        },
        showFilter : false,     // Gives the option to filter by showing the filter box.
        allowMove : false,       // Turn moving on or off.
        hoverClass : '',
        resolveRefreshIcon : function() {
          return m('i.fa.fa-refresh.fa-spin');
        }
    },
    getNodesOriginal: getNodesOriginal
};
