var $ = require('jquery');
var ko = require('knockout');
var $osf = require('osfHelpers');
require('./citations_widget.css');

var CitationsWidgetViewModel = function() {
    var self = this;

    self.widget_api_url = nodeApiUrl + 'zotero/citations/';

    self.error = ko.observable();
    self.name = ko.observable();
    self.citations = ko.observableArray();

    self.updateList = function() {
        var request = $.get(self.widget_api_url);
        request.done(function(data){
            console.log('loaded');
            console.log(data);
            self.name(data.name);
            self.citations(data.citations);
        });
        request.fail(function() {
           self.error('Loading failed');
        });
    };
    self.updateList();
};


////////////////
// Public API //
////////////////

function CitationsWidget (selector) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.viewModel = new CitationsWidgetViewModel();
    self.init();
}

CitationsWidget.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
};

//module.exports = ZoteroSettings;
new CitationsWidget('#zoteroWidget');
