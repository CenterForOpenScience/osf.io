/*
View model for API application registry and management
 */

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
require('knockout.validation');
require('knockout.punches');
ko.punches.enableAll();
require('knockout-sortable');

var $osf = require('./osfHelpers');
var koHelpers = require('./koHelpers');
require('js/objectCreateShim');



var ApplicationsViewModel = function(urls, modes) {
    var self = this;
    //ListViewModel.call(self, SchoolViewModel, urls, modes);

    self.urls = urls;

    self.userAppsList = ko.observableArray([]);

    self.loadUrls = function(){
    };
    //self.fetch();
};


var Applications = function(selector, urls, modes) {
    this.viewModel = new ApplicationsViewModel(urls, modes);
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    Applications: Applications
};
