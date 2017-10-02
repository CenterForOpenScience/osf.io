'use strict';

var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var $osf = require('js/osfHelpers');
var iconmap = require('js/iconmap');
var lodashFind = require('lodash.find');
var mHelpers = require('js/mithrilHelpers');
var Raven = require('raven-js');

var MAX_PAGES_ON_PAGINATOR = 7;
var MAX_PAGES_ON_PAGINATOR_SIDE = 5;
var PROJECTS_PAGE_SIZE = 5;

var _buildUrl = function(page, user, nodeType) {
    var userFieldSet = ['family_name', 'full_name', 'given_name'];
    var nodeFieldSet = ['title', 'category', 'parent', 'public', 'contributors'];

    var query = {
        'page[size]': PROJECTS_PAGE_SIZE,
        'page': page || 1,
        'embed': ['contributors'],
        'filter[public]': 'true',
        'version': '2.2',
        'fields[nodes]': nodeFieldSet.join(','),
        'fields[users]': userFieldSet.join(',')
    };

    if (nodeType === 'projects') {
        query['filter[parent]'] = 'null';
    }
    else {
        query['filter[parent][ne]'] = 'null';
        query.embed.push('parent');
    }

    return $osf.apiV2Url('users/' + user +  '/nodes/', { query: query});
};

function _formatContributors(item) {

    var contributorList = item.embeds.contributors.data;
    var totalContributors = item.embeds.contributors.meta.total;
    var isContributor = lodashFind(contributorList, ['id', window.contextVars.currentUser.id]);

    if (!isContributor) {
        // only show bibliographic contributors
        contributorList = contributorList.filter(function (contrib) {
            return contrib.attributes.bibliographic;
        });
        totalContributors = item.embeds.contributors.meta.total_bibliographic;
    }

    return contributorList.map(function (person, index, arr) {
        var names = $osf.extractContributorNamesFromAPIData(person);
        var name;
        var familyName = names.familyName;
        var givenName = names.givenName;
        var fullName = names.fullName;

        if (familyName) {
            name = familyName;
        } else if(givenName){
            name = givenName;
        } else if(fullName){
            name = fullName;
        } else {
            name = 'A contributor';
        }
        var comma;
        if (index === 0) {
            comma = '';
        } else if (index === totalContributors - 1) {
            comma = ' & ';
        } else {
            comma = ', ';
        }
        if (index > 3) {
            return;
        }
        if (index === 3) {
            // We already show names of the two
            return m('span', {}, [
                ' & ',
                m('a', {'href': item.links.html}, (totalContributors - 3) + ' more')
            ]);
        }
        return m('span', {}, [
            comma,
            m('a', {'href': person.embeds.users.data.links.html}, name)
        ]);
    });
}

var PublicNode = {

    controller: function(options) {
        var self = this;
        self.node = options.node;
        self.nodeType = options.nodeType;

        self.icon =  iconmap.projectComponentIcons[self.node.attributes.category];
        self.parent = self.nodeType === 'components' && self.node.embeds.parent.data ? self.node.embeds.parent.data.attributes : null;
    },

    view: function(ctrl)  {
        return m('div', [
            m('li.project list-group-item list-group-item-node cite-container', [
                m('h4.list-group-item-heading', [
                    m('span.component-overflow.f-w-lg', {style: 'line-height: 1.5;'}, [
                        m('span.project-statuses-lg'),
                        m('span', {class: ctrl.icon, style: 'padding-right: 5px;'}, ''),
                        m('a', {'href': ctrl.node.links.html}, ctrl.node.attributes.title)
                    ])
                ]),
                ctrl.nodeType === 'components' ? m('div', {style: 'padding-bottom: 10px;'}, [
                    ctrl.parent ? ctrl.parent.title + ' / ': m('em', '-- private project -- / '),
                    m('b', ctrl.node.attributes.title)
                ]) : '',
                m('div.project-authors', {}, _formatContributors(ctrl.node)),
            ])
        ]);
    }
};

