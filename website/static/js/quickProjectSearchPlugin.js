/**
 * UI and function to quick search projects
 */

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');

// XHR config for apiserver connection
var xhrconfig = function(xhr) {
    xhr.withCredentials = true;
};

var quickSearchProject = {
    controller: function() {
        var self = this;
        self.nodes = [];
        self.displayedNodes = [];
        self.lastLogin = '';
        //self.lastLogin = '';
        self.commentsCount = {};
        self.logsCount = {};

        // Load node list
        var url = $osf.apiV2Url('users/me/nodes/', { query : { 'embed': 'contributors', 'page[size]': 100}});
        var promise = m.request({method: 'GET', url : url, config : xhrconfig});
        promise.then(function(result){
            result.data.forEach(function(node){
                self.nodes.push(node);
            });
            self.nodes.sort(function(a,b){
                var A = a.attributes.date_modified;
                var B = b.attributes.date_modified;
                return (A > B) ? -1 : (A < B) ? 1 : 0;
            });
            self.displayedNodes = self.nodes.splice(0, 10)
        });

        // Load last login
        self.getLastLoginDate = function () {
            var url = $osf.apiV2Url('users/me/', {});
            var promise = m.request({method: 'GET', url: url, config : xhrconfig});
            promise.then(function(result) {
                self.lastLogin = result.data.attributes.last_login
            }
            );
            return promise
        };

        self.getFamilyName = function(i, node) {
            return node.embeds.contributors.data[i].embeds.users.data.attributes.family_name
        };
        self.getContributors = function (node) {
            var numContributors = node.embeds.contributors.links.meta.total;
            if (numContributors === 1) {
                return self.getFamilyName(0, node)
            }
            else if (numContributors == 2) {
                return self.getFamilyName(0, node) + ' and ' +
                        self.getFamilyName(1, node)
            }
            else {
                return self.getFamilyName(0, node) + ', ' +
                        self.getFamilyName(1, node) + ', ' +
                        self.getFamilyName(2, node) + ' and' +
                    (numContributors - 3) + ' others'
            }

        };

        self.getRecentComments = function (node) {
            var url = $osf.apiV2Url('nodes/' + node.id + '/comments/',
                { query : { 'filter[date_modified][gte]': self.lastLogin}}
            );
            var promise = m.request({method: 'GET', url : url, config: xhrconfig});
            promise.then(function(result) {
                self.commentsCount[node.id] = result.links.meta.total
            });
            return promise
        };

        self.loadRecentCommentCount = function (node) {
            if (node.id in self.commentsCount) {
                return self.commentsCount[node.id]
            }
            else {
                self.getRecentComments(node);
                return self.commentsCount[node.id]
            }
        };

        self.getRecentLogs = function (node) {
            var url = $osf.apiV2Url('nodes/' + node.id + '/logs/', { query : {'filter[action][ne]': 'comment_added',
                'filter[date][gte]': self.lastLogin}});
            var promise = m.request({method: 'GET', url : url, config: xhrconfig});
            promise.then(function(result){
                self.logsCount[node.id] = result.links.meta.total
            });
            return promise
        };

        self.loadRecentLogsCount = function(node) {
            if (node.id in self.logsCount){
                return self.logsCount[node.id]
            }
            else {
                self.getRecentLogs(node);
                return self.logsCount[node.id]
          }
        };

        self.loadUpToTen = function () {
            requested = self.nodes.splice(0, 10);
            for (i = 0; i < requested.length; i++) {
                self.displayedNodes.push(requested[i])
            }
            return self.displayedNodes
        };

        self.formatDate = function (node) {
            return new $osf.FormattableDate(node.attributes.date_modified).local
        };

        self.restoreFullNodeList = function () {
            for (i = 0; i < self.displayedNodes.length ; i++) {
                self.nodes.push(self.displayedNodes[i])
            }
        };

        self.sortAlphabeticalAscending = function () {
            numDisplayed = self.displayedNodes.length;
            self.restoreFullNodeList();
            self.nodes.sort(function(a,b){
                var A = a.attributes.title.toUpperCase();
                var B = b.attributes.title.toUpperCase();
                return (A < B) ? -1 : (A > B) ? 1 : 0;
            });
            self.displayedNodes = self.nodes.splice(0, numDisplayed);
            return self.displayedNodes
        };

        self.sortAlphabeticalDescending = function () {
            numDisplayed = self.displayedNodes.length;
            self.restoreFullNodeList();
            self.nodes.sort(function(a,b){
                var A = a.attributes.title.toUpperCase();
                var B = b.attributes.title.toUpperCase();
                return (A > B) ? -1 : (A < B) ? 1 : 0;
            });
            self.displayedNodes = self.nodes.splice(0, numDisplayed);
            return self.displayedNodes

        };

        self.sortDateAscending = function () {
            numDisplayed = self.displayedNodes.length;
            self.restoreFullNodeList();
            self.nodes.sort(function(a,b){
                var A = a.attributes.date_modified;
                var B = b.attributes.date_modified;
                return (A > B) ? -1 : (A < B) ? 1 : 0;
            });
            self.displayedNodes = self.nodes.splice(0, numDisplayed);
            return self.displayedNodes
        };

        self.sortDateDescending = function () {
            numDisplayed = self.displayedNodes.length;
            self.restoreFullNodeList();
            self.nodes.sort(function(a,b){
                var A = a.attributes.date_modified;
                var B = b.attributes.date_modified;
                return (A < B) ? -1 : (A > B) ? 1 : 0;
            });
            self.displayedNodes = self.nodes.splice(0, numDisplayed);
            return self.displayedNodes
        };

        //self.getLastLoginDate()

    },
    view : function(ctrl) {
        function projectView(project) {
            return m('tr', [
                m('td', m("a", {href: '/'+ project.id}, project.attributes.title)),
                m('td', ctrl.getContributors(project)),
                m('td', ctrl.formatDate(project)),
                m('td', ctrl.loadRecentCommentCount(project)),
                m('td', ctrl.loadRecentLogsCount(project))
            ])
        }

        function loadMoreButton() {
            if (ctrl.nodes.length !== 0){
                return m('button', { onclick: function() {
                    ctrl.loadUpToTen() }
                }, 'Load more')
            }
        }

        return m('div', [
            m('input[type=search]', 'Quick search projects'),
            m('table', [
                m('tr', [
                    m('th', 'Name'),
                    m('th', 'Contributors'),
                    m('th', 'Modified'),
                    m('th', 'New comments'),
                    m('th', 'New logs')
                ]),
                m('tr', [
                   m('td',
                       m('button', { onclick: function() {
                           ctrl.sortAlphabeticalAscending()
                       }}, 'Sort alphabetical asc')),
                    m('td', ''),
                    m('td',  m('button', { onclick: function() {
                           ctrl.sortDateAscending()
                       }}, 'Sort date asc'))

                ]),
                m('tr', [
                   m('td',
                   m('button', { onclick: function() {
                       ctrl.sortAlphabeticalDescending()
                   }}, 'Sort alphabetical desc')),
                    m('td', ''),
                    m('td',  m('button', { onclick: function() {
                           ctrl.sortDateDescending()
                       }}, 'Sort date desc'))

                ]),

                ctrl.displayedNodes.map(function(n){
                    return projectView(n)
                }),
                loadMoreButton()

            ])
        ])
    }
};

module.exports = quickSearchProject;

