'use strict';

require('c3/c3.css');
require('../../css/share-search.css');

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var Stats = require('./stats');
var utils = require('./utils');
var SideBar = require('./sideBar');
var Results = require('./results');
var Footer = require('./footer');
var History = require('exports?History!history');
var SearchBar = require('./searchBar');

var ShareApp = {};

ShareApp.ViewModel = function() {
    var self = this;

    self.time = 0;
    self.page = 0;
    self.count = 0;
    self.results = null;
    self.query = m.prop($osf.urlParams().q || '');
    self.sort = m.prop($osf.urlParams().sort || 'Relevance');
    self.showStats = false;
    self.resultsLoading = m.prop(false);
    self.rawNormedLoaded = m.prop(false);
    self.showFooter = (self.query() === '');
    self.requiredFilters = $osf.urlParams().required ? $osf.urlParams().required.split('|') : [];
    self.optionalFilters = $osf.urlParams().optional ? $osf.urlParams().optional.split('|') : [];

    self.sortMap = {
        'Date': 'providerUpdatedDateTime',
        Relevance: null
    };

    /** Sort the SHARE provider list for display. **/
    self.sortProviders = function() {
        return $.map(Object.keys(self.ProviderMap), function(result, index){
            return self.ProviderMap[result];
        }).sort(function(a,b){
                return a.long_name.toUpperCase() > b.long_name.toUpperCase() ? 1: -1;
        });
    };
};


ShareApp.view = function(ctrl) {
    return m('', [
        m('.col-xs-12', [
            SearchBar.view(ctrl.searchBarController),
            Stats.view(ctrl.statsController),
            ctrl.vm.results !== null ? m.component(SortBox, {vm: ctrl.vm}): [],
            ctrl.vm.results !== null ? m('.row.search-content', [
               m('.col-md-2.col-lg-3', [
                    m.component(SideBar, {vm: ctrl.vm})
                ]),
                m('.col-md-10.col-lg-9', [
                    m.component(Results, {vm: ctrl.vm})
                ])
            ]) : [],
            m.component(Footer, {vm: ctrl.vm})
        ])
    ]);
};

ShareApp.controller = function() {
    var self = this;

    self.vm = new ShareApp.ViewModel(self.vm);

    History.replaceState({
        query: self.vm.query(),
        sort: self.vm.sort(),
        optionalFilters: self.vm.optionalFilters,
        requiredFilters: self.vm.requiredFilters
    }, 'OSF | SHARE', '?' + utils.buildURLParams(self.vm));

    m.request({
        method: 'get',
        background: false,
        url: '/api/v1/share/providers/'
    }).then(function(data) {
        self.vm.ProviderMap = data.providerMap;

        self.statsController = new Stats.controller(self.vm);
        self.searchBarController = new SearchBar.controller(self.vm);

    });

    m.request({
        method: 'GET',
        background: true,
        url: '/api/v1/share/documents/status/'
    }).then(function(data) {
        self.vm.rawNormedLoaded(true);
    }, function(err) {
        // We expect this error response while the SHARE posgres API
        // is waiting to be put into production. This error response would also happen
        // if the external SHARE postgres API went down for some reason.
    });

    History.Adapter.bind(window, 'statechange', function(e) {
        var state = History.getState().data;
        if (!utils.stateChanged(self.vm)){
            return;
        }

        self.vm.optionalFilters = state.optionalFilters;
        self.vm.requiredFilters = state.requiredFilters;
        self.vm.query(state.query);
        self.vm.sort(state.sort);
        utils.search(self.vm);
    });
};

var SortBox = {
    view: function(ctrl, params) {
        var vm = params.vm;
        return m('.btn-group.pull-right', [
            m('button.btn.btn-default.dropdown-toggle', {
                    'data-toggle': 'dropdown',
                    'aria-expanded': 'false'
                }, ['Sort by: ' + vm.sort() + ' ', m('span.caret')]
            ),
                m('ul.dropdown-menu', {'role': 'menu'},
                    $.map(Object.keys(vm.sortMap), function(a) {
                        return m.component(SortItem, {vm: vm, key: a});
                    })
                )
        ]);

    }
};

var SortItem = {
    view: function(ctrl, params) {
        var vm = params.vm;
        var item = params.key;
        return m('li',
            m('a', {
                onclick: function(event) {
                    vm.sort(item);
                    utils.search(vm);
                }
            }, item)
        );
    }
};

module.exports = ShareApp;
