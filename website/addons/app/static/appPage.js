var $ = require('jQuery');
require('knockout-punches');
var ko = require('knockout');
var $osf = require('osfHelpers');


// Enable knockout punches
ko.punches.enableAll();

var ViewModel = function(url) {
    var self = this;

    self.url = url;
    self.total = ko.observable(0);
    self.chosen = ko.observable();
    self.query = ko.observable('');
    self.metadata = ko.observable('');
    self.currentIndex = ko.observable(0);
    self.results = ko.observableArray([]);

    self.search = function() {
        $.ajax({
            url: self.url + '?q=' + self.query() + '&page=' + self.currentIndex(),
            type: 'GET',
            success: self.searchRecieved
        });
    };

    self.pageNext = function() {
        if (self.currentIndex() >= self.total()) return;

        self.currentIndex(self.currentIndex() + 1);
        self.search();
    }

    self.pagePrev = function() {
        if (self.currentIndex() === 0) return;

        self.currentIndex(self.currentIndex() - 1);
        self.search();
    }

    self.getMetadata = function(id) {
        $.ajax({
            url: self.url + 'metadata/' + id + '/',
            type: 'GET',
            success: self.metadataRecieved
        });
    }

    self.searchRecieved = function(data) {
        self.total(Math.ceil(data.total / 10));
        self.results(data.results);
    };

    self.metadataRecieved = function(data) {
        self.metadata('\n' + jsl.format.formatJson(JSON.stringify(data)));
    };

    self.setSelected = function(datum) {
        self.chosen(datum);
        self.getMetadata(datum._id)
    };

};

function ApplicationView(selector, url) {
    // Initialization code
    var self = this;
    self.viewModel = new ViewModel(url);
    $.osf.applyBindings(self.viewModel, selector);
}

module.exports = ApplicationView;