var PublicNodes = {

    controller: function(options) {
        var self = this;
        self.user = options.user._id;
        self.isProfile = options.user.is_profile;
        self.nodeType = options.nodeType;

        self.publicProjects = m.prop([]);
        self.requestPending = m.prop(false);

        self.failed = false;
        self.paginators = m.prop([]);
        self.nextPage = m.prop('');
        self.prevPage = m.prop('');
        self.totalPages = m.prop(0);
        self.currentPage = m.prop(0);
        self.pageToGet = m.prop(0);

        self.getProjects = function _getProjects (url) {

            if(self.requestPending()) {
                return;
            }

            self.publicProjects([]);
            self.requestPending(true);

            function _processResults (result){

                self.publicProjects(result.data);
                self.nextPage(result.links.next);
                self.prevPage(result.links.prev);

                var params = $osf.urlParams(url);
                var page = params.page || 1;

                self.currentPage(parseInt(page));
                self.totalPages(Math.ceil(result.meta.total / result.meta.per_page));

                m.redraw();
            }

            var promise = m.request({
                method : 'GET',
                url : url,
                background : true,
                config: mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain})
            });

            promise.then(
                function(result) {
                    self.requestPending(false);
                    _processResults(result);
                    return promise;
                }, function(xhr, textStatus, error) {
                    self.failed = true;
                    self.requestPending(false);
                    m.redraw();
                    Raven.captureMessage('Error retrieving projects', {extra: {url: url, textStatus: textStatus, error: error}});
                }
            );
        };

        self.getCurrentProjects = function _getCurrentProjects (page){
            if(!self.requestPending()) {
                var url = _buildUrl(page, self.user, self.nodeType);
                return self.getProjects(url);
            }
        };

        self.getCurrentProjects();
    },

    view : function (ctrl) {

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
                                return _buildUrl(ctrl.pageToGet(), ctrl.user, ctrl.nodeType);
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
                                return _buildUrl(ctrl.pageToGet(), ctrl.user, ctrl.nodeType);
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
                                return _buildUrl(ctrl.pageToGet(), ctrl.user, ctrl.nodeType);
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
                        return _buildUrl(ctrl.pageToGet(), ctrl.user, ctrl.nodeType);
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
                'Unable to retrieve public ' + ctrl.nodeType + ' at this time. Please refresh the page or contact ',
                m('a', {'href': 'mailto:support@osf.io'}, 'support@osf.io'),
                ' if the problem persists.'
            ]) :

            // Show laoding icon while there is a pending request
            ctrl.requestPending() ?  m('.ball-pulse.ball-scale-blue.text-center', [m(''), m(''), m('')]) :

            // Display each project
            [
                ctrl.publicProjects().length !== 0 ? ctrl.publicProjects().map(function(node) {
                    return m.component(PublicNode, {nodeType: ctrl.nodeType, node: node});
                }) : ctrl.isProfile ?
                    m('div.help-block', {}, [
                        'You have no public ' + ctrl.nodeType + '.',
                        m('p', {}, [
                            'Find out how to make your ' + ctrl.nodeType + ' ',
                            m('a', {'href': 'http://help.osf.io/m/gettingstarted/l/524048-control-your-privacy-settings', 'target': '_blank'}, 'public'),
                            '.'
                        ])
                    ])
                : m('div.help-block', {}, 'This user has no public ' + ctrl.nodeType + '.'),

                // Pagination
                m('.db-activity-nav.text-center', {style: 'margin-top: 5px; margin-bottom: -10px;'}, [
                    ctrl.paginators() ? ctrl.paginators().map(function(page) {
                        return page.url() ? m('.btn.btn-sm.btn-link', { onclick : function() {
                            ctrl.getProjects(page.url());
                        }}, page.text) : m('.btn.btn-sm.btn-link.disabled', {style: 'color: black'}, page.text);
                    }) : ''
                ])
            ]
        ]);

    }
};

module.exports = {
    PublicNodes: PublicNodes
};
