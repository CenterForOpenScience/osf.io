this.DropboxConfigHelper = (function(ko, $) {
    'use strict';

    var ViewModel = function(folders) {
        var self = this;
        self.selected = ko.observable();
        self.folders = ko.observableArray(folders);

        self.submitSettings = function() {
            console.log('Sending data..');
            console.log(self.selected());
        };
    };

    // Public API
    function DropboxConfigHelper(selector, folders) {
        var self = this;
        self.selector = selector;
        self.$elem = $(selector);
        self.viewModel = new ViewModel(folders);
        this.init();
    }

    DropboxConfigHelper.prototype.init = function() {
        ko.applyBindings(this.viewModel, this.$elem[0]);
    };

    return DropboxConfigHelper;

})(ko, jQuery);

//TODO Template ify
//Dropdown all
