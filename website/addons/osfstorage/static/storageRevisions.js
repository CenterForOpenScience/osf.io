;(function(global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else {
        global.RevisionTable  = factory(ko, jQuery);
    }
}(this, function(ko, $) {

    'use strict';

    var Revision = function(data) {

        var self = this;

        $.extend(self, data);
        self.date = new $.osf.FormattableDate(data.date);

    };

    var RevisionsViewModel = function(url) {

        var self = this;

        self.url = url;
        self.page = 0;
        self.more = ko.observable(false);
        self.revisions = ko.observableArray([]);

    };

    RevisionsViewModel.prototype.fetch = function() {
        var self = this;
        $.getJSON(
            self.url,
            {page: self.page}
        ).done(function(response) {
            self.more(response.more);
            var revisions = ko.utils.arrayMap(response.revisions, function(item) {
                return new Revision(item);
            });
            self.revisions(self.revisions().concat(revisions));
            self.page += 1;
        });
    };

    var RevisionTable = function(selector, url) {

        var self = this;

        self.viewModel = new RevisionsViewModel(url);
        self.viewModel.fetch();
        $.osf.applyBindings(self.viewModel, selector);

    };

    return RevisionTable;

}));
