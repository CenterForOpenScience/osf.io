/**
 * Simple knockout model and view model for rendering the commit history on the
 * file detail page.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else {
        global.CommitTable = factory(ko, jQuery);
    }
}(this, function(ko, $) {

    'use strict';

    function Commit(data) {
        $.extend(this, data);
        this.modified = new $.osf.FormattableDate(data.date);
    }

    function CommitViewModel(url) {

        var self = this;

        self.url = url;
        self.sha = ko.observable();
        self.commits = ko.observableArray([]);

        self.fetch = function() {
            $.getJSON(
                self.url,
                function(resp) {
                    self.sha(resp.sha);
                    self.commits(ko.utils.arrayMap(resp.commits, function(commit) {
                        return new Commit(commit);
                    }));
                }
            )
        }

    }
    // Public API
    function CommitTable(selector, url) {
        this.viewModel = new CommitViewModel(url);
        this.viewModel.fetch();
        $.osf.applyBindings(this.viewModel, selector);
    }

    return CommitTable;

}));
