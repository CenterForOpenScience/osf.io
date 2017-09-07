'use strict';

var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var $osf = require('js/osfHelpers');
var iconmap = require('js/iconmap');
var lodashFind = require('lodash.find');
var mHelpers = require('js/mithrilHelpers');
var Raven = require('raven-js');


var MAX_PAGES_ON_PAGINATOR = 7;
var MAX_PAGES_ON_PAGINATOR_SIDE = 5;

var ProfilePagination = function(ctrl, buildUrlFunction) {
    var i;
    ctrl.paginators([]);
    if (ctrl.totalPages() > 1) {
        // previous page
        ctrl.paginators().push({
            url: function() { return ctrl.prevPage(); },
            text: '<'
        });
        // first page
        ctrl.paginators().push({
            text: 1,
            url: function() {
                ctrl.pageToGet(1);
                if(ctrl.pageToGet() !== ctrl.currentPage()) {
                    return buildUrlFunction(ctrl.pageToGet(), ctrl.user, ctrl.nodeType);
                }
            }
        });
        // no ellipses
        if (ctrl.totalPages() <= MAX_PAGES_ON_PAGINATOR) {
            for (i = 2; i < ctrl.totalPages(); i++) {
                ctrl.paginators().push({
                    text: i,
                    url: function() {
                        ctrl.pageToGet(parseInt(this.text));
                        if (ctrl.pageToGet() !== ctrl.currentPage()) {
                            return buildUrlFunction(ctrl.pageToGet(), ctrl.user);
                        }
                    }
                });/* jshint ignore:line */
                // function defined inside loop
            }
        }
        // one ellipse at the end
        else if (ctrl.currentPage() < MAX_PAGES_ON_PAGINATOR_SIDE - 1) {
            for (i = 2; i < MAX_PAGES_ON_PAGINATOR_SIDE; i++) {
                ctrl.paginators().push({
                    text: i,
                    url: function() {
                        ctrl.pageToGet(parseInt(this.text));
                        if (ctrl.pageToGet() !== ctrl.currentPage()) {
                            return buildUrlFunction(ctrl.pageToGet(), ctrl.user);
                        }
                    }
                });/* jshint ignore:line */
                // function defined inside loop
            }
            ctrl.paginators().push({
                text: '...',
                url: function() { }
            });
        }
        // one ellipse at the beginning
        else if (ctrl.currentPage() > ctrl.totalPages() - MAX_PAGES_ON_PAGINATOR_SIDE + 2) {
            ctrl.paginators().push({
                text: '...',
                url: function() { }
            });
            for (i = ctrl.totalPages() - MAX_PAGES_ON_PAGINATOR_SIDE + 2; i <= ctrl.totalPages() - 1; i++) {
                ctrl.paginators().push({
                    text: i,
                    url: function() {
                        ctrl.pageToGet(parseInt(this.text));
                        if (ctrl.pageToGet() !== ctrl.currentPage()) {
                            return buildUrlFunction(ctrl.pageToGet(), ctrl.user, ctrl.nodeType);
                        }
                    }
                });/* jshint ignore:line */
                // function defined inside loop
            }
        }
        // two ellipses
        else {
            ctrl.paginators().push({
                text: '...',
                url: function() { }
            });
            for (i = parseInt(ctrl.currentPage()) - 1; i <= parseInt(ctrl.currentPage()) + 1; i++) {
                ctrl.paginators().push({
                    text: i,
                    url: function() {
                        ctrl.pageToGet(parseInt(this.text));
                        if (ctrl.pageToGet() !== ctrl.currentPage()) {
                            return buildUrlFunction(ctrl.pageToGet(), ctrl.user);
                        }
                    }
                });/* jshint ignore:line */
                // function defined inside loop
            }
            ctrl.paginators().push({
                text: '...',
                url: function() { }
            });
        }
        // last page
        ctrl.paginators().push({
            text: ctrl.totalPages(),
            url: function() {
                ctrl.pageToGet(ctrl.totalPages());
                if (ctrl.pageToGet() !== ctrl.currentPage()) {
                    return buildUrlFunction(ctrl.pageToGet(), ctrl.user);
                }
            }
        });
        // next page
        ctrl.paginators().push({
            url: function() { return ctrl.nextPage(); },
            text: '>'
        });
    }
};

module.exports = {
    ProfilePagination: ProfilePagination
};
