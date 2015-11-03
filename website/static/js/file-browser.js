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
    this.id = getUID();
    this.type = 'collection';
    this.label = label || 'New Collection';
    this.data = {
        path: path,
        pathQuery: pathQuery
    };
}
var Filter = function (label, data, type) {
    this.id = getUID();
    this.label = label;
    this.data = data;
    this.type = type;
};

if (!window.fileBrowserCounter) {
    window.fileBrowserCounter = 0;
}
function getUID() {
    window.fileBrowserCounter = window.fileBrowserCounter + 1;
    return window.fileBrowserCounter;
}

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
            new Collection('All My Projects', 'users/me/nodes/', { 'related_counts' : true }),
            new Collection('All My Registrations', 'registrations/', { 'related_counts' : true }),
            new Collection('Everything', 'users/me/nodes/', { 'related_counts' : true })
        ];
        self.breadcrumbs = m.prop([
            new Breadcrumb('All My Projects','http://localhost:8000/v2/users/me/nodes/?related_counts=true', 'collection')
        ]);
        self.nameFilters = [
            new Filter('Caner Uguz', '8q36f', 'name')
        ];
        self.tagFilters = [
            new Filter('Something Else', 'something', 'tag')
        ];
        self.filesData = m.prop($osf.apiV2Url(
            self.collections[0].data.path,
            { query : self.collections[0].data.pathQuery }
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
            selectedList.map(function(item){
                // get information

            });
            self.selected(selectedList);
        };

        // USER FILTER
        self.activeFilter = m.prop(1);
        self.updateFilter = function(filter) {
            self.activeFilter(filter.id);
            var linkObject = new LinkObject(filter.type, filter.data, filter.label);
            self.updateFilesData(linkObject);
        };


        // Refresh the Grid
        self.updateList = function(element){
            if(!self.isLoadedUrl) {
                var el = element || $(self.wrapperSelector).find('.fb-main').get(0);
                m.mount(el,
                    m.component( ProjectOrganizer, {
                        filesData : self.filesData,
                        updateSelected : self.updateSelected,
                        updateFilesData : self.updateFilesData,
                        wrapperSelector : self.wrapperSelector
                        }
                    )
                );
                self.isLoadedUrl = true;
            }
        }.bind(self);


        // BREADCRUMBS
        self.updateBreadcrumbs = function(linkObject){
            var crumb = new Breadcrumb(linkObject.label, linkObject.link, linkObject.type);
            if (linkObject.type === 'collection' || linkObject.type === 'name' || linkObject.type === 'tag'){
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
            else if (linkObject.type === 'name') {
                return $osf.apiV2Url('users/' + linkObject.data + '/nodes', { query : {'related_counts' : true}});
            }
            else if (linkObject.type === 'tag') {
                return $osf.apiV2Url('nodes/', { query : {'filter[tags]' : linkObject.data , 'related_counts' : true}});
            }
            else if (linkObject.type === 'node') {
                return $osf.apiV2Url('nodes/' + linkObject.data.uid + '/children', { query : { 'related_counts' : true }});
            }
            // If nothing
            throw new Error('Link could not be generated from linkObject data');
        };



    },
    view : function (ctrl) {
        var infoPanel = '';
        var poStyle = 'width : 80%';
        var infoClass = 'btn-default';
        if (ctrl.showInfo()){
            infoPanel = m('.fb-infobar', m.component(Information, { selected : ctrl.selected }));
            poStyle = 'width : 50%';
            infoClass = 'btn-primary';
        }
        return [
            m('.fb-header.m-b-xs', [
                m.component(Breadcrumbs, {
                    data : ctrl.breadcrumbs,
                    updateFilesData : ctrl.updateFilesData
                }),
                m('.fb-buttonRow', [
                    m('#poFilter.m-r-xs'),
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
                    activeFilter : ctrl.activeFilter,
                    updateFilter : ctrl.updateFilter
                }),
                m.component(Filters, {
                    activeFilter : ctrl.activeFilter,
                    updateFilter : ctrl.updateFilter,
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
        return m('.fb-collections', [
            m('ul', [
                m('h5', [m('i.fa.fa-cubes'), 'Collections']),
                args.list.map(function(item){
                    selectedCSS = item.id === args.activeFilter() ? 'active' : '';
                    return m('li', { className : selectedCSS},
                        m('a', { href : '#', onclick : args.updateFilter.bind(null, item) },  item.label)
                    );
                })
            ]),

        ]);
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
                    m('i.fa.fa-angle-right')
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
                m('h5', [m('i.fa.fa-user'), 'Contributors']),
                m('ul', [
                    args.nameFilters.map(function(item, index){
                        selectedCSS = item.id === args.activeFilter() ? '.active' : '';
                        return m('li' + selectedCSS,
                            m('a', { href : '#', onclick : args.updateFilter.bind(null, item)}, item.label)
                        );
                    })
                ]),
                m('h5', [m('i.fa.fa-tags'), 'Tags']),
                m('ul', [
                    args.tagFilters.map(function(item){
                        selectedCSS = item.id === args.activeFilter() ? '.active' : '';
                        return m('li' + selectedCSS,
                            m('a', { href : '#', onclick : args.updateFilter.bind(null, item)}, item.label)
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
            template = m('', [
                m('h4', m('a', { href : item.data.links.html}, item.data.attributes.title)),
                m('p', [
                    m('span', 'Description: '),
                    m('span', item.data.attributes.description)
                ]),
                m('p', [
                    m('span', 'Category: '),
                    m('span', item.data.attributes.category)
                ]),
                m('p', [
                    m('', 'Tags'),
                    item.data.attributes.tags.map(function(tag){
                        return m('span.tag', tag);
                    })
                ]),
                m('p', [
                    m('span', 'Last Modified: '),
                    m('span', item.data.attributes.date_modified)
                ]),
                m('p', [
                    m('span', 'Visibility: '),
                    m('span', item.data.attributes.public ? 'Public' : 'Private')
                ])
            ]);
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