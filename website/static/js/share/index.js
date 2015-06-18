'use strict';

require('c3/c3.css');
require('../../css/share-search.css');

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
    self.showFooter = (self.query() === '');
    self.requiredFilters = $osf.urlParams().required ? $osf.urlParams().required.split('|') : [];
    self.optionalFilters = $osf.urlParams().optional ? $osf.urlParams().optional.split('|') : [];
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
            Footer.view(ctrl.footerController),
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

        self.sideBarController = new SideBar.controller(self.vm);
        self.statsController = new Stats.controller(self.vm);
        self.resultsController = new Results.controller(self.vm);
        self.searchBarController = new SearchBar.controller(self.vm);
        self.footerController = new Footer.controller(self.vm);

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
