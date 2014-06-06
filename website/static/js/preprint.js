/**
 * Module that controls the Dropbox node settings. Includes Knockout view-model
 * for syncing data, and HGrid-folderpicker for selecting a folder.
 */



;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'knockoutpunches'], factory);
    } else if (typeof $script === 'function') {
        $script.ready(['folderPicker', 'zeroclipboard'], function() {
            global.PreprintViewModel  = factory(ko, jQuery);
            $script.done('preprint');
        });
    } else {
        global.PreprintViewModel  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    'use strict';
    ko.punches.attributeInterpolationMarkup.enable();
    /**
     * Knockout view model for the Dropbox node settings widget.
     */
    var ViewModel = function(url) {
        var self = this;

        self.downloadCurrent = ko.observable('');
        self.versions        = ko.observable([]);
        self.showPreprint    = ko.observable(false);
        self.canEdit         = ko.observable(false);
        self.response = ko.observable({}); // for debugging only
        self.uploadUrl = ko.observable(url + "upload/");

        self.updateFromData = function(data) {
            self.downloadCurrent(data.downloadCurrent);
            self.versions(data.pdf.versions);
            self.response(data);
            self.canEdit(data.pdf.permissions.edit);
            self.showPreprint(true);
        };

        self.fetchFromServer = function() {
            $.ajax({
                url: url, type: 'GET', dataType: 'json',
                success: function(response) {
                    self.updateFromData(response);
                },
                error: function(xhr, textStatus, error) {
                    console.error(textStatus); console.error(error);
                    self.changeMessage('Could not retrieve preprint data at ' +
                        'this time. Please refresh ' +
                        'the page. If the problem persists, email ' +
                        '<a href="mailto:support@cos.io">support@cos.io</a>.',
                        'text-warning');
                }
            });
        };

        // Initial fetch from server
        self.fetchFromServer();

    };

    // Public API
    function PreprintViewModel(selector, url) {
        var self = this;
        self.url = url;
        self.viewModel = new ViewModel(url);
        $.osf.applyBindings(self.viewModel, selector);
    }

    return PreprintViewModel;
}));
