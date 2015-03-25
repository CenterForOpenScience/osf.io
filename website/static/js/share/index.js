'use strict';

require('c3/c3.css');
require('../../css/share-search.css');

var m = require('mithril');
var $osf = require('js/osfHelpers');
var Stats = require('./stats');
var utils = require('./utils');
var SideBar = require('./sideBar');
var Results = require('./results');
var History = require('exports?History!history');
var SearchBar = require('./searchBar');
var MESSAGES = JSON.parse(require('raw!./messages.json'));

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
            ctrl.vm.results !== null ? renderSort(ctrl) : [],
            m('.row.search-content', [
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

    self.vm.sort = m.prop($osf.urlParams().sort || 'Relevance');
    self.vm.requiredFilters = $osf.urlParams().required ? $osf.urlParams().required.split('|') : [];
    self.vm.optionalFilters = $osf.urlParams().optional ? $osf.urlParams().optional.split('|') : [];


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


    History.Adapter.bind(window, 'statechange', function(e) {
        var state = History.getState().data;
        if (state.query === self.vm.query() && state.sort === self.vm.sort() &&
            utils.arrayEqual(state.optionalFilters, self.vm.optionalFilters) &&
            utils.arrayEqual(state.requiredFilters, self.vm.requiredFilters)) {

            return;
        }
        self.vm.optionalFilters = state.optionalFilters;
        self.vm.requiredFilters = state.requiredFilters;
        self.vm.query(state.query);
        self.vm.sort(state.sort);
        utils.search(self.vm);
    });
};

var renderSort = function(ctrl){
        return m('.btn-group.pull-right', [
            m('button.btn.btn-default.dropdown-toggle', {
                    'data-toggle': 'dropdown',
                    'aria-expanded': 'false'
                }, ['Sort by: ' + ctrl.vm.sort() + ' ', m('span.caret')]
            ),
                m('ul.dropdown-menu', {'role': 'menu'}, ctrl.sideBarController.renderSort())]);
    };


module.exports = ShareApp;
