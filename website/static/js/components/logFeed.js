'use strict';

require('css/log-feed.css');
var $ = require('jquery');  // jQuery
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var oop = require('js/oop');
var $osf = require('js/osfHelpers');
var mHelpers = require('js/mithrilHelpers');
var Raven = require('raven-js');
var LogText = require('js/logTextParser');
var Paginator = require('js/paginator');

var MAX_PAGES_ON_PAGINATOR = 7;
var MAX_PAGES_ON_PAGINATOR_SIDE = 5;
var LOG_PAGE_SIZE_LIMITED = 3;
var LOG_PAGE_SIZE = 6;
var PROFILE_IMAGE_SIZE = 16;

var _buildLogUrl = function(node, page, limitLogs) {
    var logPage = page || 1;
    var urlPrefix = (node.isRegistration || node.is_registration) ? 'registrations' : 'nodes';
    var size = limitLogs ? LOG_PAGE_SIZE_LIMITED : LOG_PAGE_SIZE;
    var query = { 'page[size]': size, 'page': logPage, 'embed': ['original_node', 'user', 'linked_node', 'template_node'], 'profile_image_size': PROFILE_IMAGE_SIZE};
    if (node.link) {
        query.view_only = node.link;
    }
    return $osf.apiV2Url(urlPrefix + '/' + node.id + '/logs/', { query: query});
};

var LogFeed = {

    controller: function(options) {
        var self = this;
        self.node = options.node;
        self.activityLogs = m.prop();
        self.logRequestPending = m.prop();
        self.limitLogs = options.limitLogs;
        self.failed = false;
        self.paginators = m.prop([]);
        self.nextPage = m.prop();
        self.prevPage = m.prop();
        self.firstPage = 0;
        self.lastPage = 0;
        self.totalPages = 0;
        self.currentPage = m.prop();
        self.pageToGet = m.prop();

        self.getLogs = function _getLogs (url) {
            self.activityLogs([]); // Empty logs from other projects while load is happening;
            function _processResults (result){
                result.data.map(function(log){
                    log.attributes.formattableDate = new $osf.FormattableDate(log.attributes.date);
                });

                self.activityLogs(result.data);  // Set activity log data
                self.nextPage(result.links.next);
                self.prevPage(result.links.prev);
                self.firstPage = result.links.first;
                self.lastPage = result.links.last;

                var params = $osf.urlParams(url);
                var page = params.page || 1;
                self.currentPage(parseInt(page));
                self.totalPages = Math.ceil(result.links.meta.total / result.links.meta.per_page);
            }
            self.logRequestPending(true);
            var promise = m.request({method : 'GET', url : url, config: mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain})});
            promise.then(
                function(result) {
                    _processResults(result);
                    self.logRequestPending(false);
                    return promise;
                }, function(xhr, textStatus, error) {
                    self.failed = true;
                    var message = 'Error retrieving logs for ' + self.node.id;
                    Raven.captureMessage(message, {extra: {url: url, textStatus: textStatus, error: error}});
                }
            );
        };

        self.getCurrentLogs = function _getCurrentLogs (node, page){
            if(!self.logRequestPending()) {
                var url = _buildLogUrl(node, page, self.limitLogs);
                return self.getLogs(url);
            }
        };
        self.getCurrentLogs(self.node);
    },

    view : function (ctrl) {

        var i;
        ctrl.paginators([]);
        if (ctrl.totalPages > 1 && !ctrl.limitLogs) {
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
                        return _buildLogUrl(ctrl.node, ctrl.pageToGet());
                    }
                }
            });
            // no ellipses
            if (ctrl.totalPages <= MAX_PAGES_ON_PAGINATOR) {
                for (i = 2; i < ctrl.totalPages; i++) {
                    ctrl.paginators().push({
                        text: i,
                        url: function() {
                            ctrl.pageToGet(parseInt(this.text));
                            if (ctrl.pageToGet() !== ctrl.currentPage()) {
                                return _buildLogUrl(ctrl.node, ctrl.pageToGet());
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
                                return _buildLogUrl(ctrl.node, ctrl.pageToGet());
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
            else if (ctrl.currentPage() > ctrl.totalPages - MAX_PAGES_ON_PAGINATOR_SIDE) {
                ctrl.paginators().push({
                    text: '...',
                    url: function() { }
                });
                for (i = ctrl.totalPages - MAX_PAGES_ON_PAGINATOR_SIDE; i < ctrl.totalPages - 1; i++) {
                    ctrl.paginators().push({
                        text: i + 1,
                        url: function() {
                            ctrl.pageToGet(parseInt(this.text));
                            if (ctrl.pageToGet() !== ctrl.currentPage()) {
                                return _buildLogUrl(ctrl.node, ctrl.pageToGet());
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
                        text: i + 1,
                        url: function() {
                            ctrl.pageToGet(parseInt(this.text));
                            if (ctrl.pageToGet() !== ctrl.currentPage()) {
                                return _buildLogUrl(ctrl.node, ctrl.pageToGet());
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
                text: ctrl.totalPages,
                url: function() {
                    ctrl.pageToGet(ctrl.totalPages);
                    if (ctrl.pageToGet() !== ctrl.currentPage()) {
                        return _buildLogUrl(ctrl.node, ctrl.pageToGet());
                    }
                }
            });
            // next page
            ctrl.paginators().push({
                url: function() { return ctrl.nextPage(); },
                text: '>'
            });
        }

        return m('.db-activity-list.m-t-md', [
            // Error message if the log request fails
            ctrl.failed ? m('p', [
                'Unable to retrieve logs at this time. Please refresh the page or contact ',
                m('a', {'href': 'mailto:support@osf.io'}, 'support@osf.io'),
                ' if the problem persists.'
            ]) :
            // Show OSF spinner while there is a pending log request
            ctrl.logRequestPending() ?  m('.spinner-loading-wrapper', [
                m('.logo-spin.logo-lg'),
                m('p.m-t-sm.fg-load-message', 'Loading logs...')
            ]) :
            // Display each log item (text and user image)
            [ctrl.activityLogs() ? ctrl.activityLogs().map(function(item) {
                var image = m('i.fa.fa-desktop');
                if (ctrl.node.anonymous) { item.anonymous = true; }
                if (!item.anonymous && item.embeds.user && item.embeds.user.data) {
                    image = m('img', { src : item.embeds.user.data.links.profile_image});
                } else if (!item.anonymous && item.embeds.user && item.embeds.user.errors[0].meta){
                    image = m('img', { src : item.embeds.user.errors[0].meta.profile_image});
                }
                return m('.db-activity-item', [
                    m('', [m('.db-log-avatar.m-r-xs', image), m.component(LogText, item)]),
                    m('.text-right', m('span.text-muted.m-r-xs', item.attributes.formattableDate.local))
                ]);
            }) : '',
            // Log pagination
            m('.db-activity-nav.text-center', [
                ctrl.paginators() && !ctrl.limitLogs ? ctrl.paginators().map(function(page) {
                    return page.url() ? m('.btn.btn-sm.btn-link', { onclick : function() {
                        ctrl.getLogs(page.url());
                    }}, page.text) : m('.btn.btn-sm.btn-link.disabled', {style: 'color: black'}, page.text);
                }) : ''
            ])]
        ]);
    }
};

module.exports = {
    LogFeed: LogFeed
};
