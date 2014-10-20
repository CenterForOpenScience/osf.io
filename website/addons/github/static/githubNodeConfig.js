
/**
 * Module that controls the GitHub node settings. Includes Knockout view-model
 * for syncing data, and HGrid-folderpicker for selecting a folder.
 */



;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery',
                'zeroclipboard', 'osfutils', 'knockoutpunches'], factory);
    } else if (typeof $script === 'function') {
        $script.ready(['folderPicker', 'zeroclipboard'], function() {

            global.GithubNodeConfig  = factory(ko, jQuery, ZeroClipboard);
            $script.done('githubNodeConfig');
        });
    } else {
        global.GithubNodeConfig  = factory(ko, jQuery, ZeroClipboard);
    }
}(this, function(ko, $, FolderPicker, ZeroClipboard) {
    'use strict';
    ko.punches.attributeInterpolationMarkup.enable();
    /**
     * Knockout view model for the Github node settings widget.
     */
    var ViewModel = function(url, selector, folderPicker) {
        var self = this;
        self.selector = selector;
        // Auth information
        self.nodeHasAuth = ko.observable(false);
        // whether current user is authorizer of the addon
        self.userIsOwner = ko.observable(false);
        // whether current user has an auth token
        self.userHasAuth = ko.observable(false);
        // Currently linked folder, an Object of the form {name: ..., path: ...}
        self.folder = ko.observable({name: null, path: null});
        self.ownerName = ko.observable('');
        self.urls = ko.observable({});


        /**
         * Update the view model from data returned from the server.
         */
        self.updateFromData = function(data) {
            self.ownerName(data.ownerName);
            self.nodeHasAuth(data.nodeHasAuth);
            self.userIsOwner(data.userIsOwner);
            self.userHasAuth(data.userHasAuth);
            // Make sure folder has name and path properties defined
            self.folder(data.folder || {name: null, path: null});
            self.urls(data.urls);
        };

        self.fetchFromServer = function() {
            $.ajax({
                url: url, type: 'GET', dataType: 'json',
                success: function(response) {
                    self.updateFromData(response.result);
                    self.loadedSettings(true);
                },
                error: function(xhr, textStatus, error) {
                    self.changeMessage('Could not retrieve Github settings at ' +
                        'this time. Please refresh ' +
                        'the page. If the problem persists, email ' +
                        '<a href="mailto:support@osf.io">support@osf.io</a>.',
                        'text-warning');
                    Raven.captureMessage('Could not GET Github settings', {
                        url: url,
                        textStatus: textStatus,
                        error: error
                    });
                }
            });
        };

        self.fetchFromServer();

    }
    // Public API
    function GithubNodeConfig(selector, url, folderPicker) {
        var self = this;
        self.url = url;
        self.folderPicker = folderPicker;
        self.viewModel = new ViewModel(url, selector, folderPicker);
        $.osf.applyBindings(self.viewModel, selector);
        window.bobob = self.viewModel;
    }

    return GithubNodeConfig;
}));
