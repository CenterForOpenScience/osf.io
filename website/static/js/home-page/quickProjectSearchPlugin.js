/**
 * UI and function to quick search projects
 */

var m = require('mithril');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var AddProject = require('js/addProjectPlugin');
var NodeFetcher = require('js/myProjects').NodeFetcher;
var lodashGet = require('lodash.get');

// CSS
require('css/quick-project-search-plugin.css');
require('loaders.css/loaders.min.css');

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
        self.errorLoading = m.prop(false);  // True if error retrieving projects or contributors.
        self.someDataLoaded = m.prop(false);

        // Switches errorLoading to true
        self.requestError = function(result) {
            self.errorLoading(true);
            Raven.captureMessage('Error loading user projects on home page.', {
                extra: {requestReturn: result}
            });
        };

        self.templateNodes = new NodeFetcher('nodes');
        self.templateNodes.start();

        // Load up to first ten nodes
        var url = $osf.apiV2Url('users/me/nodes/', { query : { 'embed': ['contributors','root', 'parent']}});
        var promise = m.request({method: 'GET', url : url, config : xhrconfig, background: true});
        promise.then(function(result) {
            self.countDisplayed(result.data.length);
            result.data.forEach(function (node) {
                node.attributes.title = $osf.decodeText(node.attributes.title);
                self.nodes().push(node);
                self.retrieveContributors(node);
            });
            self.populateEligibleNodes(0, self.countDisplayed());
            self.next(result.links.next);
            self.someDataLoaded = m.prop(true);
            // NOTE: This manual redraw is necessary because we set background: true on
            // the request, which prevents a redraw. This redraw allows the loading
            // indicator to go away and the first 10 nodes to be rendered
        }, function _error(result){
            self.requestError(result);
            m.redraw();
        });
        promise.then(
            function(){
                if (self.next()) {
                    self.recursiveNodes(self.next());
                }
                else {
                    self.loadingComplete(true);
                    m.redraw();
                }
            }, function _error(result){
                self.requestError(result);
            });

        // Recursively fetches remaining user's nodes
        self.recursiveNodes = function (url) {
            if (self.next()) {
                var nextPromise = m.request({method: 'GET', url : url, config : xhrconfig, background : true});
                nextPromise.then(function(result){
                    // NOTE: We need to redraw here in because we set background: true on the request
                    // This redraw allows the "load more" button to be displayed
                    m.redraw();
                    result.data.forEach(function(node){
                        node.attributes.title = $osf.decodeText(node.attributes.title);
                        self.nodes().push(node);
                        self.retrieveContributors(node);
                    });
                    if (self.filter()) {
                        self.quickSearch();
                    }
                    else {
                        self.populateEligibleNodes(self.eligibleNodes().length, self.nodes().length);
                    }
                self.next(result.links.next);
                self.recursiveNodes(self.next());
                }, function _error(result){
                    self.requestError(result);
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
                var fullName;
                if (contrib.attributes.unregistered_contributor) {
                    fullName = contrib.attributes.unregistered_contributor;
                    contributorList.push(fullName);
                }
                else if (contrib.embeds.users.data) {
                    fullName = contrib.embeds.users.data.attributes.full_name;
                    contributorList.push(fullName);
                }
                else if (contrib.embeds.users.errors) {
                    fullName = contrib.embeds.users.errors[0].meta.full_name;
                    contributorList.push(fullName);
                }

            });
            self.contributorMapping[node.id] = contributorList;
        };

        // Gets contrib family name for display
        self.getFamilyName = function(i, node) {
            var contributor = node.embeds.contributors.data[i];
            var attributes;

            if (contributor) {
                if (contributor.attributes.unregistered_contributor) {
                    return contributor.attributes.unregistered_contributor;
                }
                else if (contributor.embeds.users.data) {
                    attributes = contributor.embeds.users.data.attributes;
                }
                else if (contributor.embeds.users.errors) {
                    attributes = contributor.embeds.users.errors[0].meta;
                }
                return $osf.findContribName(attributes);
            }
            return 'a contributor';

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

        // Filtering on root project
        self.rootMatch = function (node) {
            var root = lodashGet(node, 'embeds.root.data.attributes.title', '');
            return (root.toUpperCase().indexOf(self.filter().toUpperCase()) !== -1);
        };

        // Filtering on title
        self.titleMatch = function (node) {
            return (node.attributes.title.toUpperCase().indexOf(self.filter().toUpperCase()) !== -1);
        };

        // Filtering on contrib
        self.contributorMatch = function (node) {
            var contributors = self.contributorMapping[node.id];
            if (contributors) {
                for (var c = 0; c < contributors.length; c++) {
                if (contributors[c].toUpperCase().indexOf(self.filter().toUpperCase()) !== -1){
                    return true;
                }}
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
                if (self.titleMatch(node) || self.contributorMatch(node) || self.tagMatch(node) || self.rootMatch(node)) {
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

    },
    view : function(ctrl) {
        if (ctrl.errorLoading()) {
            return m('p.text-center.m-v-md', 'Error loading projects. Please refresh the page. Contact ' + $osf.osfSupportEmail() + ' for further assistance.');
        }

        if (!ctrl.someDataLoaded()) {
            return m('.loader-inner.ball-scale.text-center.m-v-xl', m(''));
        }

        function loadMoreButton(){
            if (ctrl.pendingNodes()){
                return m('button.col-sm-12.text-muted', {onclick: function(){
                    ctrl.loadUpToTen();
                    $osf.trackClick('quickSearch', 'view', 'load-more');
                }},
                    m('i.fa.fa-caret-down.load-nodes.m-b-xl'));
            }
        }

        function sortAlphaAsc() {
            if (ctrl.loadingComplete()) {
                return m('button', {'class': ctrl.colorSortButtons('alphaAsc'), onclick: function() {
                    ctrl.sortBySortState(ctrl.sortState('alphaAsc'));
                    $osf.trackClick('quickSearch', 'view', 'sort-' + ctrl.sortState());
                }},
                    m('i.fa.fa-angle-up'));
            }
        }

        function sortAlphaDesc(){
            if (ctrl.loadingComplete()){
                return m('button', {'class': ctrl.colorSortButtons('alphaDesc'), onclick: function() {
                    ctrl.sortBySortState(ctrl.sortState('alphaDesc'));
                    $osf.trackClick('quickSearch', 'view', 'sort-' + ctrl.sortState());
                }},
                    m('i.fa.fa-angle-down'));
            }
        }

        function sortDateAsc(){
            if (ctrl.loadingComplete()){
                 return m('button', {'class': ctrl.colorSortButtons('dateAsc'), onclick: function() {
                     ctrl.sortBySortState(ctrl.sortState('dateAsc'));
                     $osf.trackClick('quickSearch', 'view', 'sort-' + ctrl.sortState());
                 }},
                     m('i.fa.fa-angle-up'));
            }
        }

        function sortDateDesc(){
            if (ctrl.loadingComplete()){
                return m('button', {'class': ctrl.colorSortButtons('dateDesc'), onclick: function() {
                    ctrl.sortBySortState(ctrl.sortState('dateDesc'));
                    $osf.trackClick('quickSearch', 'view', 'sort-' + ctrl.sortState());
               }},
                    m('i.fa.fa-angle-down'));
            }
        }

        // Sort button for xs screen
        function ascending() {
            if (ctrl.loadingComplete()){
                return m('button', {'class': ctrl.colorSortButtonsXS('Asc'), onclick: function() {
                     ctrl.directionSort('Asc');
                     ctrl.sortDirectionGivenField();
                     $osf.trackClick('quickSearch', 'view', 'sort-' + ctrl.sortState());
                }},
                     m('i.fa.fa-angle-up'));
            }
        }

        // Sort button for xs screen
        function descending() {
            if (ctrl.loadingComplete()){
                return m('button', {'class': ctrl.colorSortButtonsXS('Desc'), onclick: function() {
                    ctrl.directionSort('Desc');
                    ctrl.sortDirectionGivenField();
                    $osf.trackClick('quickSearch', 'view', 'sort-' + ctrl.sortState());
                }},
                     m('i.fa.fa-angle-down'));
            }
        }

        // Dropdown for XS screen - if sort on title on large screen, when resize to xs, 'title' is default selected
        function defaultSelected() {
            var selected = ctrl.preSelectField();
            switch (selected) {
                case 'title':
                    return [m('option', {value: 'title', selected:'selected'}, 'Title'), m('option', {value: 'date'}, 'Modified')];

                case 'date':
                    return [m('option', {value: 'title'}, 'Title'), m('option', {value: 'date', selected:'selected'}, 'Modified')];
            }
        }

        function searchBar() {
            return m('div.m-v-sm.quick-search-input', [
                m('input[type=search]', {'id': 'searchQuery', 'class': 'form-control', placeholder: 'Search your projects', onkeyup: function(search) {
                    ctrl.filter(search.target.value);
                    ctrl.quickSearch();
                }, onchange: function() {
                    $osf.trackClick('quickSearch', 'filter', 'search-projects');
                }})
            ]);
            }

        function xsDropdown() {
            if (ctrl.loadingComplete()){
                return m('.row', m('.col-xs-12.f-w-xl.node-sort-dropdown.text-right',
                    m('span', ascending(), descending()),
                    m('label', [
                        m('select.form-control', {'id': 'sortDropDown', onchange: function(dropdown){
                            ctrl.fieldSort(dropdown.target.value);
                            $osf.trackClick('quickSearch', 'view', 'sort-' + ctrl.sortState());
                            ctrl.sortFieldGivenDirection();
                        }}, defaultSelected())
                    ])
                ));
            }
        }

        function headerTemplate ( ){
            return [ m('h2.col-xs-9', 'Dashboard'), m('.m-b-lg.col-xs-3', m('.pull-right', m.component(AddProject, {
                buttonTemplate : m('button.btn.btn-success.btn-success-high-contrast.m-t-md.f-w-xl[data-toggle="modal"][data-target="#addProjectFromHome"]', {onclick: function(){
                                $osf.trackClick('quickSearch', 'add-project', 'open-add-project-modal');
                }}, 'Create new project'),
                modalID : 'addProjectFromHome',
                stayCallback : function _stayCallback_inPanel() {
                                document.location.reload(true);
                },
                trackingCategory: 'quickSearch',
                trackingAction: 'add-project',
                templatesFetcher: ctrl.templateNodes
            })))];
        }

        if (ctrl.eligibleNodes().length === 0 && ctrl.filter() == null) {
            return m('',
                [
                    m('.row', headerTemplate()),
                    m('.row.quick-project',
                        m('.col-sm-12.text-center', [
                            m('p','You have no projects yet. Create a project with the button on the top right.'),
                            m('p', 'This feature allows you to search and quickly access your projects.'),
                            m('img.img-responsive.center-block', { src : '/static/img/quicksearch-min.png', alt : 'Preview of a full quick projects screen'})
                        ])
                    )
                ]
            );
        }
        else {
            return m('.row',
                m('.col-xs-12', headerTemplate()),
                m('.col-xs-12',[
                    m('.row.quick-project', m('.col-xs-12',
                    m('.m-b-sm.text-center', [
                        searchBar()
                    ]),
                    m('p.text-center.f-w-lg', [ 'Go to ', m('a', {href:'/myprojects/', onclick: function(){
                        $osf.trackClick('quickSearch', 'navigate', 'navigate-to-my-projects');
                    }}, 'My Projects'),  ' to organize your work or ',
                        m('a', {href: '/search/', onclick: function(){ $osf.trackClick('quickSearch', 'navigate', 'navigate-to-search-the-OSF'); }}, 'search'), ' the GakuNin RDM' ]),
                    m('.quick-search-table', [
                        m('.row.node-col-headers.m-t-md', [
                            m('.col-sm-3.col-md-6', m('.quick-search-col', 'Title', sortAlphaAsc(), sortAlphaDesc())),
                            m('.col-sm-3.col-md-3', m('.quick-search-col', 'Contributors')),
                            m('.col-sm-3.col-md-3', m('.quick-search-col','Modified', m('span.sort-group', sortDateAsc(), sortDateDesc())))
                        ]),
                        xsDropdown(),
                        m.component(QuickSearchNodeDisplay, {
                            eligibleNodes: ctrl.eligibleNodes,
                            nodes: ctrl.nodes,
                            filter: ctrl.filter,
                            countDisplayed: ctrl.countDisplayed,
                            getFamilyName: ctrl.getFamilyName,
                            formatDate: function(node) {
                                return ctrl.formatDate(node);
                            },
                            loadingComplete: ctrl.loadingComplete
                        }),
                        !ctrl.loadingComplete() && ctrl.filter() ? m('.loader-inner.ball-scale.text-center', m('')) : m('.m-v-md')

                                ]),
                                m('.text-center', loadMoreButton())
                    ))
                ])
            );
        }
    }
};

function getAncestorDescriptor(node, nodeID, ancestor, ancestorID) {
    var ancestorDescriptor;
    var ancestorTitleRequest = $osf.decodeText(lodashGet(node, 'embeds.' + ancestor + '.data.attributes.title', ''));
    var errorRequest = lodashGet(node, 'embeds.' + ancestor + '.errors[0].detail', '');
    switch(errorRequest) {
        case '':
            if (ancestorID === nodeID || ancestorID === '') {
                ancestorDescriptor = '';
            }
            else {
//            Remove trailing period
                if (ancestorTitleRequest[ancestorTitleRequest.length-1] === '.') {
                    ancestorTitleRequest = ancestorTitleRequest.slice(0,-1);
                }
                ancestorDescriptor = ancestorTitleRequest + ' / ';
            }
            break;

        case 'You do not have permission to perform this action.':
            if (ancestor === 'root') {
                ancestorDescriptor = m('em', 'Private Project / ');
            }
            if (ancestor === 'parent') {
                ancestorDescriptor = m('em', 'Private / ');
            }
            break;

        default:
            ancestorDescriptor = 'Name Unavailable / ';
    }
    return ancestorDescriptor;
}

var QuickSearchNodeDisplay = {
    view: function(ctrl, args) {
        if (args.eligibleNodes().length === 0 && args.filter() != null && args.loadingComplete() === true) {
            return m('.row.m-v-sm', m('.col-sm-12',
                m('.row',
                    m('.col-sm-12', m('em', 'No results found!'))
                ))
            );
        }
        else {
            return m('.', args.eligibleNodes().slice(0, args.countDisplayed()).map(function(n){
                var project = args.nodes()[n];
                var numContributors = project.embeds.contributors.links.meta.total;
                var nodeID = project.id;
                var title = project.attributes.title;

                var rootID = lodashGet(project, 'embeds.root.data.id', '');
                var rootURL = lodashGet(project, 'embeds.root.data.links.self');
                var root = getAncestorDescriptor(project, nodeID, 'root', rootID);

                var parentID = lodashGet(project, 'embeds.parent.data.id', '');
                var parent = getAncestorDescriptor(project, nodeID, 'parent', parentID);

                // API doesn't provide grandparent GUID, so we have to use API URL.
                var grandParentURL = lodashGet(project, 'embeds.parent.data.relationships.parent.links.related.href', '');

                // Parent and root ID are the same, and they aren't both private (would cause both to have empty ID)
                if (parentID === rootID && parentID !== '') {
                    parent = '';
                }

                // There are projects in between root and parent and they aren't both private
                if (grandParentURL !== rootURL && grandParentURL !== '' && rootID !== '') {
                    root += '... / ';
                }

                return m('a', {href: '/' + project.id, onclick: function() {
                    $osf.trackClick('quickSearch', 'navigate', 'navigate-to-specific-project');
                }}, m('.m-v-sm.node-styling',  m('.row', m('div',
                    [
                        m('.col-sm-3.col-md-6.p-v-xs', m('.quick-search-col', root, parent, m('strong', title))),
                        m('.col-sm-3.col-md-3.p-v-xs', m('.quick-search-col', $osf.contribNameFormat(project, numContributors, args.getFamilyName))),
                        m('.col-sm-3.col-md-3.p-v-xs', m('.quick-search-col', args.formatDate(project)))
                    ]
                ))));
            }));
        }
    }
};

module.exports = QuickSearchProject;
