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
        self.latest_download_url = ko.observable(null);
        self.api_url = ko.observable(null);
        self.files_page_url = ko.observable(null);

        // Date when this project was registered, or null if not a registration
        // TODO: should I populate this? (@mambocab)
        self.registered = ko.observable(false);

        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function(response) {
            self.versions(ko.utils.arrayMap(response.versions, function(rev) {
                return new Version(rev);
            }));
            self.node_title(response.node_title);
            self.file_name(response.file_name);
            self.node_title(response.node_title);
            self.latest_download_url(response.urls.latest.download);
            self.api_url(response.urls.api);
            self.files_page_url(response.urls.files);
            self.registered(response.registered);
        }).fail(
            $.osf.handleJSONError
        );

        self.deleteFile = function(){
            bootbox.confirm({
                title: 'Delete file from OSF Storage?',
                message: 'Are you sure you want to delete <strong>' +
                      self.file_name() + '</strong>? It will not be recoverable.',
                callback: function(result) {
                    if (result) {
                        $('#deletingAlert').addClass('in');
                        var request = $.ajax({
                            type: 'DELETE',
                            url: self.api_url()
                        });
                        request.done(function() {
                            window.location = self.files_page_url();
                        });
                        request.fail(function( jqXHR, textStatus ) {
                            $('#deletingAlert').removeClass('in');
                            $.osf.growl( 'Could not delete', textStatus );
                        });
                    }
                }
            });
        };
    }
    // Public API
    function VersionTable(selector, url) {
        this.viewModel = new VersionViewModel(url);
        $.osf.applyBindings(this.viewModel, selector);
    }

    return VersionTable;
}));
