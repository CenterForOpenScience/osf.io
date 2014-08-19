;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils', 'knockoutpunches'], factory);
    } else {
        global.ApplicationView  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    // Enable knockout punches
    ko.punches.enableAll();

    var ViewModel = function(url) {
        var self = this;
        self.url = url;
        self.query = ko.observable('');
        self.chosen = ko.observable();
        self.results = ko.observableArray([]);
        self.metadata = ko.observable('');


        self.search = function() {
            $.ajax({
                url: self.url + '?q=' + self.query(),
                type: 'GET',
                success: self.searchRecieved
            });
        };

        self.getMetadata = function(id) {
            $.ajax({
                url: self.url + id,
                type: 'GET',
                success: self.metadataRecieved
            });
        }

        self.searchRecieved = function(data) {
            self.results(data.results);
        };

        self.metadataRecieved = function(data) {
            self.metadata('\n' + jsl.format.formatJson(JSON.stringify(data)));
        };

        self.setSelected = function(datum) {
            self.chosen(datum);
            self.getMetadata(datum.guid)
        };

    };

    function ApplicationView(selector, url) {
        // Initialization code
        var self = this;
        self.viewModel = new ViewModel(url);
        $.osf.applyBindings(self.viewModel, selector);
    }

    return ApplicationView

}));
