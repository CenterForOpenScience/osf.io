var m = require('mithril');
var $osf = require('osfHelpers');
var Stats = require('../share/stats.js');
var Results = require('../share/results.js');
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
};


ShareApp.view = function(ctrl) {
    return m('.row', [
        m('.col-md-offset-1.col-md-10', [
            SearchBar.view(ctrl.searchBarController),
            Stats.view(ctrl.statsController),
            m('br'),
            Results.view(ctrl.resultsController),
	    m('.row', m('.col-md-12', {style: "padding-top: 30px;"},m('span', m.trust(MESSAGES.ABOUTSHARE))))
        ])
    ]);
};

ShareApp.controller = function() {
    var self = this;

    self.vm = new ShareApp.ViewModel(self.vm);
    self.statsController = new Stats.controller(self.vm);
    self.resultsController = new Results.controller(self.vm);
    self.searchBarController = new SearchBar.controller(self.vm);
};

module.exports = ShareApp;
