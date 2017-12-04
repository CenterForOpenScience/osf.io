var $ = require('jquery');
var ko = require('knockout');
var $osf = require('js/osfHelpers');

/**
    * The NavbarViewModel, for OSF wide navigation.
    * @param {Object} ...
    */
var NavbarViewModel = function() {
    var self = this;
    self.trackClick = function(label){
        if (label === 'Dropdown Arrow'){
            $('.navbar-collapse').collapse('hide');
        }
        return $osf.trackClick('link', 'click', 'Navbar - ' + label);
    };
};

function NavbarControl (selector, data, options) {
    var self = this;
    self.selector = selector;
    self.$element = $(self.selector);
    self.data = data;
    self.viewModel = new NavbarViewModel(self.data);
    self.options = $.extend({}, {}, options);
    self.init();
}

NavbarControl.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
};


module.exports = NavbarControl;
