
var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');

/**
    * The NavbarViewModel, for OSF wide navigation.
    * @param {Object} ... 
    */
var NavbarViewModel = function() {
    var self = this;

    self.showSearch = ko.observable(false);
    self.searchCSS = ko.observable('');
    self.query = ko.observable('');
    self.showClose = true;

    self.onSearchPage = ko.computed(function() {
        var path = window.location.pathname;
        var indexOfSearch = path.indexOf('search');
        return indexOfSearch === 1;
    });


    self.toggleSearch = function(){
        if(self.showSearch()){
            self.showSearch(false);
            self.searchCSS('');            
        } else {
            self.showSearch(true);
            self.searchCSS('active');
            $('#searchPageFullBar').focus();
        }
    };

    self.help = function() {
        bootbox.dialog({
            title: 'Search help',
            message: '<h4>Queries</h4>'+
                '<p>Search uses the <a href="http://extensions.xwiki.org/xwiki/bin/view/Extension/Search+Application+Query+Syntax">Lucene search syntax</a>. ' +
                'This gives you many options, but can be very simple as well. ' +
                'Examples of valid searches include:' +
                '<ul><li><a href="/search/?q=repro*">repro*</a></li>' +
                '<li><a href="/search/?q=brian+AND+title%3Amany">brian AND title:many</a></li>' +
                '<li><a href="/search/?q=tags%3A%28psychology%29">tags:(psychology)</a></li></ul>' +
                '</p>'
        });
    };


    self.submit = function() {
        $('#searchPageFullBar').blur().focus();
       if(self.query() !== ''){
           window.location.href = '/search/?q=' + self.query();
       }
    };

};

ko.bindingHandlers.fadeVisible = {
    init: function(element, valueAccessor) {
        // Initially set the element to be instantly visible/hidden depending on the value
        var value = valueAccessor();
        $(element).toggle(ko.utils.unwrapObservable(value)); // Use "unwrapObservable" so we can handle values that may or may not be observable
    },
    update: function(element, valueAccessor) {
        // Whenever the value subsequently changes, slowly fade the element in or out
        var value = valueAccessor();
        ko.utils.unwrapObservable(value) ? $(element).fadeIn() : $(element).fadeOut();
    }
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
