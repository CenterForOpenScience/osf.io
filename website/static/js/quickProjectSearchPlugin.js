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

        // When 'load more' button pressed, loads up to 10 nodes
        self.loadUpToTen = function () {
            var requested = self.nodes().splice(0, 10);
            for (var i = 0; i < requested.length; i++) {
                self.displayedNodes().push(requested[i])
            }
            self.countDisplayed(self.displayedNodes().length);
            return self.displayedNodes()
        };

        // If < 10 contribs, map node id to contrib names. Otherwise, make a call to get all contribs.
        self.retrieveContributors = function(node) {
            if (node.embeds.contributors.links.meta.total > 10) {
                self.pullOverTenContributorNames(node)
            }
            else {
                var contributors = node.embeds.contributors;
                self.mapNodeToContributors(node, contributors)
                }
        };

        // Call to get up to 1000 contributors on a node.
        self.pullOverTenContributorNames = function (node) {
            var url = $osf.apiV2Url('nodes/' + node.id + '/contributors/', { query : { 'page[size]': 1000 }});
            var promise = m.request({method: 'GET', url : url, config: xhrconfig, background : true});
            promise.then(function(result){
                self.mapNodeToContributors(node, result)
            })
        };

        // Maps node id to list of contrib names for later searching
        self.mapNodeToContributors = function (node, contributors){
            var contributorList = [];
            contributors.data.forEach(function(contrib){
                fullName = contrib.embeds.users.data.attributes.full_name;
                contributorList.push(fullName)

            });
            self.contributorMapping[node.id] = contributorList
        };

        // Gets contrib family name for display
        self.getFamilyName = function(i, node) {
            return node.embeds.contributors.data[i].embeds.users.data.attributes.family_name
        };

        // Formats contrib family names for display
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

         // Formats date for display
        self.formatDate = function (node) {
            return new $osf.FormattableDate(node.attributes.date_modified).local
        };


        // Shifts nodes back to master node list (from displayedNodes or nonMatchingNodes)
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

        // Sorts nodes depending on current sort state.
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

        // For xs screen
        self.sortFieldGivenDirection = function(){
            var dropdown = document.getElementById('sortDropDown');
            var fieldSort = dropdown.options[dropdown.selectedIndex].value;
            var directionSort = self.preSelectDirection();
            self.sortState(fieldSort + directionSort);
            self.sortNodesAndModifyDisplay()
        };

        // For xs screen
        self.sortDirectionGivenField = function(clicked) {
            console.log('sorted');
            var fieldSort = self.preSelectField();
            var directionSort = clicked.id;
            self.sortState(fieldSort + directionSort);
            self.sortNodesAndModifyDisplay()
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
        self.colorSortButtons = function () {
            var sortButtons = ['dateAsc', 'dateDesc', 'alphaAsc', 'alphaDesc'];
            var button = document.getElementById(self.sortState()).className = 'selected';
            sortButtons.forEach(function(button) {
                if (self.sortState() !== button) {
                    document.getElementById(button).className = 'not-selected'
                }
            });

            var shrunkSortButtons = ['Asc', 'Desc'];
            var direction = self.preSelectDirection();
            document.getElementById(direction).className = 'selected';
            if (direction === 'Asc'){
                document.getElementById('Desc').className = 'not-selected'
            }
            else {
                document.getElementById('Asc').className = 'not-selected'
            }
        };

        // Shifts all nodes back to master node list, sorts, and returns self.countDisplayed() number of nodes for display
        self.sortNodesAndModifyDisplay = function () {
            self.restoreToNodeList(self.displayedNodes());
            self.sortBySortState();
            self.colorSortButtons();
            self.displayedNodes(self.nodes().splice(0, self.countDisplayed()))
        };

        // Filtering on title
        self.noTitleMatch = function (node) {
            return (node.attributes.title.toUpperCase().indexOf(self.filter().toUpperCase()) === -1);
        };

        // Filtering on contrib
        self.noContributorMatch = function (node) {
            var contributors = self.contributorMapping[node.id];

            for (var c = 0; c < contributors.length; c++) {
                if (contributors[c].toUpperCase().indexOf(self.filter().toUpperCase()) !== -1){
                    return false
                }
            }
            return true
        };

        // Filtering on tag
        self.noTagMatch = function (node) {
            var tags = node.attributes.tags;
            for (var t = 0; t < tags.length; t++){
                if (tags[t].toUpperCase().indexOf(self.filter().toUpperCase()) !== -1) {
                    return false
                }
            }
            return true
        };

        // Filters nodes
        self.filterNodes = function (){
            for (var n = self.nodes().length - 1; n >= 0; n--) {
                var node = self.nodes()[n];
                if (self.noTitleMatch(node) && self.noContributorMatch(node) && self.noTagMatch(node)) {
                    self.nonMatchingNodes().push(node);
                    self.nodes().splice(n, 1)
                }
            }
        };

        // Colors node div and changes cursor to pointer on hover
        self.mouseOver = function (node) {
            node.style.backgroundColor='#E0EBF3';
            node.style.cursor = 'pointer'
        };

        self.mouseOut = function (node) {
            node.style.backgroundColor='#fcfcfc'
        };

        self.clearSearch = function () {
            document.getElementById('searchQuery').value="";
            self.filter(document.getElementById('searchQuery').value);
            self.quickSearch()
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

        // Onclick, directs user to project page
        self.nodeDirect = function(node) {
            location.href = '/'+ node.id
        };

    },
    view : function(ctrl) {
        function loadMoreButton() {
            if (ctrl.nodes().length !== 0){
                return m('button', {class: 'col-sm-12 text-muted', onclick: function() {
                        ctrl.loadUpToTen()}
                },
                m('i', {class: 'fa fa-caret-down load-nodes'}))
            }
        }

        function sortAlphaAsc() {
            if (ctrl.loadingComplete()) {
                return m('button', {id: 'alphaAsc', class: 'not-selected', onclick: function() {
                    ctrl.sortState('alphaAsc');
                    ctrl.sortNodesAndModifyDisplay();
                }},
                    m('i', {class: 'fa fa-angle-up'}))
            }
        }

        function sortAlphaDesc(){
            if (ctrl.loadingComplete()){
                return m('button', {id: 'alphaDesc', class: 'not-selected', onclick: function() {
                    ctrl.sortState('alphaDesc');
                    ctrl.sortNodesAndModifyDisplay();
                }},
                m('i', {class: 'fa fa-angle-down'}))
            }
        }

        function sortDateAsc(){
            if (ctrl.loadingComplete()){
                 return m('button', {id: 'dateAsc', class: 'not-selected', onclick: function() {
                     ctrl.sortState('dateAsc');
                     ctrl.sortNodesAndModifyDisplay()}},
                 m('i', {class: 'fa fa-angle-up'}))
            }
        }

        function sortDateDesc(){
            if (ctrl.loadingComplete()){
                return m('button', {id: 'dateDesc', class: 'selected', onclick: function() {
                    ctrl.sortState('dateDesc');
                    ctrl.sortNodesAndModifyDisplay();
               }},
                m('i', {class: 'fa fa-angle-down'}))
            }
        }

        // Sort button for xs screen
        function ascending() {
            if (ctrl.loadingComplete()){
                var direction = ctrl.preSelectDirection()
                if (direction === 'Asc') {
                    return m('button', {id: 'Asc', class: 'selected', onclick: function() {
                         ctrl.sortDirectionGivenField(this)
                         }},
                         m('i', {class: 'fa fa-angle-up'}))
                }
                else {
                    return m('button', {id: 'Asc', class: 'not-selected', onclick: function() {
                         ctrl.sortDirectionGivenField(this)
                         }},
                         m('i', {class: 'fa fa-angle-up'}))

                }
            }
        }

        // Sort button for xs screen
        function descending() {
            if (ctrl.loadingComplete()){
                var direction = ctrl.preSelectDirection();
                if (direction === 'Desc') {
                    return m('button', {id: 'Desc', class: 'selected', onclick: function() {
                         ctrl.sortDirectionGivenField(this)
                         }},
                         m('i', {class: 'fa fa-angle-down'}))
                }
                else {
                    return m('button', {id: 'Desc', class: 'not-selected', onclick: function() {
                         ctrl.sortDirectionGivenField(this)
                         }},
                         m('i', {class: 'fa fa-angle-down'}))
                }
            }
        }

        function defaultSelected() {
            var selected = ctrl.preSelectField();
            if (selected === 'alpha') {
                return [m('option', {value: 'alpha', selected:'selected'}, 'Title'), m('option', {value: 'date'}, 'Modified')]
            }
            else {
                return [m('option', {value: 'alpha'}, 'Title'), m('option', {value: 'date', selected:'selected'}, 'Modified')]
            }

        }

        function searchBar() {
            if (ctrl.loadingComplete()){
                return m('div', {class : 'input-group'}, [
                    m('span', {class: 'input-group-addon'}, m('i', {class: 'fa fa-search'})),
                    m('input[type=search]', {class: 'form-control', id: 'searchQuery', placeholder: 'Quick search projects', onkeyup: function() {ctrl.quickSearch()}}),
                    m('span', {class: 'input-group-addon', onclick: function() {ctrl.clearSearch()}},  m('button', m('i', {class: 'fa fa-times'})))
                ])
            }
        }

        function displayNodes() {
            if (ctrl.displayedNodes().length == 0 && ctrl.filter() != null) {
                return m('div', {class: 'row m-v-sm'}, m('div', {class: 'col-sm-10 col-sm-offset-1'},
                    m('div', {class: 'row'}, [
                        m('div', {class: 'col-sm-1'}),
                        m('div', {class: 'col-sm-11'},[m('p', {class :'fa fa-exclamation-triangle'}, m('em', '  No results found!'))])
                    ])
                ))
            }
            else {
                return ctrl.displayedNodes().map(function(n){
                    return projectView(n)
                })
            }
        }

        function projectView(project) {
            console.log('pending: ' + ctrl.nodes().length, ', displayed: ' + ctrl.displayedNodes().length, ', non-matching: ' + ctrl.nonMatchingNodes().length, ctrl.sortState());
            return m('div', {class: 'row m-v-sm'}, m('div', {class: 'col-sm-8 col-sm-offset-2'},
                m('div', {class: 'row node-styling',  onmouseover: function(){ctrl.mouseOver(this)}, onmouseout: function(){ctrl.mouseOut(this)}, onclick: function(){{ctrl.nodeDirect(project)}}}, [
                    m('div', {class: 'col-sm-7 col-md-6 col-lg-5 p-v-xs'}, project.attributes.title),
                    m('div', {class: 'col-sm-3 col-md-3 col-lg-4 text-muted  p-v-xs'}, ctrl.getContributors(project)),
                    m('div', {class: 'col-sm-2 col-md-3 col-lg-3 p-v-xs'}, ctrl.formatDate(project))
                ])
            ))
        }

        function resultsFound(){
            return m('div', {class: 'container'}, [
                m('div', {class: 'row'}, [
                    m('div', {'class': 'col-sm-1'}),
                    m('div', {'class': 'col-sm-11'}, m('h3', 'My Projects'))
                ]),
                m('div', {class: 'row'},
                    m('div', {class: 'col-sm-3'}),
                    m('div', {class: 'col-sm-6 m-b-md text-center'}, [
                        searchBar(),
                        ctrl.loadingComplete() ? '' : m('.spinner-div', m('div', {class:'logo-spin logo-sm m-r-lg'}), 'Loading projects...')
                    ]),
                    m('div', {class: 'col-sm-3'})),

                m('div', {class: 'row'}, m('div', {class: 'col-sm-8 col-sm-offset-2'},
                m('div', {class: 'row node-col-headers'}, [
                    m('div', {class: 'col-sm-7 col-md-6 col-lg-5 p-v-xs, f-w-xl'}, 'Title', sortAlphaAsc(), sortAlphaDesc()),
                    m('div', {class: 'col-sm-3 col-md-3 col-lg-4 f-w-xl p-v-xs'}, 'Contributors'),
                    m('div', {class: 'col-sm-2 col-md-3 col-lg-3 f-w-xl p-v-xs'}, 'Modified', m('span', {class: 'sort-group'}, sortDateAsc(), sortDateDesc())),
                ])
                )),

                m('div', {class: 'row'}, m('div', {class: 'col-sm-8 col-sm-offset-2'},
                    m('div', {class: 'row node-sort-dropdown'}, [
                        m('div', {class: 'col-sm-12 p-v-xs, f-w-xl'},
                            m('label', [m('span', 'Order by: '),
                                m('select', {class: 'form-control', id: 'sortDropDown', onchange: function(){ctrl.sortFieldGivenDirection(this)}},
                                    defaultSelected()),
                                ascending(), descending()]
                            )
                        )]
                    ))
                ),
                displayNodes(),
                m('div', {class: 'row'}, [
                    m('div', {class: 'col-sm-5'}),
                    m('div', {class: 'col-sm-2'}, loadMoreButton()),
                    m('div', {class: 'col-sm-5'})
                ])
            ]);
        }

        if (ctrl.displayedNodes().length == 0 && ctrl.filter() == null) {
            return m('div', {class: 'container'}, [
                m('div', {class: 'row'}, [
                    m('div', {'class': 'col-sm-1'}),
                    m('div', {'class': 'col-sm-11'}, m('h3', 'My Projects'))
                ]),
                m('div', {class: 'row m-v-md'},
                    m('div', {class: 'col-sm-1'}),
                    m('div', {class: 'col-sm-11'}, m('h4', 'You have no projects. Go here to create one.'))
            )]
        )}
        else {
            return resultsFound()
        }
    }
};
module.exports = quickSearchProject;


