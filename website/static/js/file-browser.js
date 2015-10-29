/**
 * Builds full page project browser
 */
'use strict';

var Treebeard = require('treebeard');   // Uses treebeard, installed as plugin
var $ = require('jquery');  // jQuery
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var ProjectOrganizer = require('js/project-organizer');
var $osf = require('js/osfHelpers');

var LinkObject = function (type, data, label, id) {
    if (!type || !data || !label || !id) {
        console.error("File browser error: Link object expects type, data, label and id passed. One or more are missing:", {
            type : type,
            data : data,
            label : label,
            id : id
        });
    }
    this.type = type;
    this.data = data;
    this.label = label;
    this.id = id;
};

/**
 * Initialize File Browser. Prepeares an option object within FileBrowser
 * @constructor
 */
var FileBrowser = {
    controller : function (args) {
        var self = this;
        self.isLoadedUrl = false;
        self.wrapperSelector = args.wrapperSelector;

        // VIEW STATES
        self.showInfo = m.prop(false);

        // DEFAULT DATA -- to be switched with server response
        self.collections = [
            {
                id:1,
                type : 'collection',
                label : 'All My Projects',
                path : 'users/me/nodes/',
                pathQuery : { 'filter[registration]' : 'false'}
            },
            {
                id:2,
                type : 'collection',
                label : 'All My Registrations',
                path : 'users/me/nodes/',
                pathQuery : {  'filter[registration]' : 'true'} },
            {
                id:3,
                type : 'collection',
                label : 'Nodes',
                path : 'users/me/nodes/',
                pathQuery : {}
            }
        ];
        self.filesData = m.prop($osf.apiV2Url(
            self.collections[0].path,
            { query : self.collections[0].pathQuery }
        ));

        self.breadcrumbs = m.prop([
            {
                label : 'All My Projects',
                url : 'http://localhost:8000/v2/users/me/nodes/?filter%5Bregistration%5D=false',
                type : 'collection'}
        ]);
        self.nameFilters = [
            {
                label : 'Caner Uguz',
                id : '8q36f',
                type : 'filter'
            }
        ];
        self.tagFilters = [
            {
                tag : 'something',
                type : 'filter'
            }
        ];

        self.updateFilesData = function(linkObject) {
            linkObject.link = self.generateLinks(linkObject);
            if (linkObject.link !== self.filesData()) {
                self.filesData(linkObject.link);
                self.isLoadedUrl = false; // check if in fact changed
                self.updateBreadcrumbs(linkObject);
            }
        };

        // INFORMATION PANEL
        self.selected = m.prop([]);
        self.updateSelected = function(selectedList){
            self.selected(selectedList);
        };

        // COLLECTIONS PANEL
        self.activeCollection = m.prop(1);
        self.updateCollection = function(coll) {
            self.activeCollection(coll.id);
            var linkObject = new LinkObject('collection', coll, coll.label, coll.id);
            self.updateFilesData(linkObject);
        };


        // USER FILTER
        self.activeUser = m.prop(1);
        self.updateUserFilter = function(user) {
            self.activeUser(user.id);
            var linkObject = new LinkObject('user', user, user.label, user.id);
            self.updateFilesData(linkObject);
        };

        // Refresh the Grid
        self.updateList = function(element, isInit, context){
            if(!self.isLoadedUrl) {
                var el = element || $(self.wrapperSelector).find('.fb-main').get(0);
                m.mount(el, m.component( ProjectOrganizer, { filesData : self.filesData, updateSelected : self.updateSelected, updateFilesData : self.updateFilesData}));
                self.isLoadedUrl = true;
            }
        }.bind(self);

        // BREADCRUMBS
        self.updateBreadcrumbs = function(linkObject){
            var crumb = {
                label : linkObject.label,
                url : linkObject.link,
                id : linkObject.id
            };
            if (linkObject.type === 'collection' || linkObject.type === 'user'){
                self.breadcrumbs([crumb]);
                return;
            }
            if (linkObject.type === 'breadcrumb'){
                self.breadcrumbs().splice(linkObject.index+1, self.breadcrumbs().length-linkObject.index-1);
                return;
            }
            self.breadcrumbs().push(crumb);
        }.bind(self);

        self.generateLinks = function (linkObject) {
            if (linkObject.type === 'collection'){
                return $osf.apiV2Url(linkObject.data.path, {
                        query : linkObject.data.pathQuery
                    }
                );
            }
            if (linkObject.type === 'breadcrumb') {
                return linkObject.data.url;
            }
            if (linkObject.type === 'user') {
                return $osf.apiV2Url('users/' + linkObject.id + '/nodes', {});
            }
            return $osf.apiV2Url('nodes/' + linkObject.data.uid + '/children', {}); // If type === node
        };



    },
    view : function (ctrl) {
        var infoPanel = '';
        var poStyle = 'width : 75%';
        var infoClass = 'btn-default';
        if(ctrl.showInfo()){
            infoPanel = m('.fb-infobar', m.component(Information, { selected : ctrl.selected }));
            poStyle = 'width : 55%';
            infoClass = 'btn-primary';
        }

        return [
            m('.fb-header', [
                m.component(Breadcrumbs, { data : ctrl.breadcrumbs, updateFilesData : ctrl.updateFilesData}),
                m('.fb-buttonRow', [
                    m('button.btn', {
                        'class' : infoClass,
                        onclick : function () {
                            ctrl.showInfo(!ctrl.showInfo());
                        }
                    }, m('.fa.fa-info'))
                ])
            ]),
            m('.fb-sidebar', [
                m.component(Collections, {list : ctrl.collections, activeCollection : ctrl.activeCollection, updateCollection : ctrl.updateCollection } ),
                m.component(Filters, { activeUser : ctrl.activeUser, updateUser : ctrl.updateUserFilter, nameFilters : ctrl.nameFilters, tagFilters : ctrl.tagFilters })
            ]),
            m('.fb-main', { config: ctrl.updateList, style : poStyle },
                m('#poOrganizer', m('.spinner-loading-wrapper', m('.logo-spin.logo-md')))
            ),
            infoPanel
        ];
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
            args.updateFilesData(this);
        };
    },
    view : function (ctrl, args) {
        return m('.fb-breadcrumbs', m('ul', [
            args.data().map(function(item, index, array){
                if(index === array.length-1){
                    return m('li',  item.label);
                }
                var linkObject = {
                    type : 'breadcrumb',
                    data : item,
                    label : item.label,
                    id : null,
                    index : index
                };
                return m('li',
                    m('a', { href : '#', onclick : ctrl.updateFilesData.bind(linkObject)},  item.label),
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