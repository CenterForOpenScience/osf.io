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
        var root = {id:0, children: [], kind : 'folder' };

        // Generate tree list from flat data
        for (var i = 0; i < data.length; i++) {
            var n = data[i];
            if (n.attributes.registration) {
                continue;
            }
            var parentLink = n.relationships.parent.links.self.href;
            var node = {
                id : n.id,
                node : n,
                kind : 'node',
                hasChildren : false
            };
            if(!parentLink) {

                root.children.push(node);

            }
        }
        console.log(root);

        // For information panel
        self.selected = m.prop([]);
        self.updateSelected = function(selectedList){
            self.selected(selectedList);
            console.log(self.selected());
        }.bind(self);


        self.activeCollection = m.prop(1);
        self.updateCollection = function(coll) {
            self.activeCollection(coll.id);
            console.log(self.activeCollection());
            self.updateList(coll.url);
        };

        self.activeUser = m.prop(1);
        self.updateUserFilter = function(user) {
            self.activeUser(user.id);
            var url  = 'v2/users/' + user.userID;
            self.updateList(url);
        };

        self.updateList = function(url){
            self.filesData(url);
            console.log(self.filesData());
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
            { id:1, label : 'All My Projects', url : 'v2/users/me/nodes'},
            { id:2, label : 'All My Registrations', url : '#'},
            { id:3, label : 'Another Collection', url : '#'}
        ];

        self.nameFilters = [
            { label : 'Caner Uguz', userID : '8q36f'}
        ];

        self.tagFilters = [
            { tag : 'something'}
        ];

        self.filesData = m.prop(root.children);

    },
    view : function (ctrl) {
        return m('', [
            m.component(Breadcrumbs, { data : ctrl.breadcrumbs } ),
            m('.fb-sidebar', [
                m.component(Collections, {list : ctrl.collections, activeCollection : ctrl.activeCollection, updateCollection : ctrl.updateCollection } ),
                m.component(Filters, { activeUser : ctrl.activeUser, updateUser : ctrl.updateUserFilter, nameFilters : ctrl.nameFilters, tagFilters : ctrl.tagFilters })
            ]),
            m('.fb-main', m.component(ProjectOrganizer, { filesData : ctrl.filesData, updateSelected : ctrl.updateSelected, updateBreadcrumbs : ctrl.updateBreadcrumbs})),
            m('.fb-infobar', m.component(Information, { selected : ctrl.selected }))
        ]);
    }
};

/**
 * Collections Module.
 * @constructor
 */
var Collections  = {
    controller : function (args) {
        var self = this;
        self.updateCollection = function(){
           args.updateCollection(this);
        };
    },
    view : function (ctrl, args) {
        var selectedCSS;
        return m('.fb-collections', m('ul', [
            args.list.map(function(item, index, array){
                selectedCSS = item.id === args.activeCollection() ? '.active' : '';
                return m('li' + selectedCSS,
                    m('a', { href : '#', onclick : ctrl.updateCollection.bind(item) },  item.label)
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
    controller : function (args) {
        var self = this;
        self.updateUser = function(){
            args.updateUser(this);
        };
    },
    view : function (ctrl, args) {
        var selectedCSS;
        return m('.fb-filters.m-t-lg',
            [
                m('h4', 'Filters'),
                m('', 'Contributors'),
                m('ul', [
                    args.nameFilters.map(function(item){
                        selectedCSS = item.id === args.activeUser() ? '.active' : '';
                        return m('li' + selectedCSS,
                            m('a', { href : '#', onclick : ctrl.updateUser.bind(item)}, item.label)
                        );
                    })
                ])

            ]
        );
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
            template = m('h4', item.data.node.attributes.title);
        }
        if (args.selected().length > 1) {
            template = m('', [ 'There are multiple items: ', args.selected().map(function(item){
                    return m('p', item.data.node.attributes.title);
                })]);
        }
        return m('.fb-information', template);
    }
};



module.exports = FileBrowser;