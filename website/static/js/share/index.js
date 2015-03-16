require('c3/c3.css');
require('../../css/share-search.css');

var m = require('mithril');
var $osf = require('osfHelpers');
var Stats = require('../share/stats.js');
var utils = require('../share/utils.js');
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
    self.results = [];
    self.query = m.prop($osf.urlParams().q || '');
    m.request({
        method: 'get',
        background: true,
        url: '/api/v1/share/providers/'
    }).then(function(data) {
        self.ProviderMap = data.providerMap
    });
};


ShareApp.view = function(ctrl) {
    return m('.row', [
        m('.col-md-offset-1.col-md-10', [
            SearchBar.view(ctrl.searchBarController),
            Stats.view(ctrl.statsController),
            m('br'),
            Results.view(ctrl.resultsController),
            m('.row', m('.col-md-12', {style: 'padding-top: 30px;'}, m('span', m.trust(MESSAGES.ABOUTSHARE))))
        ])
    ]);
};

ShareApp.controller = function() {
    var self = this;

    self.vm = new ShareApp.ViewModel(self.vm);
    self.statsController = new Stats.controller(self.vm);
    self.resultsController = new Results.controller(self.vm);
    self.searchBarController = new SearchBar.controller(self.vm);

    History.Adapter.bind(window, 'statechange', function(e) {
        var state = History.getState().data;
        if (state.query === self.vm.query()) return;
        self.vm.query(state.query);
        utils.search(self.vm);
    });
};

module.exports = ShareApp;
