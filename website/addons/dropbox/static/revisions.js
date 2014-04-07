/**
 * Simple knockout model and view model for rendering the revision table on the
 * file detail page.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else {
        global.RevisionTable  = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    'use strict';

    function Revision(data) {
        this.rev = data.rev;
        this.modified = new $.osf.FormattableDate(data.modified);
        this.download = data.download;
        this.view = data.view;
    }
    function RevisionViewModel(url) {
        var self = this;
        self.revisions = ko.observableArray([]);
        // Get current revision from URL param
        self.currentRevision = $.osf.urlParams().rev;
        // Date when this project was registered, or null if not a registration
        // Note: Registering Dropbox content is disabled for now; leaving
        // this code here in case we enable registrations later on.
        // @jmcarp
        self.registered = ko.observable(null);
        $.ajax({
            url: url, type: 'GET', dataType: 'json',
            // On success, update the revisions observable
            success: function(response) {
                if (response.registered) {
                    self.registered(new Date(response.registered));
                }
                self.revisions(ko.utils.arrayMap(response.result, function(rev) {
                    return new Revision(rev);
                }));
            }
        });
    }
    // Public API
    function RevisionTable(selector, url) {
        this.viewModel = new RevisionViewModel(url);
        $.osf.applyBindings(this.viewModel, selector);
    }

    return RevisionTable;
}));
