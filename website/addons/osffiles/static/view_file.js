/**
 * Simple knockout model and view model for rendering the revision table on the
 * file detail page.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else {
        global.VersionTable  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    'use strict';
    ko.punches.enableAll();
    ko.punches.attributeInterpolationMarkup.enable();


    function Version(data) {
        this.version_number = data.version_number;
        this.modified_date = new $.osf.FormattableDate(data.modified_date);
        this.downloads = data.downloads;
        this.download_url = data.download_url;
        this.committer_name = data.committer_name;
        this.committer_url = data.committer_url;
        this.view = data.view;
    }
    function VersionViewModel(url) {
        var self = this;
        self.versions = ko.observable([]);

        self.file_name = ko.observable(null);
        self.files_url = ko.observable(null);
        self.node_title = ko.observable(null);


        // Date when this project was registered, or null if not a registration
        // TODO: should I populate this? (@mambocab)
        self.registered = ko.observable(null);
        $.ajax({
            url: url, type: 'GET', dataType: 'json',
            // On success, update the revisions observable
            success: function(response) {
                self.versions(ko.utils.arrayMap(response.versions, function(rev) {
                    return new Version(rev);
                }));
                self.node_title(response.node_title);
                self.file_name(response.file_name);
                self.node_title(response.node_title);
            }
        });
    }
    // Public API
    function VersionTable(selector, url) {
        this.viewModel = new VersionViewModel(url);
        $.osf.applyBindings(this.viewModel, selector);
    }

    return VersionTable;
}));
