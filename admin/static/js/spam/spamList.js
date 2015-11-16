/** Facilitate actions in the list view of spam.
 *
 **/

'use strict';

var $ = require('jquery');
var ko = require('knockout');

var SpamListModel = function() {
    var self = this;
};

var SpamListViewModel = function() {
    var self = this;
};

function SpamListManager() {
    var self = this;

    self.selector = selector;
    self.$element = $(selector);
    self.viewModel = new SpamListViewModel();
    self.init();
}

SpamListManager.prototype.init = function() {
    ko.applyBindings(this.viewModel, this.$element[0])
    this.$element.show();
};
