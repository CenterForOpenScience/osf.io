/**
 * Builds full page project browser
 */
'use strict';

var Treebeard = require('treebeard');   // Uses treebeard, installed as plugin
var $ = require('jquery');  // jQuery
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var ProjectOrganizer = require('js/projectorganizer').ProjectOrganizer;
var $osf = require('js/osfHelpers');

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
        self.data = [];
        self.isLoadedUrl = false;
        self.collections = [
            { id:1, label : 'All My Projects', path : 'users/me/nodes/', pathOptions : {  query : { 'filter[registration]' : 'false'} } },
            { id:2, label : 'All My Registrations', path : 'users/me/nodes/', pathOptions : { query : {  'filter[registration]' : 'true'} } },
            { id:3, label : 'Nodes', path : 'users/me/nodes/', pathOptions : {}}
        ];
        self.filesData = m.prop($osf.apiV2Url(self.collections[0].path, self.collections[0].pathOptions));

        self.breadcrumbs = m.prop([
            { label : 'All My Projects', url : 'http://localhost:8000/v2/users/me/nodes/?filter%5Bregistration%5D=false'}
        ]);
        self.nameFilters = [
            { label : 'Caner Uguz', userID : '8q36f'}
        ];
        self.tagFilters = [
            { tag : 'something'}
        ];

        self.updateFilesData = function(value) {
            if (value !== self.filesData()) {
                self.filesData(value);
                self.isLoadedUrl = false; // check if in fact changed
                //self.updateList();
            }
        };

        // INFORMATION PANEL
        self.selected = m.prop([]);
        self.updateSelected = function(selectedList){
            self.selected(selectedList);
            console.log(self.selected());
        }.bind(self);


        // COLLECTIONS PANEL
        self.activeCollection = m.prop(1);
        self.updateCollection = function(coll) {
            self.activeCollection(coll.id);
            console.log(self.activeCollection());
            coll.url = $osf.apiV2Url(coll.path, coll.pathOptions);
            self.updateFilesData(coll.url);
        };


        // USER FILTER
        self.activeUser = m.prop(1);
        self.updateUserFilter = function(user) {
            self.activeUser(user.id);
            var url  = 'v2/users/' + user.userID;
            //self.updateList(url);
        };

        // Refresh the Grid
        self.updateList = function(element, isInit, context){
            if(!self.isLoadedUrl) {
                var el = element || document.getElementById('pOrganizer');
                m.mount(el, m.component( ProjectOrganizer, { filesData : self.filesData, updateSelected : self.updateSelected, updateBreadcrumbs : self.updateBreadcrumbs}));
                self.isLoadedUrl = true;
            }
        }.bind(self);

        // BREADCRUMBS
        self.updateBreadcrumbs = function(node){
            var link = self.generateLinks('node', node.uid);
            self.breadcrumbs().push({
                label : node.attributes.title,
                url : link,
                uid : node.id
            });
            self.updateFilesData(link);
        }.bind(self);

        self.loadBreadcrumbs = function(item){
            self.updateFilesData(item.url);
        };

        self.generateLinks = function (type, data) {
            if(type === 'node'){
                return $osf.apiV2Url('nodes/' + data + '/children', {});
            }
        };



    },
    view : function (ctrl) {
        return m('', [
            m.component(Breadcrumbs, { data : ctrl.breadcrumbs, loadBreadcrumbs : ctrl.loadBreadcrumbs} ),
            m('.fb-sidebar', [
                m.component(Collections, {list : ctrl.collections, activeCollection : ctrl.activeCollection, updateCollection : ctrl.updateCollection } ),
                m.component(Filters, { activeUser : ctrl.activeUser, updateUser : ctrl.updateUserFilter, nameFilters : ctrl.nameFilters, tagFilters : ctrl.tagFilters })
            ]),
            m('.fb-main', { config: ctrl.updateList }, m('#poOrganizer' )),
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
    controller : function (args) {
        var self = this;
        self.updateFilesData = function() {
            args.loadBreadcrumbs(this);
        };
    },
    view : function (ctrl, args) {
        return m('.fb-breadcrumbs', m('ul', [
            args.data().map(function(item, index, array){
                if(index === array.length-1){
                    return m('li',  item.label);
                }
                return m('li',
                    m('a', { href : '#', onclick : ctrl.updateFilesData.bind(item)},  item.label),
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
            template = m('h4', item.data.attributes.title);
        }
        if (args.selected().length > 1) {
            template = m('', [ 'There are multiple items: ', args.selected().map(function(item){
                    return m('p', item.data.attributes.title);
                })]);
        }
        return m('.fb-information', template);
    }
};



module.exports = FileBrowser;