var $ = require('jquery');
var ko = require('knockout');
var $osf = require('osfHelpers');

var CitationsWidgetViewModel = function() {
    var self = this;

    self.temp = ko.observable('Working');
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

//module.exports = MendeleySettings;
new CitationsWidget('#mendeleyWidget');
