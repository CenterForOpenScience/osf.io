this.DropboxConfigManager = (function(ko, $) {
    'use strict';


    var ViewModel = function(data) {
        var self = this;
        self.selected = ko.observable();
        self.folders = ko.observableArray(data.folders);
        self.ownerName = data.ownerName;
        self.urls = data.urls;
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');

        self.submitSettings = function() {
            $.osf.putJSON(self.urls.config, ko.toJS(self),
                function(response) {
                    self.message(response.message);
                    self.messageClass('text-success');
                    setTimeout(function() {
                        self.message('');
                    }, 2000)
                },
                function(xhr, error, textStatus) {
                    self.message('Could not change settings. Please try again later.');
                    self.messageClass('text-danger');
                }
                );
        };
    };

    // Public API
    function DropboxConfigManager(selector, url) {
        var self = this;
        self.url = url;
        self.selector = selector;
        self.$elem = $(selector);
        $.ajax({
            url: self.url,
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                var viewModel = new ViewModel(response.result);
                ko.applyBindings(viewModel, self.$elem[0]);
            },
            error: function(xhr, error, textError) {
                console.log('an error occurred getting dropbox info');
            }
        });
    }

    return DropboxConfigManager;

})(ko, jQuery);
