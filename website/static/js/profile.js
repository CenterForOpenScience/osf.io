/**
 *
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'knockout'], factory);
    } else {
        global.Profile = factory(jQuery, ko);
        $script.done('profile');
    }
}(this, function($, ko){

    'use strict';

    var SubViewModel = function() {};

    SubViewModel.prototype.unserialize = function(data) {
        var self = this;
        $.each(data || {}, function(key, value) {
            if (ko.isObservable(self[key])) {
                self[key](value);
            }
        });
        return self;
    };

    SubViewModel.prototype.serialize = function() {
//        return ko.toJS(this);
    };

    var NameViewModel = function($root) {

        var self = this;

        self.full = ko.observable('');
        self.given = ko.observable('');
        self.middle = ko.observable('');
        self.family = ko.observable('');
        self.suffix = ko.observable('');

        self.citations = ko.observable();

        self.parseNames = function() {
            $.ajax({
                type: 'GET',
                url: '',
                data: {
                    full: self.full()
                },
                dataType: 'json',
                success: self.unserialize,
                error: $root.handleError
            });
        };

        self.updateCitations = function() {
            $.ajax({
                type: 'GET',
                url: '',
                data: self.serialize(),
                dataType: 'json',
                success: self.unserialize,
                error: $root.handleError
            });
        };

        self.watchNames = ko.computed(function() {
            self.updateCitations();
        }).extend({
            rateLimit: 500
        });

    };
    NameViewModel.prototype = new SubViewModel();

    var SocialViewModel = function($root) {

        var self = this;

        self.personal = ko.observable('');
        self.orcid = ko.observable('');
        self.researcherId = ko.observable('');
        self.twitter = ko.observable('');

    };
    SocialViewModel.prototype = new SubViewModel();

    var HistoryViewModel = function($root) {

        var self = this;

        self.institution = ko.observable('');
        self.department = ko.observable('');
        self.title = ko.observable('');

        self.startDate = ko.observable();
        self.endDate = ko.observable();

        self.remove = function() {
            $root.history.splice($root.history().indexOf(self), 1);
        };

    };
    HistoryViewModel.prototype = new SubViewModel();

    var ViewModel = function(getUrl, putUrl) {

        var self = this;

        self.names = new NameViewModel(self);
        self.social = new SocialViewModel(self);
        self.history = ko.observableArray([]);

        self.unserialize = function(data) {
            self.names.unserialize(data.names);
            self.social.unserialize(data.social);
            self.history(ko.utils.arrayMap(data.history || [], function(history) {
                return new HistoryViewModel(self).unserialize(history);
            }));
        };

        self.addHistory = function() {
            self.history.push(new HistoryViewModel(self));
        };

        self.serialize = function() {
            return ko.toJS(self);
        };

        self.submit = function() {
            $.ajax({
                type: 'PUT',
                url: putUrl,
                data: JSON.stringify(self.serialize()),
                contentType: 'application/json',
                dataType: 'json',
                success: handleSuccess,
                error: handleError
            });
        };

        var handleSuccess = function() {

        };

        var handleError = function() {

        };

        $.ajax({
            type: 'GET',
            url: getUrl,
            dataType: 'json',
            success: self.unserialize,
            error: handleError
        });

    };

    var Profile = function(selector, fetchUrl, submitUrl) {
        this.viewModel = new ViewModel(fetchUrl, submitUrl);
        $.osf.applyBindings(this.viewModel, selector);
        window.viewModel = this.viewModel;
    };

    return Profile;

}));
