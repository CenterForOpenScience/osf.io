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

var Collection = function(label, path, pathQuery, systemCollection) {
    this.id = getUID();
    this.type = 'collection';
    this.label = label || 'New Collection';
    this.data = {
        path: path,
        pathQuery: pathQuery
    };
    this.systemCollection = systemCollection || false;
};
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
        self.showSidebar = m.prop(true);
        self.showCollectionMenu = m.prop(false); // Show hide ellipsis menu for collections
        self.collectionMenuObject = m.prop({item : {label:null}, x : 0, y : 0}); // Collection object to complete actions on menu

        // DEFAULT DATA -- to be switched with server response
        self.collections = [
            new Collection('All My Projects', 'users/me/nodes/', { 'related_counts' : true }, true),
            new Collection('All My Registrations', 'registrations/', { 'related_counts' : true }, true),
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
            self.showSidebar(false);
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

        self.sidebarInit = function (element, isInit) {
            if(!isInit){
                $('[data-toggle="tooltip"]').tooltip();
            }
        };

        self.updateCollectionMenu = function (item, event) {
            var x = event.x - 4;
            var y = event.y-205;
            if (event.view.innerWidth < 767){
                x = x-115;
                y = y-30;
            }
            console.log(event.view.innerWidth < 767);
            self.showCollectionMenu(true);
            self.collectionMenuObject({
                item : item,
                x : x,
                y : y
            });
        };

    },
    view : function (ctrl) {
        var mobile = window.innerWidth < 767; // true if mobile view
        var infoPanel = '';
        var poStyle = 'width : 75%';
        var infoButtonClass = 'btn-default';
        var sidebarButtonClass = 'btn-default';
        if (ctrl.showInfo()){
            infoPanel = m('.fb-infobar', m.component(Information, { selected : ctrl.selected }));
            infoButtonClass = 'btn-primary';
            poStyle = 'width : 45%';
        }
        if(ctrl.showSidebar()){
            sidebarButtonClass = 'btn-primary';
        }
        if (mobile) {
            poStyle = 'width : 100%';
        } else {
            ctrl.showSidebar(true);
        }
        return [
            m('.fb-header.m-b-xs.row', [
                m('.col-xs-12.col-sm-6', m.component(Breadcrumbs, {
                    data : ctrl.breadcrumbs,
                    updateFilesData : ctrl.updateFilesData
                })),
                m('.fb-buttonRow.col-xs-12.col-sm-6', [
                    mobile ? m('button.btn.btn-sm.m-r-sm', {
                        'class' : sidebarButtonClass,
                        onclick : function () {
                            ctrl.showSidebar(!ctrl.showSidebar());
                        }
                    }, m('.fa.fa-bars')) : '',
                    m('#poFilter.m-r-xs'),
                    !mobile ? m('button.btn', {
                        'class' : infoButtonClass,
                        onclick : function () {
                            ctrl.showInfo(!ctrl.showInfo());
                        }
                    }, m('.fa.fa-info')) : ''
                ])
            ]),
            ctrl.showSidebar() ?
            m('.fb-sidebar', { config : ctrl.sidebarInit}, [
                mobile ? m('.fb-dismiss', m('button.close[aria-label="Close"]', {
                    onclick : function () {
                        ctrl.showSidebar(false);
                    }
                }, [
                    m('span[aria-hidden="true"]','×'),
                ])) : '',
                m.component(Collections, {
                    list : ctrl.collections,
                    activeFilter : ctrl.activeFilter,
                    updateFilter : ctrl.updateFilter,
                    showCollectionMenu : ctrl.showCollectionMenu,
                    updateCollectionMenu : ctrl.updateCollectionMenu,
                    collectionMenuObject : ctrl.collectionMenuObject
                }),
                m.component(Filters, {
                    activeFilter : ctrl.activeFilter,
                    updateFilter : ctrl.updateFilter,
                    nameFilters : ctrl.nameFilters,
                    tagFilters : ctrl.tagFilters
                })
            ]) : '',
            m('.fb-main', { config: ctrl.updateList, style : poStyle },
                m('#poOrganizer', m('.spinner-loading-wrapper', m('.logo-spin.logo-md')))
            ),
            infoPanel,
            m.component(Modals, { collectionMenuObject : ctrl.collectionMenuObject, selected : ctrl.selected}),
            mobile && ctrl.showSidebar() ? m('.fb-overlay') : ''
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
            m('h5', [
                'Collections ',
                m('i.fa.fa-question-circle.text-muted', {
                    'data-toggle':  'tooltip',
                    'title':  'Collections are groups of projects. You can create new collections and add any project you are a collaborator on or a public project.',
                    'data-placement' : 'bottom'
                }, ''),
                m('.pull-right', m('button.btn.btn-xs.btn-success[data-toggle="modal"][data-target="#addColl"]', m('i.fa.fa-plus')))
            ]),
            m('ul', [
                args.list.map(function(item){
                    selectedCSS = item.id === args.activeFilter() ? 'active' : '';
                    return m('li', { className : selectedCSS},
                        [
                            m('a', { href : '#', onclick : args.updateFilter.bind(null, item) },  item.label),
                            !item.systemCollection ? m('', {
                                onclick : function (e) {
                                    args.updateCollectionMenu(item, e);
                                }
                            }, m('i.fa.fa-ellipsis-v.pull-right.text-muted')) : ''
                        ]
                    );
                }),
                args.showCollectionMenu() ? m('.collectionMenu',{
                    style : 'top: ' + args.collectionMenuObject().y + 'px;left: ' + args.collectionMenuObject().x + 'px;'
                }, [
                    m('ul', [
                        m('li[data-toggle="modal"][data-target="#renameColl"]',{
                            onclick : function (e) {
                                args.showCollectionMenu(false);
                            }
                        }, [
                            m('i.fa.fa-pencil'),
                            ' Rename'
                        ]),
                        m('li[data-toggle="modal"][data-target="#removeColl"]',{
                            onclick : function (e) {
                                args.showCollectionMenu(false);
                            }
                        }, [
                            m('i.fa.fa-trash'),
                            ' Delete'
                        ])
                    ])
                ]) : ''
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
        var mobile = window.innerWidth < 767; // true if mobile view
        var items = args.data();
        if (mobile && items.length > 1) {
            return m('.fb-breadcrumbs', [
                m('ul', [
                    m('li', [
                        m('.btn.btn-link[data-toggle="modal"][data-target="#parentsModal"]', '...'),
                        m('i.fa.fa-angle-right')
                    ]),
                    m('li', items[items.length-1].label)
                ]),
                m('#parentsModal.modal.fade[tabindex=-1][role="dialog"][aria-hidden="true"]',
                    m('.modal-dialog',
                        m('.modal-content', [
                            m('.modal-body', [
                                m('button.close[data-dismiss="modal"][aria-label="Close"]', [
                                    m('span[aria-hidden="true"]','×'),
                                ]),
                                m('h4', 'Parent Projects'),
                                args.data().map(function(item, index, array){
                                    if(index === array.length-1){
                                        return m('.fb-parent-row.btn', {
                                            style : 'margin-left:' + (index*20) + 'px;',
                                        },  [
                                            m('i.fa.fa-angle-right.m-r-xs'),
                                            item.label
                                        ]);
                                    }
                                    var linkObject = new LinkObject(item.type, item, item.label, index);
                                    return m('.fb-parent-row',
                                        m('span.btn.btn-link', {
                                            style : 'margin-left:' + (index*20) + 'px;',
                                            onclick : function() {
                                                args.updateFilesData(linkObject);
                                                $('.modal').modal('hide');
                                            }
                                        },  [
                                            m('i.fa.fa-angle-right.m-r-xs'),
                                            item.label
                                        ])
                                    );
                                })
                            ]),
                        ])
                    )
                )
            ]);
        }
        return m('.fb-breadcrumbs', m('ul', [
            args.data().map(function(item, index, array){
                if(index === array.length-1){
                    return m('li',  item.label);
                }
                var linkObject = new LinkObject(item.type, item, item.label, index);
                return m('li',
                    m('span.btn.btn-link', { onclick : args.updateFilesData.bind(null, linkObject)},  item.label),
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
                m('h5', 'Contributors'),
                m('ul', [
                    args.nameFilters.map(function(item, index){
                        selectedCSS = item.id === args.activeFilter() ? '.active' : '';
                        return m('li' + selectedCSS,
                            m('a', { href : '#', onclick : args.updateFilter.bind(null, item)}, item.label)
                        );
                    })
                ]),
                m('h5', 'Tags'),
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
                m('p.fb-info-meta.text-muted', [
                    m('span', item.data.attributes.public ? 'Public' : 'Private' + ' ' + item.data.attributes.category),
                    m('span', ', Last Modified on ' + item.data.date.local)

                ]),
                m('p', [
                    m('span', item.data.attributes.description)
                ]),
                m('p', [
                    m('h5', 'Tags'),
                    item.data.attributes.tags.map(function(tag){
                        return m('span.tag', tag);
                    })
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

/**
 * Modals views.
 * @constructor
 */

var Modals = {
    view : function(ctrl, args) {
        return m('.fb-Modals', [
            m('#addColl.modal.fade[tabindex=-1][role="dialog"][aria-labelledby="addCollLabel"][aria-hidden="true"]',
                m('.modal-dialog',
                    m('.modal-content', [
                        m('.modal-header', [
                            m('button.close[data-dismiss="modal"][aria-label="Close"]', [
                                m('span[aria-hidden="true"]','×'),
                            ]),
                            m('h3.modal-title#addCollLabel', 'Add New Collection')
                        ]),
                        m('.modal-body', [
                            m('p', 'Collections are groups of projects that help you organize your work. [Learn more] about how to use Collections to organize your workflow. '),
                            m('.form-inline', [
                                m('.form-group', [
                                    m('label[for="addCollInput]', 'Collection Name'),
                                    m('input[type="text"].form-control#addCollInput')
                                ])
                            ]),
                            m('p', 'After you create your collection drag and drop projects to the collection. ')
                        ]),
                        m('.modal-footer', [
                            m('button[type="button"].btn.btn-default[data-dismiss="modal"]', 'Close'),
                            m('button[type="button"].btn.btn-success', 'Add')
                        ])
                    ])
                )
            ),
            m('#renameColl.modal.fade[tabindex=-1][role="dialog"][aria-labelledby="renameCollLabel"][aria-hidden="true"]',
                m('.modal-dialog',
                    m('.modal-content', [
                        m('.modal-header', [
                            m('button.close[data-dismiss="modal"][aria-label="Close"]', [
                                m('span[aria-hidden="true"]','×'),
                            ]),
                            m('h3.modal-title#renameCollLabel', 'Rename Collection')
                        ]),
                        m('.modal-body', [
                            m('p', 'Collections are groups of projects that help you organize your work. [Learn more] about how to use Collections to organize your workflow. '),
                            m('.form-inline', [
                                m('.form-group', [
                                    m('label[for="addCollInput]', 'Collection Name'),
                                    m('input[type="text"].form-control#addCollInput', { value : args.collectionMenuObject().item.label})
                                ])
                            ]),
                        ]),
                        m('.modal-footer', [
                            m('button[type="button"].btn.btn-default[data-dismiss="modal"]', 'Close'),
                            m('button[type="button"].btn.btn-success', 'Rename')
                        ])
                    ])
                )
            ),
            m('#removeColl.modal.fade[tabindex=-1][role="dialog"][aria-labelledby="removeCollLabel"][aria-hidden="true"]',
                m('.modal-dialog',
                    m('.modal-content', [
                        m('.modal-header alert-danger', [
                            m('button.close[data-dismiss="modal"][aria-label="Close"]', [
                                m('span[aria-hidden="true"]','×'),
                            ]),
                            m('h3.modal-title#removeCollLabel', 'Delete Collection ' + args.collectionMenuObject().item.label)
                        ]),
                        m('.modal-body', [
                            m('p', 'You sure?'),

                        ]),
                        m('.modal-footer', [
                            m('button[type="button"].btn.btn-default[data-dismiss="modal"]', 'Close'),
                            m('button[type="button"].btn.btn-danger', 'Delete')
                        ])
                    ])
                )
            ),
            m('#infoModal.modal.fade[tabindex=-1][role="dialog"][aria-hidden="true"]',
                m('.modal-dialog',
                    m('.modal-content', [
                        m('.modal-body', [
                            m('button.close[data-dismiss="modal"][aria-label="Close"]', [
                                m('span[aria-hidden="true"]','×'),
                            ]),
                            m.component(Information, { selected : args.selected })
                        ]),
                    ])
                )
            )
        ]);
    }
};

module.exports = FileBrowser;