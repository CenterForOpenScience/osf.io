/**
 * UI and function to quick search projects
 */

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');

// CSS
require('css/quick-project-search-plugin.css');

// XHR config for apiserver connection
var xhrconfig = function(xhr) {
    xhr.withCredentials = true;
};

var quickSearchProject = {
    controller: function() {
        var self = this;
        self.nodes = m.prop([]); // Pending nodes waiting to be displayed
        self.displayedNodes = m.prop([]); // Nodes that are rendered
        self.nonMatchingNodes = m.prop([]); //Nodes that don't match search query
        //self.lastLogin = '';
        // NEED TO FIGURE OUT WHAT TO DO ABOUT LASTLOGIN.
        self.lastLogin = '2016-01-01T15:20:11.531000';
        self.commentsCount = {};
        self.logsCount = {};
        self.sortState = m.prop();
        self.countState = m.prop();
        self.next = m.prop();
        self.allLoaded = m.prop(false);

        // Load first ten nodes
        var url = $osf.apiV2Url('users/me/nodes/', { query : { 'embed': 'contributors'}});
        var promise = m.request({method: 'GET', url : url, config : xhrconfig});
        promise.then(function(result) {
            result.data.forEach(function (node) {
                self.nodes().push(node);
            });
            self.next(result.links.next);
            self.countState(10);
            self.displayedNodes(self.nodes().splice(0, 10));
        });
        promise.then(
            function(){
                self.recursiveNodes(self.next())
            }
        );

        // Recursively calls remaining user's nodes
        self.recursiveNodes = function (url) {
             var nextPromise = m.request({method: 'GET', url : url, config : xhrconfig, background : true});
                nextPromise.then(function(result){
                    result.data.forEach(function(node){
                        self.nodes().push(node)
                    });
                    self.next(result.links.next);
                    console.log(self.next());
                    if (self.next()) {
                        self.recursiveNodes(self.next())
                    }
                    else {
                        self.allLoaded(true)
                    }
        })};

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

        self.loadUpToTen = function () {
            var requested = self.nodes().splice(0, 10);
            for (var i = 0; i < requested.length; i++) {
                self.displayedNodes().push(requested[i])
            }
            self.countState(self.displayedNodes().length);
            return self.displayedNodes()
        };

        self.removeUpToTen = function() {
            var remove = 0;
            if (self.countState() - 10 >= 10) {
                if (self.countState() % 10 === 0) {
                    remove = 10
                }
                else {
                    remove = self.countState() % 10
                }

            }
            else if (self.countState() - 10 >= 0) {
                remove = self.countState() - 10
            }
            else {
                return
            }
            var removedNodes = self.displayedNodes().splice(self.displayedNodes().length - remove);
            for (var i = 0; i < removedNodes.length; i++) {
                self.nodes().push(removedNodes[i])
            }
            self.sortBySortState();
            self.countState(self.displayedNodes().length);
            return self.displayedNodes()
        };

        self.getFamilyName = function(i, node) {
            return node.embeds.contributors.data[i].embeds.users.data.attributes.family_name
        };
        self.getContributors = function (node) {
            var numContributors = node.embeds.contributors.links.meta.total;
            if (numContributors === 1) {
                return self.getFamilyName(0, node)
            }
            else if (numContributors === 2) {
                return self.getFamilyName(0, node) + ' and ' +
                    self.getFamilyName(1, node)
            }
            else if (numContributors === 3) {
                return self.getFamilyName(0, node) + ', ' +
                    self.getFamilyName(1, node) + ', and ' +
                    self.getFamilyName(2, node)
            }
            else {
                return self.getFamilyName(0, node) + ', ' +
                    self.getFamilyName(1, node) + ', ' +
                    self.getFamilyName(2, node) + ' + ' + (numContributors - 3)
            }

        };

        self.getRecentComments = function (node) {
            var url = $osf.apiV2Url('nodes/' + node.id + '/comments/',
                { query : { 'filter[date_modified][gte]': self.lastLogin }}
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

        self.formatDate = function (node) {
            return new $osf.FormattableDate(node.attributes.date_modified).local
        };

        self.restoreToNodeList = function (missingNodes) {
            for (var i = 0; i < missingNodes.length ; i++) {
                self.nodes().push(missingNodes[i])
            }
        };

        self.sortAlphabeticalAscending = function () {
            self.nodes().sort(function(a,b){
                var A = a.attributes.title.toUpperCase();
                var B = b.attributes.title.toUpperCase();
                return (A < B) ? -1 : (A > B) ? 1 : 0;
            });
            self.sortState('alphaAsc');
        };

        self.sortAlphabeticalDescending = function () {
            self.nodes().sort(function(a,b){
                var A = a.attributes.title.toUpperCase();
                var B = b.attributes.title.toUpperCase();
                return (A > B) ? -1 : (A < B) ? 1 : 0;
            });
            self.sortState('alphaDesc');
        };

        self.sortDateAscending = function () {
            self.nodes().sort(function(a,b){
                var A = a.attributes.date_modified;
                var B = b.attributes.date_modified;
                return (A < B) ? -1 : (A > B) ? 1 : 0;
            });
            self.sortState('dateAsc')
        };

        self.sortDateDescending = function () {
            self.nodes().sort(function(a,b){
                var A = a.attributes.date_modified;
                var B = b.attributes.date_modified;
                return (A > B) ? -1 : (A < B) ? 1 : 0;
            });
            self.sortState('dateDesc');
        };

        self.sortBySortState = function () {
            if (self.sortState() === 'alphaAsc') {
                self.sortAlphabeticalAscending()
            }
            else if (self.sortState() === 'alphaDesc') {
                self.sortAlphabeticalDescending()
            }
            else if (self.sortState() === 'dateAsc') {
                self.sortDateAscending()
            }
            else {
                self.sortDateDescending()
            }
        };

        self.sortNodesAndModifyDisplay = function () {
            self.restoreToNodeList(self.displayedNodes());
            self.sortBySortState();
            self.displayedNodes(self.nodes().splice(0, self.countState()))
        };

        self.noTitleMatch = function (node, query) {
            return (node.attributes.title.toUpperCase().indexOf(query.toUpperCase()) === -1);
        };

        self.noContributorMatch = function (node, query) {
             var contributors =  node.embeds.contributors.data;
             for (var c = 0; c < contributors.length; c++ ) {
                 if (contributors[c].embeds.users.data.attributes.full_name.toUpperCase().indexOf(query.toUpperCase()) !== -1){
                     return false
                 }
             }
             return true
        };


        self.filterNodes = function (query){
            for (var n = self.nodes().length - 1; n >= 0; n--) {
                var node = self.nodes()[n];
                if (self.noTitleMatch(node, query) && self.noContributorMatch(node, query)) {
                    self.nonMatchingNodes().push(node);
                    self.nodes().splice(n, 1)
                }
            }
        };

        self.quickSearch = function () {
            var query = document.getElementById('searchQuery').value;
            self.restoreToNodeList(self.nonMatchingNodes());
            self.restoreToNodeList(self.displayedNodes());
            self.displayedNodes([]);
            self.nonMatchingNodes([]);
            // if backspace completely, previous nodes with prior sorting/count will be displayed
            if (query === '') {
                self.sortNodesAndModifyDisplay();
                return self.displayedNodes()
            }
            else {
                self.filterNodes(query);
                self.sortBySortState();
                var numDisplay = Math.min(self.nodes().length, self.countState());
                for (var i = 0; i < numDisplay; i++) {
                    self.displayedNodes().push(self.nodes()[i])

                }
                self.nodes().splice(0, numDisplay);
                return self.displayedNodes()
            }

        };
        //self.getLastLoginDate()

    },
    view : function(ctrl) {
        function projectView(project) {
            console.log('pending: ' + ctrl.nodes().length, ', displayed: ' + ctrl.displayedNodes().length, ', non-matching: ' + ctrl.nonMatchingNodes().length, ctrl.sortState());
            return m('tr', [
                m('td', m("a", {href: '/'+ project.id}, project.attributes.title)),
                m('td', ctrl.getContributors(project)),
                m('td', ctrl.formatDate(project)),
                m('td', ctrl.loadRecentCommentCount(project)),
                m('td', ctrl.loadRecentLogsCount(project))
            ])
        }

        function loadMoreButton() {
            if (ctrl.nodes().length !== 0){
                return m('button', { onclick: function() {
                    ctrl.loadUpToTen() }
                }, 'Show more')
            }
        }

         function loadLessButton() {
            if (ctrl.displayedNodes().length > 10){
                return m('button', { onclick: function() {
                    ctrl.removeUpToTen() }
                }, 'Show less')
            }
        }

        return m('div', [
            m('input[type=search]', {id: 'searchQuery', onkeyup: function() {ctrl.quickSearch()}}, 'Quick search projects'),
            m('div', {'class': 'container-fluid'},
                m('table', [
                    m('tr', [
                        m('th', {class: 'col-md-5'}, 'Name',
                            m('button', {class: 'glyphicon glyphicon-chevron-up', onclick: function() {
                                ctrl.sortState('alphaAsc');
                                ctrl.sortNodesAndModifyDisplay();
                            }}),
                            m('button', {class: 'glyphicon glyphicon-chevron-down', onclick: function() {
                                ctrl.sortState('alphaDesc');
                                ctrl.sortNodesAndModifyDisplay();
                            }})),
                        m('th', {class: 'col-md-3'}, 'Contributors'),
                        m('th', {class: 'col-md-2'}, 'Modified',
                            m('button', {class: 'glyphicon glyphicon-chevron-up', onclick: function() {
                                ctrl.sortState('dateAsc');
                                ctrl.sortNodesAndModifyDisplay()}}),
                            m('button', {class: 'glyphicon glyphicon-chevron-down', onclick: function() {
                                ctrl.sortState('dateDesc');
                                ctrl.sortNodesAndModifyDisplay();
                           }})
                        ),
                        m('th', {class: 'col-md-1'}, 'New comments'),
                        m('th', {class: 'col-md-1'}, 'New logs')
                    ]),

                    ctrl.displayedNodes().map(function(n){
                        return projectView(n)
                    }),
                    loadMoreButton(),
                    loadLessButton()
            ])
            )
        ])
    }
};

module.exports = quickSearchProject;

