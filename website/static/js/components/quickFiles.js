'use strict';

var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var $osf = require('js/osfHelpers');
var iconmap = require('js/iconmap');
var lodashFind = require('lodash.find');
var mHelpers = require('js/mithrilHelpers');
var Raven = require('raven-js');

var MAX_PAGES_ON_PAGINATOR = 7;
var MAX_PAGES_ON_PAGINATOR_SIDE = 5;
var QUICKFILES_PAGE_SIZE = 10;

var _buildUrl = function(page, user) {

    var query = {
        'page[size]': QUICKFILES_PAGE_SIZE,
        'page': page || 1,
        'version': '2.2',
    };

    return $osf.apiV2Url('users/' + user +  '/quickfiles/', { query: query});
};


var QuickFile = {

    controller: function(options) {
        var self = this;
        self.file = options.file;
        self.icon =  iconmap.file;
    },

    view: function(ctrl)  {
        var viewBase = window.location.origin + '/quickfiles';
        var viewUrl = ctrl.file.attributes.guid ? viewBase + '/' + ctrl.file.attributes.guid : viewBase + ctrl.file.attributes.path;
        return m('div', [
            m('li.project list-group-item list-group-item-node cite-container', [
                m('h4.list-group-item-heading', [
                    m('span.component-overflow.f-w-lg', {style: 'line-height: 1.5; width: 100%'}, [
                        m('span.project-statuses-lg', {style: 'width: 50%; float:left'}, [
                            m('span', {class: ctrl.icon, style: 'padding-right: 5px;'}, ''),
                            m('a', {'href': viewUrl}, ctrl.file.attributes.name),
                        ]),
                        m('div', {style: 'width: 50%; float:right; font-size:small; line-height:2;'}, 'downloads: ' + ctrl.file.attributes.extra.downloads)
                    ])
                ])
            ])
        ]);
    }
};

var QuickFiles = {

    controller: function (options) {
        var self = this;
        self.user = options.user._id;
        self.isProfile = options.user.is_profile;

        self.quickFiles = m.prop([]);
        self.requestPending = m.prop(false);

        self.failed = false;
        self.paginators = m.prop([]);
        self.nextPage = m.prop('');
        self.prevPage = m.prop('');
        self.totalPages = m.prop(0);
        self.currentPage = m.prop(0);
        self.pageToGet = m.prop(0);

        self.getQuickFiles = function _getQuickFiles(url) {
            if (self.requestPending()) {
                return;
            }
            self.quickFiles([]);
            self.requestPending(true);

            function _processResults(result) {

                self.quickFiles(result.data);
                self.nextPage(result.links.next);
                self.prevPage(result.links.prev);

                var params = $osf.urlParams(url);
                var page = params.page || 1;

                self.currentPage(parseInt(page));
                self.totalPages(Math.ceil(result.meta.total / result.meta.per_page));

                m.redraw();
            }

            var promise = m.request({
                method: 'GET',
                url: url,
                background: true,
                config: mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain})
            });

            promise.then(
                function (result) {
                    self.requestPending(false);
                    _processResults(result);
                    return promise;
                }, function (xhr, textStatus, error) {
                    self.failed = true;
                    self.requestPending(false);
                    m.redraw();
                    Raven.captureMessage('Error retrieving quickfiles', {
                        extra: {
                            url: url,
                            textStatus: textStatus,
                            error: error
                        }
                    });
                }
            );
        };

        self.getCurrentQuickFiles = function _getCurrentQuickFiles(page) {
            if (!self.requestPending()) {
                var url = _buildUrl(page, self.user);
                return self.getQuickFiles(url);
            }
        };
        self.getCurrentQuickFiles();
    },

    view: function (ctrl) {
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
                        return _buildUrl(ctrl.pageToGet(), ctrl.user, ctrl.nodeType);
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
                                return _buildUrl(ctrl.pageToGet(), ctrl.user);
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
                                return _buildUrl(ctrl.pageToGet(), ctrl.user);
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
                                return _buildUrl(ctrl.pageToGet(), ctrl.user, ctrl.nodeType);
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
                                return _buildUrl(ctrl.pageToGet(), ctrl.user);
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
                        return _buildUrl(ctrl.pageToGet(), ctrl.user);
                    }
                }
            });
            // next page
            ctrl.paginators().push({
                url: function() { return ctrl.nextPage(); },
                text: '>'
            });
        }

        return m('ul.list-group m-md', [
            // Error message if the request fails
            ctrl.failed ? m('p', [
                'Unable to retrieve quickfiles at this time. Please refresh the page or contact ',
                m('a', {'href': 'mailto:support@osf.io'}, 'support@osf.io'),
                ' if the problem persists.'
            ]) :

            // Show laoding icon while there is a pending request
            ctrl.requestPending() ?  m('.ball-pulse.ball-scale-blue.text-center', [m(''), m(''), m('')]) :

            // Display each quickfile
            [
                ctrl.quickFiles().length !== 0 ? ctrl.quickFiles().map(function(file) {
                    return m.component(QuickFile, {file: file});
                }) : ctrl.isProfile ?
                    m('div.help-block', {}, 'You have no public quickfiles')
                : m('div.help-block', {}, 'This user has no public quickfiles.'),

                // Pagination
                m('.db-activity-nav.text-center', {style: 'margin-top: 5px; margin-bottom: -10px;'}, [
                    ctrl.paginators() ? ctrl.paginators().map(function(page) {
                        return page.url() ? m('.btn.btn-sm.btn-link', { onclick : function() {
                            ctrl.getQuickFiles(page.url());
                        }}, page.text) : m('.btn.btn-sm.btn-link.disabled', {style: 'color: black'}, page.text);
                    }) : ''
                ])
            ]
        ]);
    }
};

module.exports = {
    QuickFiles: QuickFiles
};
