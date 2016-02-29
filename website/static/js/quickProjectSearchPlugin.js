/**
 * UI and function to quick search projects
 */

var m = require('mithril');
var $osf = require('js/osfHelpers');

// CSS
require('css/quick-project-search-plugin.css');

// XHR config for apiserver connection
var xhrconfig = function(xhr) {
    xhr.withCredentials = true;
};


var QuickSearchProject = {
    controller: function() {
        var self = this;
        self.nodes = m.prop([]); // Master node list
        self.eligibleNodes = m.prop([]); // Array of indices corresponding to self.nodes() that are eligible to be loaded
        self.sortState = m.prop('dateDesc'); //How nodes are sorted - default is date descending - dateDesc
        self.countDisplayed = m.prop(); // Max number of nodes that can be rendered.  'Load more' increases this by up to ten.
        self.next = m.prop(); // URL for getting the next ten user nodes. When null, all nodes are loaded.
        self.loadingComplete = m.prop(false); // True when all user nodes are loaded.
        self.contributorMapping = {}; // Maps node id to list of contributors for searching
        self.filter = m.prop(); // Search query from user
        self.fieldSort = m.prop(); // For xs screen, either alpha or date
        self.directionSort = m.prop(); // For xs screen, either Asc or Desc

        // Load up to first ten nodes
        var url = $osf.apiV2Url('users/me/nodes/', { query : { 'embed': 'contributors'}});
        var promise = m.request({method: 'GET', url : url, config : xhrconfig});
        promise.then(function(result) {
            self.countDisplayed(result.data.length);
            result.data.forEach(function (node) {
                self.nodes().push(node);
                self.retrieveContributors(node);
            });
            self.populateEligibleNodes(0, self.countDisplayed());
            self.next(result.links.next);
        });
        promise.then(
            function(){
                if (self.next()) {
                    self.recursiveNodes(self.next());
                }
                else {
                    self.loadingComplete(true);
                }
            }
        );

        // Recursively fetches remaining user's nodes
        self.recursiveNodes = function (url) {
            if (self.next()) {
                var nextPromise = m.request({method: 'GET', url : url, config : xhrconfig, background : true});
                nextPromise.then(function(result){
                    result.data.forEach(function(node){
                        self.nodes().push(node);
                        self.retrieveContributors(node);
                    });
                self.populateEligibleNodes(self.eligibleNodes().length, self.nodes().length);
                self.next(result.links.next);
                self.recursiveNodes(self.next());
                });
            }
            else {
                self.loadingComplete(true);
                m.redraw();
            }
        };

        // Adds eligible node indices to array - used when no filter
        self.populateEligibleNodes = function (first, last) {
            for (var n = first; n < last; n++) {
                self.eligibleNodes().push(n);
            }
        };

        // Returns true if there are nodes in the background that are not rendered on screen
        self.pendingNodes = function () {
            return (self.countDisplayed() < self.eligibleNodes().length);
        };


        // When 'load more' button pressed, loads up to 10 nodes
        self.loadUpToTen = function () {
            if (self.eligibleNodes().length - self.countDisplayed() >= 10) {
                self.countDisplayed(self.countDisplayed() + 10);
            }
            else {
                self.countDisplayed(self.eligibleNodes().length);
            }
        };

        // If < 10 contribs, map node id to contrib names. Otherwise, make a call to get all contribs.
        self.retrieveContributors = function(node) {
            if (node.embeds.contributors.links.meta.total > 10) {
                self.pullOverTenContributorNames(node);
            }
            else {
                var contributors = node.embeds.contributors;
                self.mapNodeToContributors(node, contributors);
            }
        };

        // Call to get up to 1000 contributors on a node.
        self.pullOverTenContributorNames = function (node) {
            var url = $osf.apiV2Url('nodes/' + node.id + '/contributors/', { query : { 'page[size]': 1000 }});
            var promise = m.request({method: 'GET', url : url, config: xhrconfig, background : true});
            promise.then(function(result){
                self.mapNodeToContributors(node, result);
            });
        };

        // Maps node id to list of contrib names for later searching
        self.mapNodeToContributors = function (node, contributors){
            var contributorList = [];
            contributors.data.forEach(function(contrib){
                fullName = contrib.embeds.users.data.attributes.full_name;
                contributorList.push(fullName);
            });
            self.contributorMapping[node.id] = contributorList;
        };

        // Gets contrib family name for display
        self.getFamilyName = function(i, node) {
            return node.embeds.contributors.data[i].embeds.users.data.attributes.family_name;
        };

        // Formats contrib family names for display
        self.getContributors = function (node, number) {
            if (number === 1) {
                return self.getFamilyName(0, node);
            }
            else if (number === 2) {
                return self.getFamilyName(0, node) + ' and ' +
                    self.getFamilyName(1, node);
            }
            else if (number === 3) {
                return self.getFamilyName(0, node) + ', ' +
                    self.getFamilyName(1, node) + ', and ' +
                    self.getFamilyName(2, node);
            }
            else {
                return self.getFamilyName(0, node) + ', ' +
                    self.getFamilyName(1, node) + ', ' +
                    self.getFamilyName(2, node) + ' + ' + (number - 3);
            }

        };

         // Formats date for display
        self.formatDate = function (node) {
            return new $osf.FormattableDate(node.attributes.date_modified).local;
        };

        // Shortcut for sorting ascending
        self.sortAscending = function (A, B) {
            return (A < B) ? -1 : (A > B) ? 1 : 0;
        };

        // Shortcut for sorting descending
        self.sortDescending = function (A, B) {
            return (A > B) ? -1 : (A < B) ? 1 : 0;
        };

        self.sortAlphabeticalAscending = function () {
            self.nodes().sort(function(a,b){
                var A = a.attributes.title.toUpperCase();
                var B = b.attributes.title.toUpperCase();
                return self.sortAscending(A, B);
            });
            self.sortState('alphaAsc');
        };

        self.sortAlphabeticalDescending = function () {
            self.nodes().sort(function(a,b){
                var A = a.attributes.title.toUpperCase();
                var B = b.attributes.title.toUpperCase();
                return self.sortDescending(A, B);
            });
            self.sortState('alphaDesc');
        };

        self.sortDateAscending = function () {
            self.nodes().sort(function(a,b){
                var A = a.attributes.date_modified;
                var B = b.attributes.date_modified;
                return self.sortAscending(A, B);
            });
            self.sortState('dateAsc');
        };

        self.sortDateDescending = function () {
            self.nodes().sort(function(a,b){
                var A = a.attributes.date_modified;
                var B = b.attributes.date_modified;
                return self.sortDescending(A, B);
            });
            self.sortState('dateDesc');
        };

        // Sorts nodes depending on current sort state.
        self.sortBySortState = function () {
            switch (self.sortState()) {
                case 'alphaAsc':
                    self.sortAlphabeticalAscending();
                    break;
                case 'alphaDesc':
                    self.sortAlphabeticalDescending();
                    break;
                case 'dateAsc':
                    self.sortDateAscending();
                    break;
                default:
                    self.sortDateDescending();
            }
            if (self.filter()) {
                self.quickSearch();
            }
        };

        // For xs screen
        self.sortFieldGivenDirection = function(){
            var directionSort = self.preSelectDirection();
            self.sortState(self.fieldSort() + directionSort);
            self.sortBySortState();
        };

        // For xs screen
        self.sortDirectionGivenField = function() {
            var fieldSort = self.preSelectField();
            self.sortState(fieldSort + self.directionSort());
            self.sortBySortState();
        };

        // When shifting to xs screen, tells which field to automatically display in select
        self.preSelectField = function(){
            return self.sortState().split(/[A-Z][a-z]+/g)[0];
        };

        // When shifting to xs screen, tells which direction to automatically highlight in select
        self.preSelectDirection = function(){
            return self.sortState().match(/[A-Z][a-z]+/g)[0];
        };

        // Colors sort asc/desc buttons either selected or not-selected
        self.colorSortButtons = function (sort) {
            return self.sortState() === sort ? 'selected' : 'not-selected';
        };

        // Colors asc/desc buttons on XS screen
        self.colorSortButtonsXS = function (sort) {
            return self.preSelectDirection() === sort ? 'selected' : 'not-selected';
        };

        // Filtering on title
        self.titleMatch = function (node) {
            return (node.attributes.title.toUpperCase().indexOf(self.filter().toUpperCase()) !== -1);
        };

        // Filtering on contrib
        self.contributorMatch = function (node) {
            var contributors = self.contributorMapping[node.id];
            for (var c = 0; c < contributors.length; c++) {
                if (contributors[c].toUpperCase().indexOf(self.filter().toUpperCase()) !== -1){
                    return true;
                }
            }
            return false;
        };

        // Filtering on tag
        self.tagMatch = function (node) {
            var tags = node.attributes.tags;
            for (var t = 0; t < tags.length; t++){
                if (tags[t].toUpperCase().indexOf(self.filter().toUpperCase()) !== -1) {
                    return true;
                }
            }
            return false;
        };

        // Filters nodes
        self.filterNodes = function (){
            for (var n = 0;  n < self.nodes().length;  n++) {
                var node = self.nodes()[n];
                if (self.titleMatch(node) || self.contributorMatch(node) || self.tagMatch(node)) {
                    self.eligibleNodes().push(n);
                }
            }
        };

        self.quickSearch = function () {
            self.eligibleNodes([]);
            // if backspace completely, previous nodes with prior sorting/count will be displayed
            if (self.filter() === '') {
                self.populateEligibleNodes(0, self.nodes().length);
            }
            else {
                self.filterNodes();
            }
        };

        // Onclick, directs user to project page
        self.nodeDirect = function(node) {
            location.href = '/'+ node.id;
        };

    },
    view : function(ctrl) {
        function loadMoreButton() {
            if (ctrl.pendingNodes()){
                return m('button', {'class': 'col-sm-12 text-muted', onclick: function() {
                        ctrl.loadUpToTen();
                }},
                m('i', {'class': 'fa fa-caret-down load-nodes'}));
            }
        }

        function sortAlphaAsc() {
            if (ctrl.loadingComplete()) {
                return m('button', {id: 'alphaAsc', 'class': ctrl.colorSortButtons('alphaAsc'), onclick: function() {
                    ctrl.sortBySortState(ctrl.sortState('alphaAsc'));
                }},
                    m('i', {'class': 'fa fa-angle-up'}));
            }
        }

        function sortAlphaDesc(){
            if (ctrl.loadingComplete()){
                return m('button', {'class': ctrl.colorSortButtons('alphaDesc'), onclick: function() {
                    ctrl.sortBySortState(ctrl.sortState('alphaDesc'));
                }},
                m('i', {'class': 'fa fa-angle-down'}));
            }
        }

        function sortDateAsc(){
            if (ctrl.loadingComplete()){
                 return m('button', {'class': ctrl.colorSortButtons('dateAsc'), onclick: function() {
                     ctrl.sortBySortState(ctrl.sortState('dateAsc'));
                 }},
                 m('i', {'class': 'fa fa-angle-up'}));
            }
        }

        function sortDateDesc(){
            if (ctrl.loadingComplete()){
                return m('button', {'class': ctrl.colorSortButtons('dateDesc'), onclick: function() {
                    ctrl.sortBySortState(ctrl.sortState('dateDesc'));
               }},
                m('i', {'class': 'fa fa-angle-down'}));
            }
        }

        // Sort button for xs screen
        function ascending() {
            if (ctrl.loadingComplete()){
                return m('button', {'class': ctrl.colorSortButtonsXS('Asc'), onclick: function() {
                     ctrl.directionSort('Asc');
                     ctrl.sortDirectionGivenField();
                }},
                     m('i', {'class': 'fa fa-angle-up'}));
            }
        }

        // Sort button for xs screen
        function descending() {
            if (ctrl.loadingComplete()){
                return m('button', {'class': ctrl.colorSortButtonsXS('Desc'), onclick: function() {
                    ctrl.directionSort('Desc');
                    ctrl.sortDirectionGivenField();
                }},
                    m('i', {'class': 'fa fa-angle-down'}));
            }
        }

        // Dropdown for XS screen - if sort on title on large screen, when resize to xs, 'title' is default selected
        function defaultSelected() {
            var selected = ctrl.preSelectField();
            if (selected === 'alpha') {
                return [m('option', {value: 'alpha', selected:'selected'}, 'Title'), m('option', {value: 'date'}, 'Modified')];
            }
            else {
                return [m('option', {value: 'alpha'}, 'Title'), m('option', {value: 'date', selected:'selected'}, 'Modified')];
            }
        }


        function searchBar() {
            if (ctrl.loadingComplete()){
                return m('div.m-v-sm', {'class' : 'input-group'}, [
                    m('span', {'class': 'input-group-addon'}, m('i', {'class': 'fa fa-search'})),
                    m('input[type=search]', {'id': 'searchQuery', 'class': 'form-control', placeholder: 'Quick search projects', onkeyup: function(search) {
                        ctrl.filter(search.target.value);
                        ctrl.quickSearch();}
                    }),
                    m('span', {'class': 'input-group-addon', onclick: function() {
                        ctrl.filter('');
                        document.getElementById('searchQuery').value = '';
                        ctrl.quickSearch();
                    }},  m('button', m('i', {'class': 'fa fa-times'})))
                ]);
            }
        }

        function displayNodes() {
            if (ctrl.eligibleNodes().length ===0 && ctrl.filter() != null) {
                return m('div', {'class': 'row m-v-sm'}, m('div', {'class': 'col-sm-10 col-sm-offset-1'},
                    m('div', {'class': 'row'}, [
                        m('div', {'class': 'col-sm-1'}),
                        m('div', {'class': 'col-sm-11'},[m('p', {'class' :'fa fa-exclamation-triangle'}, m('em', '  No results found!'))])
                    ])
                ));
            }
            else {
                return ctrl.eligibleNodes().slice(0, ctrl.countDisplayed()).map(function(n){
                    return projectView(ctrl.nodes()[n]);
                });
            }
        }

        function projectView(project) {
            var numContributors = project.embeds.contributors.links.meta.total;
            return m('div', {'class': 'row m-v-sm'}, m('div', {'class': 'col-sm-8 col-sm-offset-2'},
                m('div', {'class': 'row node-styling', onclick: function(){{ctrl.nodeDirect(project);
                }}}, [
                    m('div', {'class': 'col-sm-6 col-md-6 col-lg-5 p-v-xs'}, project.attributes.title),
                    m('div', {'class': 'col-sm-3 col-md-3 col-lg-4 text-muted p-v-xs'}, $osf.contribNameFormat(project, numContributors, ctrl.getFamilyName)),
                    m('div', {'class': 'col-sm-3 col-md-3 col-lg-3 p-v-xs'}, ctrl.formatDate(project))
                ])
            ));
        }

        function xsDropdown () {
            if (ctrl.loadingComplete()) {
                return m('div', {'class': 'row'}, m('div', {'class': 'col-sm-8 col-sm-offset-2'},
                    m('div. node-sort-dropdown.text-right', {'class': 'row'}, [
                        m('div.f-w-xl', {'class': 'col-sm-12'},
                            m('span', ascending(), descending()),
                            m('label', [
                                m('select', {'class': 'form-control', id: 'sortDropDown', onchange: function(dropdown){
                                    ctrl.fieldSort(dropdown.target.value);
                                    ctrl.sortFieldGivenDirection();
                                }}, defaultSelected())
                            ])
                        )]
                    ))
                );
            }
        }

        function resultsFound(){
            return m('div', {'class': 'container quick-project'}, [
                m('div', {'class': 'row'},
                    m('div', {'class': 'col-md-10 col-md-offset-1'},
                    m('div', {'class': 'col-sm-12'}, m('h3', 'My Projects')))),
                m('div', {'class': 'row'},
                    m('div', {'class': 'col-sm-3'}),
                    m('div.m-b-sm.text-center', {'class': 'col-sm-6'}, [
                        searchBar(),
                        ctrl.loadingComplete() ? '' : m('.spinner-div', m('div.logo-spin.logo-sm.m-r-md'), 'Loading projects...')
                    ]),
                    m('div', {'class': 'col-sm-3'})),

                m('div', {class: 'row'},
                    m('div.text-center.m-b-sm', {'class': 'col-sm-12'},
                    m('h5', 'Go to ', m('a', {href:'/dashboard/'}, 'My Projects'),  ' to organize your work or ', m('a', {href: '/search/'}, 'Search Everything')
                    ))
                ),

                m('div', {'class': 'row'}, m('div', {'class': 'col-sm-8 col-sm-offset-2'},
                    m('div.node-col-headers', {'class': 'row'}, [
                        m('div.p-v-xs.f-w-xl', {'class': 'col-sm-6 col-md-6 col-lg-5'}, 'Title', sortAlphaAsc(), sortAlphaDesc()),
                        m('div.f-w-xl.p-v-xs', {'class': 'col-sm-3 col-md-3 col-lg-4'}, 'Contributors'),
                        m('div.f-w-xl.p-v-xs', {'class': 'col-sm-3 col-md-3 col-lg-3'}, 'Modified', m('span.sort-group', sortDateAsc(), sortDateDesc()))]
                    )
                )),

                xsDropdown(),

                displayNodes(),
                m('div', {'class': 'row'}, [
                    m('div', {'class': 'col-xs-5'}),
                    m('div', {'class': 'col-xs-2'}, loadMoreButton()),
                    m('div', {'class': 'col-xs-5'})
                ])
            ]);
        }

        if (ctrl.eligibleNodes().length === 0 && ctrl.filter() == null) {
            return m('div', {'class': 'container'}, [
                m('div', {'class': 'row'}, [
                    m('div', {'class': 'col-sm-1'}),
                    m('div', {'class': 'col-sm-11'}, m('h3', 'My Projects'))
                ]),
                m('div', {'class': 'row m-v-md'},
                    m('div', {'class': 'col-sm-1'}),
                    m('div', {'class': 'col-sm-11'}, m('h4', 'You have no projects. Go ', m('a', {href: '/dashboard'}, 'here'), ' to create one.'))
            )]
        );
        }
        else {
            return resultsFound();
        }
    }
};
module.exports = QuickSearchProject;



