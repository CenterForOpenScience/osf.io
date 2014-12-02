;(function(global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else {
        global.FolderCreator = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    'use strict';

    function FolderCreatorViewModel(url) {
        var self = this;
        self.url = url;

        self.title = ko.observable('').extend({
            maxLength: 200
        });

        self.formErrorText = ko.observable('');


        self.createFolder = function () {
            $.osf.postJSON(
                self.url,
                self.serialize()
            ).done(
                self.createSuccess
            ).fail(
                self.createFailure
            );
        };

        self.createSuccess = function (data) {
            window.location = data.projectUrl;
        };

        self.createFailure = function () {
            $.osf.growl('Could not create a new folder.', 'Please try again. If the problem persists, email <a href="mailto:support@osf.io.">support@osf.io</a>');
        };

        self.serialize = function () {
            return {
                title: self.title()
            };
        };

        self.verifyTitle = function () {
            if (self.title() === ''){
                self.formErrorText('We need a title for your folder.');
            } else {
                self.createFolder();
            }

        };
    }

    function FolderCreator(selector, url) {
        var viewModel = new FolderCreatorViewModel(url);
        // Uncomment for debugging
        // window.viewModel = viewModel;
        $.osf.applyBindings(viewModel, selector);
    }

    return FolderCreator;
}));
