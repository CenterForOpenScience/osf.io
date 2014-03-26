/**
 * Simple knockout model and view model for rendering the revision table on the
 * file detail page.
 */
this.RevisionTable = (function(ko, $) {
    'use strict';

    function Revision(data) {
        this.rev = data.rev;
        this.modified = new FormattableDate(data.modified);
        this.download = data.download;
        this.view = data.view;
    }
    function RevisionViewModel(url) {
        var self = this;
        self.revisions = ko.observableArray([]);
        $.ajax({
            url: url,
            type: 'GET', dataType: 'json',
        })
        .done(function(response) {
            self.revisions(ko.utils.arrayMap(response.result, function(rev) {
                return new Revision(rev);
            }));
        });
    }

    function RevisionTable(selector, url) {
        $.osf.applyBindings(new RevisionViewModel(url), selector);
    }

    $script.done('revisionsTable');
    return RevisionTable;

})(ko, jQuery);
