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
        self.countDisplayed = m.prop();
        self.next = m.prop();
        self.loadingComplete = m.prop(false);
        self.contributorMapping = {};
        self.filter = m.prop();
        self.totalLoaded = m.prop();

        // Load first ten nodes
        var url = $osf.apiV2Url('users/me/nodes/', { query : { 'embed': 'contributors'}});
        var promise = m.request({method: 'GET', url : url, config : xhrconfig});
        promise.then(function(result) {
            self.countDisplayed(result.data.length);
            result.data.forEach(function (node) {
                self.nodes().push(node);
                self.retrieveContributors(node)
            });
            self.next(result.links.next);
            self.displayedNodes(self.nodes().splice(0, 10));
            self.totalLoaded(self.displayedNodes().length)
        });
        promise.then(
            function(){
                if (self.next()) {
                    self.recursiveNodes(self.next())
                }
                else {
                    self.loadingComplete(true);
                    m.redraw()
                }
            }
        );

        // Recursively fetches remaining user's nodes
        self.recursiveNodes = function (url) {
            if (self.nodes().length > 0) {
                m.redraw()
            }
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
                        self.loadingComplete(true);
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
            self.countDisplayed(self.displayedNodes().length);
            return self.displayedNodes()
        };

        self.removeUpToTen = function() {
            var remove = 0;
            if (self.countDisplayed() - 10 >= 10) {
                if (self.countDisplayed() % 10 === 0) {
                    remove = 10
                }
                else {
                    remove = self.countDisplayed() % 10
                }

            }
            else if (self.countDisplayed() - 10 >= 0) {
                remove = self.countDisplayed() - 10
            }
            else {
                return
            }
            var removedNodes = self.displayedNodes().splice(self.displayedNodes().length - remove);
            for (var i = 0; i < removedNodes.length; i++) {
                self.nodes().push(removedNodes[i])
            }
            self.sortBySortState();
            self.countDisplayed(self.displayedNodes().length);
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
            self.displayedNodes(self.nodes().splice(0, self.countDisplayed()))
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
                var numDisplay = Math.min(self.nodes().length, self.countDisplayed());
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
            return [m('div', {class: 'row node-outline'}, [
                m('div', {class: 'col-xs-4 m-v-xs'}, m("a", {href: '/'+ project.id}, project.attributes.title)),
                m('div', {class: 'col-xs-4 m-v-xs text-muted'}, ctrl.getContributors(project)),
                m('div', {class: 'col-xs-4 m-v-xs'}, ctrl.formatDate(project))
            ]),
            m('div', {class: 'row'}, m('div', {class: 'col-xs-12 m-v-xs'}))];
        }

        function loadMoreButton() {
            if (ctrl.nodes().length !== 0){
                return m('button', {class: 'col-xs-12 text-muted', onclick: function() {
                        ctrl.loadUpToTen()}
                },
                m('i', {class: 'fa fa-caret-down load-nodes'}))
            }
        }

        function loadLessButton() {
            if (ctrl.displayedNodes().length > 10 && ctrl.loadingComplete()){
                return m('button', {class: 'col-xs-12 text-muted', onclick: function() {
                        ctrl.removeUpToTen()}
                    },
                m('i', {class: 'fa fa-caret-up load-nodes'}))
            }
        }

        function sortAlphaAsc() {
            if (ctrl.loadingComplete()) {
                return m('button', {onclick: function() {
                    ctrl.sortState('alphaAsc');
                    ctrl.sortNodesAndModifyDisplay();
                }},
                    m('i', {class: 'fa fa-chevron-up'})
)
            }
        }

        function sortAlphaDesc(){
            if (ctrl.loadingComplete()){
                return m('button', {onclick: function() {
                    ctrl.sortState('alphaDesc');
                    ctrl.sortNodesAndModifyDisplay();
                }},
                m('i', {class: 'fa fa-chevron-down'}))
            }
        }

        function sortDateAsc(){
            if (ctrl.loadingComplete()){
                 return m('button', {onclick: function() {
                     ctrl.sortState('dateAsc');
                     ctrl.sortNodesAndModifyDisplay()}},
                 m('i', {class: 'fa fa-chevron-up'}))
            }
        }
        function sortDateDesc(){
            if (ctrl.loadingComplete()){
                return m('button', {onclick: function() {
                    ctrl.sortState('dateDesc');
                    ctrl.sortNodesAndModifyDisplay();
               }},
                m('i', {class: 'fa fa-chevron-down'}))
            }
        }

        function searchBar() {
            if (ctrl.loadingComplete()){
                return m('div', {class : 'input-group'}, [
                    m('span', {class: 'input-group-addon'}, m('i', {class: 'fa fa-search'})),
                    m('input[type=search]', {class: 'form-control', id: 'searchQuery', placeholder: 'Quick search projects', onkeyup: function() {ctrl.quickSearch()}})
                ])
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
            return m('div', {class: 'container'}, [
                m('div', {class: 'row'},
                    m('div', {class: 'col-xs-2'}),
                    m('div', {class: 'col-xs-8 text-center'}, [
                        searchBar(),
                        ctrl.loadingComplete() ? '' : m('.spinner-div', m('i.fa.fa-refresh.fa-spin'), ' Loading projects...')
                    ]),
                    m('div', {class: 'col-xs-2'})),
                m('div', {class: 'row'}, [
                    m('div', {class: 'col-xs-4 m-v-md'}, 'Name', sortAlphaAsc(), sortAlphaDesc()),
                    m('div', {class: 'col-xs-4 m-v-md'}, 'Contributors'),
                    m('div', {class: 'col-xs-4 m-v-md'}, 'Date Modified', sortDateAsc(), sortDateDesc())
                ]),
                displayNodes(),
                loadMoreButton(),
                loadLessButton()
            ]);
        }

        if (ctrl.displayedNodes().length == 0 && ctrl.filter() == null) {
            return m('div', {class: 'row'}, m('h2', 'You have no projects. Go here to create one.'))
        }
        else {
            return resultsFound()
        }
    }
};

module.exports = quickSearchProject;

