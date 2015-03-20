require('c3/c3.css');
require('../../css/share-search.css');

var m = require('mithril');
var $osf = require('osfHelpers');
var Stats = require('../share/stats.js');
var utils = require('../share/utils.js');
var SideBar = require('../share/sideBar.js');
var Results = require('../share/results.js');
var History = require('exports?History!history');
var SearchBar = require('../share/searchBar.js');
var MESSAGES = JSON.parse(require('raw!../share/messages.json'));

var ShareApp = {};

ShareApp.ViewModel = function() {
    var self = this;

    self.time = 0;
    self.page = 0;
    self.count = 0;
    self.results = null;
    self.query = m.prop($osf.urlParams().q || '');
   };


ShareApp.view = function(ctrl) {
    return m('', [
        m('.col-xs-12', [
            SearchBar.view(ctrl.searchBarController),
            Stats.view(ctrl.statsController),
            ctrl.vm.results !== null ? ctrl.renderSort() : [],
            m('.row.searchContent', [
               m('.col-md-2.col-lg-3', [
                    SideBar.view(ctrl.sideBarController)
                ]),
                m('.col-md-10.col-lg-9', [
                    Results.view(ctrl.resultsController)
                ])
            ]),
            m('.row', m('.col-md-12', {style: 'padding-top: 30px;'}, m('span', m.trust(MESSAGES.ABOUTSHARE))))
        ])
    ]);
};

ShareApp.controller = function() {
    var self = this;

    self.vm = new ShareApp.ViewModel(self.vm);

    m.request({
        method: 'get',
        background: false,
        url: '/api/v1/share/providers/'
    }).then(function(data) {
        self.vm.ProviderMap = data.providerMap;

        self.sideBarController = new SideBar.controller(self.vm);
        self.statsController = new Stats.controller(self.vm);
        self.resultsController = new Results.controller(self.vm);
        self.searchBarController = new SearchBar.controller(self.vm);

    });

    self.renderSort = function(){
        return m('.btn-group', {style: {'float': 'right'}}, [
            m('button.btn.btn-default.dropdown-taggle', {
                    'data-toggle': 'dropdown',
                    'aria-expanded': 'false'
                }, ['Sort by: ' + self.vm.sort() + ' ', m('span.caret')]
            ),
                m('ul.dropdown-menu', {'role': 'menu'}, self.sideBarController.renderSort())])
    };


    History.Adapter.bind(window, 'statechange', function(e) {
        var state = History.getState().data;
        if (state.query === self.vm.query() &&
            state.sort === self.vm.sort() &&
            utils.arrayEqual(state.optionalFilters, self.vm.optionalFilters) &&
            utils.arrayEqual(state.requiredFilters, self.vm.requiredFilters)) return;
        self.vm.optionalFilters = state.optionalFilters;
        self.vm.requiredFilters = state.requiredFilters;
        self.vm.query(state.query);
        self.vm.sort(state.sort);
        utils.search(self.vm);
    });
};

module.exports = ShareApp;
