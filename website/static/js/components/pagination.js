'use strict';

var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var $osf = require('js/osfHelpers');
var iconmap = require('js/iconmap');
var lodashFind = require('lodash.find');
var mHelpers = require('js/mithrilHelpers');
var Raven = require('raven-js');

var MAX_PAGES_ON_PAGINATOR = 7;
var MAX_PAGES_ON_PAGINATOR_SIDE = 5;


var withPagination = function(options) {
    return function PaginationWrapper(component) {
        /**
         * Wrapper around another controller to add pagination functionality.
         * options should include a buildUrl function to control how to create a new
         * URL for pagination, and a getNextItems function to handle requests
         */
        return {
            controller: function (ctrlOptions) {
                var self = this;

                self.paginators = m.prop([]);
                self.nextPage = m.prop('');
                self.prevPage = m.prop('');
                self.totalPages = m.prop(0);
                self.currentPage = m.prop(0);
                self.pageToGet = m.prop(0);

                ctrlOptions.updatePagination = function (result, url) {
                    self.nextPage(result.links.next);
                    self.prevPage(result.links.prev);
                    var params = $osf.urlParams(url);
                    var page = params.page || 1;
                    self.currentPage(parseInt(page));
                    self.totalPages(Math.ceil(result.meta.total / result.meta.per_page));
                };

                self.updatePagination = ctrlOptions.updatePagination;
                self.getNextItems = options.getNextItems;
                self.buildUrl = options.buildUrl;
                self.user = ctrlOptions.user._id;
                self.nodeType = ctrlOptions.nodeType;
                self.innerCtrl = new component.controller(ctrlOptions);
            },
            view: function (ctrl) {
                var i;
                ctrl.paginators([]);
                if (ctrl.totalPages() > 1) {
                    // previous page
                    ctrl.paginators().push({
                        url: function () {
                            return ctrl.prevPage();
                        },
                        text: '<'
                    });
                    // first page
                    ctrl.paginators().push({
                        text: 1,
                        url: function () {
                            ctrl.pageToGet(1);
                            if (ctrl.pageToGet() !== ctrl.currentPage()) {
                                return ctrl.buildUrl(ctrl.pageToGet(), ctrl.user, ctrl.nodeType);
                            }
                        }
                    });
                    // no ellipses
                    if (ctrl.totalPages() <= MAX_PAGES_ON_PAGINATOR) {
                        for (i = 2; i < ctrl.totalPages(); i++) {
                            ctrl.paginators().push({
                                text: i,
                                url: function () {
                                    ctrl.pageToGet(parseInt(this.text));
                                    if (ctrl.pageToGet() !== ctrl.currentPage()) {
                                        return ctrl.buildUrl(ctrl.pageToGet(), ctrl.user, ctrl.nodeType);
                                    }
                                }
                            });
                            /* jshint ignore:line */
                            // function defined inside loop
                        }
                    }
                    // one ellipse at the end
                    else if (ctrl.currentPage() < MAX_PAGES_ON_PAGINATOR_SIDE - 1) {
                        for (i = 2; i < MAX_PAGES_ON_PAGINATOR_SIDE; i++) {
                            ctrl.paginators().push({
                                text: i,
                                url: function () {
                                    ctrl.pageToGet(parseInt(this.text));
                                    if (ctrl.pageToGet() !== ctrl.currentPage()) {
                                        return ctrl.buildUrl(ctrl.pageToGet(), ctrl.user, ctrl.nodeType);
                                    }
                                }
                            });
                            /* jshint ignore:line */
                            // function defined inside loop
                        }
                        ctrl.paginators().push({
                            text: '...',
                            url: function () {
                            }
                        });
                    }
                    // one ellipse at the beginning
                    else if (ctrl.currentPage() > ctrl.totalPages() - MAX_PAGES_ON_PAGINATOR_SIDE + 2) {
                        ctrl.paginators().push({
                            text: '...',
                            url: function () {
                            }
                        });
                        for (i = ctrl.totalPages() - MAX_PAGES_ON_PAGINATOR_SIDE + 2; i <= ctrl.totalPages() - 1; i++) {
                            ctrl.paginators().push({
                                text: i,
                                url: function () {
                                    ctrl.pageToGet(parseInt(this.text));
                                    if (ctrl.pageToGet() !== ctrl.currentPage()) {
                                        return ctrl.buildUrl(ctrl.pageToGet(), ctrl.user, ctrl.nodeType);
                                    }
                                }
                            });
                            /* jshint ignore:line */
                            // function defined inside loop
                        }
                    }
                    // two ellipses
                    else {
                        ctrl.paginators().push({
                            text: '...',
                            url: function () {
                            }
                        });
                        for (i = parseInt(ctrl.currentPage()) - 1; i <= parseInt(ctrl.currentPage()) + 1; i++) {
                            ctrl.paginators().push({
                                text: i,
                                url: function () {
                                    ctrl.pageToGet(parseInt(this.text));
                                    if (ctrl.pageToGet() !== ctrl.currentPage()) {
                                        return ctrl.buildUrl(ctrl.pageToGet(), ctrl.user, ctrl.nodeType);
                                    }
                                }
                            });
                            /* jshint ignore:line */
                            // function defined inside loop
                        }
                        ctrl.paginators().push({
                            text: '...',
                            url: function () {
                            }
                        });
                    }
                    // last page
                    ctrl.paginators().push({
                        text: ctrl.totalPages(),
                        url: function () {
                            ctrl.pageToGet(ctrl.totalPages());
                            if (ctrl.pageToGet() !== ctrl.currentPage()) {
                                return ctrl.buildUrl(ctrl.pageToGet(), ctrl.user, ctrl.nodeType);
                            }
                        }
                    });
                    // next page
                    ctrl.paginators().push({
                        url: function () {
                            return ctrl.nextPage();
                        },
                        text: '>'
                    });
                }

                return m('span', [
                    component.view.call(this, ctrl.innerCtrl),
                    m('.db-activity-nav.text-center', {style: 'margin-top: 5px; margin-bottom: -10px;'}, [
                        ctrl.paginators() ? ctrl.paginators().map(function (page) {
                            return page.url() ? m('.btn.btn-sm.btn-link', {
                                onclick: function () {
                                    ctrl.getNextItems(ctrl.innerCtrl, page.url(), ctrl.updatePagination);
                                }
                            }, page.text) : m('.btn.btn-sm.btn-link.disabled', {style: 'color: black'}, page.text);
                        }) : ''
                    ])
                ]);
            }
        };
    };
};

module.exports = {
    withPagination: withPagination
};
