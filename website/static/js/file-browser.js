/**
 * Builds full page project browser
 */
'use strict';

var Treebeard = require('treebeard');   // Uses treebeard, installed as plugin
var $ = require('jquery');  // jQuery
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var ProjectOrganizer = require('js/project-organizer');
var $osf = require('js/osfHelpers');

var LinkObject = function (type, data, label, index) {
    this.type = type;
    this.data = data;
    this.label = label;
    this.index = index;  // For breadcrumbs to cut off when clicking parent level
};

var Breadcrumb = function (label, url, type) {
    this.label = label;
    this.url = url;
    this.type = 'breadcrumb' || type;
};

var Collection = function(label, path, pathQuery) {
    this.type = 'collection';
    this.label = label || 'New Collection';
    this.path = path;
    this.pathQuery = pathQuery;
};

var Filter = function (label, data, type) {
    this.label = label;
    this.data = data;
    this.type = 'name' || type;
};

/**
 * Initialize File Browser. Prepeares an option object within FileBrowser
 * @constructor
 */
var FileBrowser = {
    controller : function (options) {
        var self = this;
        self.isLoadedUrl = false;
        self.wrapperSelector = options.wrapperSelector;

        // VIEW STATES
        self.showInfo = m.prop(false);

        // DEFAULT DATA -- to be switched with server response
        self.collections = [
            new Collection('All My Projects', 'users/me/nodes/', { 'filter[registration]' : 'false'}),
            new Collection('All My Registrations', 'users/me/nodes/', { 'filter[registration]' : 'true'}),
            new Collection('Everything', 'users/me/nodes/', { 'filter[registration]' : 'false'}),
        ];
        self.breadcrumbs = m.prop([
            new Breadcrumb('All My Projects','http://localhost:8000/v2/users/me/nodes/?filter%5Bregistration%5D=false', 'collection')
        ]);
        self.nameFilters = [
            new Filter('Caner Uguz', '8q36f')
        ];
        self.tagFilters = [
            new Filter('Something Else', 'something-else', 'tag')
        ];
        self.filesData = m.prop($osf.apiV2Url(
            self.collections[0].path,
            { query : self.collections[0].pathQuery }
        ));

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
            var linkObject = new LinkObject( 'collection', coll, coll.label);
            self.updateFilesData(linkObject);
        };


        // USER FILTER
        self.activeUser = m.prop(1);
        self.updateUserFilter = function(user) {
            self.activeUser(user.id);
            var linkObject = new LinkObject('user', user, user.label);
            self.updateFilesData(linkObject);
        };

        // Refresh the Grid
        self.updateList = function(element, isInit, context){
            if(!self.isLoadedUrl) {
                var el = element || $(self.wrapperSelector).find('.fb-main').get(0);
                m.mount(el,
                    m.component( ProjectOrganizer, {
                        filesData : self.filesData,
                        updateSelected : self.updateSelected,
                        updateFilesData : self.updateFilesData}
                    )
                );
                self.isLoadedUrl = true;
            }
        }.bind(self);


        // BREADCRUMBS
        self.updateBreadcrumbs = function(linkObject){
            var crumb = new Breadcrumb(linkObject.label, linkObject.link, linkObject.type);
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
            else if (linkObject.type === 'breadcrumb') {
                return linkObject.data.url;
            }
            else if (linkObject.type === 'user') {
                return $osf.apiV2Url('users/' + linkObject.id + '/nodes', {});
            }
            else if (linkObject.type === 'node') {
                return $osf.apiV2Url('nodes/' + linkObject.data.uid + '/children', {});
            }
            // If nothing
            throw new Error('Link could not be generated from linkObject data');
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
                m.component(Breadcrumbs, {
                    data : ctrl.breadcrumbs,
                    updateFilesData : ctrl.updateFilesData
                }),
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
                m.component(Collections, {
                    list : ctrl.collections,
                    activeCollection : ctrl.activeCollection,
                    updateCollection : ctrl.updateCollection
                }),
                m.component(Filters, {
                    activeUser : ctrl.activeUser,
                    updateUser : ctrl.updateUserFilter,
                    nameFilters : ctrl.nameFilters,
                    tagFilters : ctrl.tagFilters
                })
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
    view : function (ctrl, args) {
        var selectedCSS;
        return m('.fb-collections', m('ul', [
            args.list.map(function(item, index, array){
                selectedCSS = item.id === args.activeCollection() ? '.active' : '';
                return m('li', { className : selectedCSS},
                    m('a', { href : '#', onclick : args.updateCollection.bind(null, item) },  item.label)
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
    view : function (ctrl, args) {
        return m('.fb-breadcrumbs', m('ul', [
            args.data().map(function(item, index, array){
                if(index === array.length-1){
                    return m('li',  item.label);
                }
                var linkObject = new LinkObject(item.type, item, item.label, index);
                return m('li',
                    m('a', { href : '#', onclick : args.updateFilesData.bind(null, linkObject)},  item.label),
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
                            m('a', { href : '#', onclick : args.updateUser.bind(null, item)}, item.label)
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