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
        self.sortState = m.prop('dateDesc');
        self.countState = m.prop();
        self.next = m.prop();
        self.allLoaded = m.prop(false);
        self.contributorMapping = {};
        self.filter = m.prop();

        // Load first ten nodes
        var url = $osf.apiV2Url('users/me/nodes/', { query : { 'embed': 'contributors'}});
        var promise = m.request({method: 'GET', url : url, config : xhrconfig});
        promise.then(function(result) {
            result.data.forEach(function (node) {
                self.nodes().push(node);
                self.retrieveContributors(node)
            });
            self.next(result.links.next);
            self.countState(10);
            self.displayedNodes(self.nodes().splice(0, 10));
        });
        promise.then(
            function(){
                if (self.next()) {
                    self.recursiveNodes(self.next())
                }
                else {
                    self.allLoaded(true);
                    m.redraw()
                }
            }
        );

        // Recursively calls remaining user's nodes
        self.recursiveNodes = function (url) {
             var nextPromise = m.request({method: 'GET', url : url, config : xhrconfig, background : true});
                nextPromise.then(function(result){
                    result.data.forEach(function(node){
                        self.nodes().push(node);
                        self.retrieveContributors(node)
                    });
                    self.next(result.links.next);
                    console.log(self.next());
                    if (self.next()) {
                        self.recursiveNodes(self.next())
                    }
                    else {
                        self.allLoaded(true);
                        m.redraw()
                    }
        })};

        self.retrieveContributors = function(node) {
            if (node.embeds.contributors.links.meta.total > 10) {
                self.pullOverTenContributorNames(node)
            }
            else {
                var contributors = node.embeds.contributors;
                self.mapNodeToContributors(node, contributors)
                }
        };

        self.pullOverTenContributorNames = function (node) {
            var url = $osf.apiV2Url('nodes/' + node.id + '/contributors/', { query : { 'page[size]': 1000 }});
            var promise = m.request({method: 'GET', url : url, config: xhrconfig, background : true});
            promise.then(function(result){
                self.mapNodeToContributors(node, result)
            })
        };

        self.mapNodeToContributors = function (node, contributors){
            var contributorList = [];
            contributors.data.forEach(function(contrib){
                fullName = contrib.embeds.users.data.attributes.full_name;
                contributorList.push(fullName)

            });
            self.contributorMapping[node.id] = contributorList
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

        self.noTitleMatch = function (node) {
            return (node.attributes.title.toUpperCase().indexOf(self.filter().toUpperCase()) === -1);
        };

        self.noContributorMatch = function (node) {
            var contributors = self.contributorMapping[node.id];

            for (var c = 0; c < contributors.length; c++) {
                if (contributors[c].toUpperCase().indexOf(self.filter().toUpperCase()) !== -1){
                    return false
                }
            }
            return true
        };

        self.filterNodes = function (){
            for (var n = self.nodes().length - 1; n >= 0; n--) {
                var node = self.nodes()[n];
                if (self.noTitleMatch(node) && self.noContributorMatch(node)) {
                    self.nonMatchingNodes().push(node);
                    self.nodes().splice(n, 1)
                }
            }
        };

        self.quickSearch = function () {
            self.filter(document.getElementById('searchQuery').value);
            self.restoreToNodeList(self.nonMatchingNodes());
            self.restoreToNodeList(self.displayedNodes());
            self.displayedNodes([]);
            self.nonMatchingNodes([]);
            // if backspace completely, previous nodes with prior sorting/count will be displayed
            if (self.filter() === '') {
                self.sortNodesAndModifyDisplay();
                return self.displayedNodes()
            }
            else {
                self.filterNodes();
                self.sortBySortState();
                var numDisplay = Math.min(self.nodes().length, self.countState());
                for (var i = 0; i < numDisplay; i++) {
                    self.displayedNodes().push(self.nodes()[i])
                }
                self.nodes().splice(0, numDisplay);
                return self.displayedNodes()
            }

        };

    },
    view : function(ctrl) {
        function projectView(project) {
            console.log('pending: ' + ctrl.nodes().length, ', displayed: ' + ctrl.displayedNodes().length, ', non-matching: ' + ctrl.nonMatchingNodes().length, ctrl.sortState());
            return m('tr', [
                m('td', m("a", {href: '/'+ project.id}, project.attributes.title)),
                m('td', ctrl.getContributors(project)),
                m('td', ctrl.formatDate(project))
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

        function sortAlphaAsc() {
            if (ctrl.allLoaded()) {
                return m('button', {class: 'glyphicon glyphicon-chevron-up', onclick: function() {
                    ctrl.sortState('alphaAsc');
                    ctrl.sortNodesAndModifyDisplay();
                }})
            }

        }

        function sortAlphaDesc(){
            if (ctrl.allLoaded()){
                return m('button', {class: 'glyphicon glyphicon-chevron-down', onclick: function() {
                    ctrl.sortState('alphaDesc');
                    ctrl.sortNodesAndModifyDisplay();
                }})
            }
        }

        function sortDateAsc(){
            if (ctrl.allLoaded()){
                 return m('button', {class: 'glyphicon glyphicon-chevron-up', onclick: function() {
                     ctrl.sortState('dateAsc');
                     ctrl.sortNodesAndModifyDisplay()}})
            }
        }
        function sortDateDesc(){
            if (ctrl.allLoaded()){
                return m('button', {class: 'glyphicon glyphicon-chevron-down', onclick: function() {
                    ctrl.sortState('dateDesc');
                    ctrl.sortNodesAndModifyDisplay();
               }})
            }
        }

        function searchBar() {
            if (ctrl.allLoaded()){
                return  m('input[type=search]', {id: 'searchQuery', onkeyup: function() {ctrl.quickSearch()}}, 'Quick search projects')
            }
        }

        function displayNodes() {
            if (ctrl.displayedNodes().length == 0 && ctrl.filter() != null) {
                return 'No results found!'
            }
            else {
                return ctrl.displayedNodes().map(function(n){
                    return projectView(n)
                })
            }
        }

        function resultsFound(){
            return m('div', [
                searchBar(),
                m('div', {'class': 'container-fluid'},
                    m('table', [
                        m('tr', [
                            m('th', 'Name', sortAlphaAsc(), sortAlphaDesc()),
                            m('th', 'Contributors'),
                            m('th', 'Modified', sortDateAsc(), sortDateDesc())
                        ]),
                        displayNodes(),
                        loadMoreButton(),
                        loadLessButton()
                    ])
                )
            ])
        }

        if (ctrl.displayedNodes().length == 0 && ctrl.filter() == null) {
            return m('h2', 'No nodes found! Create some!')
        }
        else {
            return resultsFound()
        }
    }
};

module.exports = quickSearchProject;

