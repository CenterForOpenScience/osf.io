/**
 * Builds full page project browser
 */
'use strict';

var Treebeard = require('treebeard');   // Uses treebeard, installed as plugin
var $ = require('jquery');  // jQuery
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var ProjectOrganizer = require('js/projectorganizer').ProjectOrganizer;


/**
 *  Options for fileBrowser
 */
var defaults = {
    wrapper : '#fileBrowser',  // Default ID for wrapping empty div, all contents will be filled in.
    tboptions : {},
    fullWidth : true
};

/**
 * Initialize File Browser. Prepeares an option object within FileBrowser
 * @constructor
 */
var FileBrowser = {
    controller : function (args) {
        var self = this;
        var data = args.data;
        // Reorganize data
        var root = {id:0, children: [], data : {} };
        var node_list = { 0 : root};

        // Generate tree list from flat data
        for (var i = 0; i < data.length; i++) {
            var n = data[i];
            var parentLink = n.relationships.parent.links.self.href;
            var node = {
                id : n.id,
                data : n
            };
            if(!node_list[n.id]){
                node_list[n.id] = { id: n.id, data : n, children : [] };
            } else {
                node_list[n.id].id = n.id;
                node_list[n.id].data = n;
            }
            if(parentLink && !n.attributes.registration) {
                var parentID = parentLink.split('/')[5];
                if(!node_list[parentID]){
                    node_list[parentID] = { children : [] };
                }
                node_list[parentID].children.push(node_list[n.id]);

            } else {
                node_list[0].children.push(node_list[n.id]);
            }
        }
        console.log(root, node_list);

        // For information panel
        self.selected = m.prop([]);
        self.updateSelected = function(selectedList){
            self.selected(selectedList);
            console.log(self.selected());
        }.bind(self);

        // For breadcrumbs
        self.breadcrumbs = [
            { label : 'First', href : '/first'},
            { label : 'Second', href : '/second'},
            { label : 'Third', href : '/third'}
        ];
        self.updateBreadcrumbs = function(){

        }.bind(self);

        self.collections = [
            { id:1, label : 'Dashboard', href : '#'},
            { id:2, label : 'All My Registrations', href : '#'},
            { id:3, label : 'All My Projects', href : '#'},
            { id:4, label : 'Another Collection', href : '#'}
        ];

        self.renderCollections = function _renderDo(){
            if (self.data().data){
                self.data().data.map(function(item){
                    console.log(item.category);
                });
            }
        };

        self.poOptions = {
            placement : 'dashboard',
            divID: 'projectOrganizer',
            filesData: root.children,
            multiselect : true
        };

    },
    view : function (ctrl) {
        return m('', [
            m.component(Breadcrumbs, { data : ctrl.breadcrumbs } ),
            m('.fb-sidebar', [
                m.component(Collections, {list : ctrl.collections, selected : 1 } ),
                m.component(Filters)
            ]),
            m('.fb-main', m.component(ProjectOrganizer, { options : ctrl.poOptions, updateSelected : ctrl.updateSelected, updateBreadcrumbs : ctrl.updateBreadcrumbs})),
            m('.fb-infobar', m.component(Information, { selected : ctrl.selected }))
        ]);
    }
};

/**
 * Collections Module.
 * @constructor
 */
var Collections  = {
    controller : function (data) {
        this.list = data.list|| [];
        this.selected = data.selected;
    },
    view : function (ctrl) {
        var selectedCSS;
        return m('.fb-collections', m('ul', [
            ctrl.list.map(function(item, index, array){
                selectedCSS = item.id === ctrl.selected ? '.active' : '';
                if (index === array.length-1){
                    return m('li' + selectedCSS,  item.label);
                }
                return m('li' + selectedCSS,
                    m('a', { href : item.href},  item.label)
                );
            })
        ]));
    }
};

/**
 * Breadcrumbs Module.
 * @constructor
 */
var Breadcrumbs = {
    controller : function (data) {
        this.data = data ? data.data : [];
    },
    view : function (ctrl) {
        return m('.fb-breadcrumbs', m('ul', [
            ctrl.data.map(function(item, index, array){
                if(index === array.length-1){
                    return m('li',  item.label);
                }
                return m('li',
                    m('a', { href : item.href},  item.label),
                    m('i.fa.fa-chevron-right')
                );
            })
        ]));
    }
};


/**
 * Filters Module.
 * @constructor
 */
var Filters = {
    view : function (ctrl) {
        return m('.fb-filters', 'Filters');
    }
};

/**
 * Information Module.
 * @constructor
 */
var Information = {
    view : function (ctrl, args) {
        var template = '';
        if (args.selected().length === 1) {
            var item = args.selected()[0];
            if (item.data.isDashboard) {
                template = m('h4', 'This is the dashboard!');
            } else {
                template = m('h4', item.data.name);
            }
        }
        if (args.selected().length > 1) {
            template = m('', [ 'There are multiple items: ', args.selected().map(function(item){
                    return m('p', item.data.name);
                })]);
        }
        return m('.fb-information', template);
    }
};



module.exports = FileBrowser;