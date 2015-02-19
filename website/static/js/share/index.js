var m = require('mithril');
var Stats = require('../share/stats.js');
var Results = require('../share/results.js');
var SideBar = require('../share/sideBar.js');
var SearchBar = require('../share/searchBar.js');


var ShareApp = {};

ShareApp.ViewModel = function() {
    var self = this;

    self.time = 0;
    self.page = 0;
    self.count = 0;
    self.results = [];
    self.query = m.prop('');
};


ShareApp.view = function(ctrl) {
    return m('.row', [
        m('.col-md-offset-1.col-md-10', [
            SearchBar.view(ctrl.searchBarController),
            Stats.view(ctrl.statsController),
            m('br'),
            m('br'),
            Results.view(ctrl.resultsController)
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
