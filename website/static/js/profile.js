/**
 *
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'knockout'], factory);
    } else {
        global.profile = factory(jQuery, ko);
        $script.done('profile');
    }
}(this, function($, ko){

    'use strict';

    var socialRules = {
        orcid: /orcid\.org\/([-\d]+)/i,
        researcherId: /researcherid\.com\/rid\/([-\w]+)/i,
        scholar: /scholar\.google\.com\/citations\?user=(\w+)/i,
        twitter: /twitter\.com\/(\w+)/i,
        linkedIn: /linkedin\.com\/profile\/view\?id=(\d+)/i,
        github: /github\.com\/(\w+)/i
    };

    var cleanByRule = function(rule) {
        return function(value) {
            var match = value.match(rule);
            if (match) {
                return match[1];
            }
            return value;
        }
    };

    var SerializeMixin = function() {};

    SerializeMixin.prototype.serialize = function() {
        return ko.toJSON(this);
    };

    SerializeMixin.prototype.unserialize = function(data) {
        var self = this;
        $.each(data || {}, function(key, value) {
            if (ko.isObservable(self[key])) {
                self[key](value);
                // Ensure that validation errors are displayed
                self[key].notifySubscribers();
            }
        });
        return self;
    };

    var BaseViewModel = function(urls, modes) {

        var self = this;

        self.urls = urls;
        self.modes = modes || ['view'];
        self.viewable = $.inArray('view', modes) >= 0;
        self.editable = ko.observable(false);
        self.mode = ko.observable(self.viewable ? 'view' : 'edit');

        self.original = ko.observable();
        self.tracked = [];  // Define for each view model that inherits

        self.setOriginal = function() {
            self.original(ko.toJSON(self.tracked));
        };

        self.dirty = ko.computed(function() {
            return self.mode() === 'edit' && ko.toJSON(self.tracked) !== self.original();
        });

        // Must be set after isValid is defined in inherited view models
        // Necessary for enableSubmit to subscribe to isValid
        self.hasValidProperty = ko.observable(false);

        self.enableSubmit = ko.computed(function() {
            return self.hasValidProperty() && self.isValid() && self.dirty();
        });

        // Warn on URL change if dirty
        $(window).on('beforeunload', function() {
            if (self.dirty()) {
                return 'There are unsaved changes to your settings.';
            }
        });

        // Warn on tab change if dirty
        $('body').on('show.bs.tab', function() {
            if (self.dirty()) {
                bootbox.alert('There are unsaved changes to your settings. ' +
                    'Please save or discard your changes before switching ' +
                    'tabs.');
                return false;
            }
            return true;
        });

        this.message = ko.observable();
        this.messageClass = ko.observable();

    };

    BaseViewModel.prototype.changeMessage = function(text, css, timeout) {
        var self = this;
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(
                function() {
                    self.message('');
                    self.messageClass('text-info');
                },
                timeout
            );
        }
    };

    BaseViewModel.prototype.handleSuccess = function() {
        if ($.inArray('view', this.modes) >= 0) {
            this.mode('view');
        } else {
            this.changeMessage(
                'Settings updated',
                'text-success',
                5000
            );
        }
    };

    BaseViewModel.prototype.handleError = function() {
        this.changeMessage(
            'Could not update settings',
            'text-danger',
            5000
        );
    };

    BaseViewModel.prototype.fetch = function() {
        $.ajax({
            type: 'GET',
            url: this.urls.crud,
            dataType: 'json',
            success: [this.unserialize.bind(this), this.setOriginal],
            error: this.handleError.bind(this, 'Could not fetch data')
        });
    };

    BaseViewModel.prototype.edit = function() {
        if (this.editable()) {
            this.mode('edit');
        }
    };

    BaseViewModel.prototype.cancel = function(data, event) {
        event && event.preventDefault();
        this.mode('view');
    };

    BaseViewModel.prototype.submit = function() {
        if (this.enableSubmit() === false) {
            return
        }
        $.ajax({
            type: 'PUT',
            url: this.urls.crud,
            data: this.serialize(),
            contentType: 'application/json',
            dataType: 'json',
            success: [this.handleSuccess.bind(this), this.setOriginal],
            error: this.handleError.bind(this)
        });
    };

    var NameViewModel = function(urls, modes) {

        var self = this;
        BaseViewModel.call(self, urls, modes);

        self.full = $.osf.ko.sanitizedObservable().extend({
            required: true
        });
        self.given = $.osf.ko.sanitizedObservable();
        self.middle = $.osf.ko.sanitizedObservable();
        self.family = $.osf.ko.sanitizedObservable();
        self.suffix = $.osf.ko.sanitizedObservable();

        self.tracked = [
            self.full,
            self.given,
            self.middle,
            self.family,
            self.suffix
        ];

        var validated = ko.validatedObservable(self);
        self.isValid = ko.computed(function() {
            return validated.isValid();
        });
        self.hasValidProperty(true);

        self.citations = ko.observable();

        self.hasFirst = ko.computed(function() {
            return !! self.full();
        });

        self.impute = function() {
            if (! self.hasFirst()) {
                return
            }
            $.ajax({
                type: 'GET',
                url: urls.impute,
                data: {
                    name: self.full()
                },
                dataType: 'json',
                success: self.unserialize.bind(self),
                error: self.handleError.bind(self, 'Could not fetch names')
            });
        };

        var initials = function(names) {
            return names
                .split(' ')
                .map(function(name) {
                    return name[0].toUpperCase() + '.';
                })
                .filter(function(initial) {
                    return initial.match(/^[a-z]/i);
                }).join(' ');
        };

        var suffix = function(suffix) {
            var suffixLower = suffix.toLowerCase();
            if ($.inArray(suffixLower, ['jr', 'sr']) != -1) {
                suffix = suffix + '.';
                suffix = suffix.charAt(0).toUpperCase() + suffix.slice(1);
            } else if ($.inArray(suffixLower, ['ii', 'iii', 'iv', 'v']) != -1) {
                suffix = suffix.toUpperCase();
            }
            return suffix;
        };

        self.citeApa = ko.computed(function() {
            var cite = self.family();
            var given = $.trim(self.given() + ' ' + self.middle());
            if (given) {
                cite = cite + ', ' + initials(given);
            }
            if (self.suffix()) {
                cite = cite + ', ' + suffix(self.suffix());
            }
            return cite;
        });

        self.citeMla = ko.computed(function() {
            var cite = self.family();
            if (self.given()) {
                cite = cite + ', ' + self.given();
                if (self.middle()) {
                    cite = cite + ' ' + initials(self.middle());
                }
            }
            if (self.suffix()) {
                cite = cite + ', ' + suffix(self.suffix());
            }
            return cite;
        });

        self.fetch();

    };
    NameViewModel.prototype = Object.create(BaseViewModel.prototype);
    $.extend(NameViewModel.prototype, SerializeMixin.prototype);

    /*
     * Custom observable for use with external services.
     */
    var extendLink = function(obs, $parent, label, baseUrl) {

        obs.url = ko.computed(function($data, event) {
            // Prevent click from submitting form
            event && event.preventDefault();
            if (obs()) {
                return baseUrl ? baseUrl + obs() : obs();
            }
            return '';
        });

        obs.hasAddon = ko.computed(function() {
            return $parent.addons()[label] !== undefined;
        });

        obs.importAddon = function() {
            if (obs.hasAddon()) {
                obs($parent.addons()[label]);
            }
        };

        return obs;

    };

    var SocialViewModel = function(urls, modes) {

        var self = this;
        BaseViewModel.call(self, urls, modes);

        self.addons = ko.observableArray();

        self.personal = extendLink(
            // Note: Apply extenders in reverse order so that `ensureHttp` is
            // applied before `url`.
            ko.observable().extend({
                url: true,
                ensureHttp: true
            }),
            self, 'personal'
        );
        self.orcid = extendLink(
            ko.observable().extend({cleanup: cleanByRule(socialRules.orcid)}),
            self, 'orcid', 'http://orcid.org/'
        );
        self.researcherId = extendLink(
            ko.observable().extend({cleanup: cleanByRule(socialRules.researcherId)}),
            self, 'researcherId', 'http://researcherId.com/'
        );
        self.twitter = extendLink(
            ko.observable().extend({cleanup: cleanByRule(socialRules.twitter)}),
            self, 'twitter', 'https://twitter.com/'
        );
        self.scholar = extendLink(
            ko.observable().extend({cleanup: cleanByRule(socialRules.scholar)}),
            self, 'scholar', 'http://scholar.google.com/citations?user='
        );
        self.linkedIn = extendLink(
            ko.observable().extend({cleanup: cleanByRule(socialRules.linkedIn)}),
            self, 'linkedIn', 'https://www.linkedin.com/profile/view?id='
        );
        self.github = extendLink(
            ko.observable().extend({cleanup: cleanByRule(socialRules.github)}),
            self, 'github', 'https://github.com/'
        );

        self.tracked = [
            self.personal,
            self.orcid,
            self.researcherId,
            self.twitter,
            self.scholar,
            self.linkedIn,
            self.github
        ];

        var validated = ko.validatedObservable(self);
        self.isValid = ko.computed(function() {
            return validated.isValid();
        });
        self.hasValidProperty(true);

        self.values = ko.computed(function() {
            return [
                {label: 'Personal Site', text: self.personal(), value: self.personal.url()},
                {label: 'ORCID', text: self.orcid(), value: self.orcid.url()},
                {label: 'ResearcherId', text: self.researcherId(), value: self.researcherId.url()},
                {label: 'Twitter', text: self.twitter(), value: self.twitter.url()},
                {label: 'GitHub', text: self.github(), value: self.github.url()},
                {label: 'LinkedIn', text: self.linkedIn(), value: self.linkedIn.url()},
                {label: 'Google Scholar', text: self.scholar(), value: self.scholar.url()}
            ];
        });

        self.hasValues = ko.computed(function() {
            var values = self.values();
            for (var i=0; i<self.values().length; i++) {
                if (values[i].value) {
                    return true;
                }
            }
            return false;
        });

        self.fetch();

    };
    SocialViewModel.prototype = Object.create(BaseViewModel.prototype);
    $.extend(SocialViewModel.prototype, SerializeMixin.prototype);

    var ListViewModel = function(ContentModel, urls, modes) {

        var self = this;
        BaseViewModel.call(self, urls, modes);

        self.ContentModel = ContentModel;
        self.contents = ko.observableArray();

        self.tracked = self.contents;

        self.canRemove = ko.computed(function() {
            return self.contents().length > 1;
        });

        self.isValid = ko.computed(function() {
            for (var i=0; i<self.contents().length; i++) {
                if (! self.contents()[i].isValid()) {
                    return false;
                }
            }
            return true;
        });
        self.hasMultiple = ko.computed(function() {
            return self.contents().length > 1;
        });
        self.hasValidProperty(true);

    };
    ListViewModel.prototype = Object.create(BaseViewModel.prototype);

    ListViewModel.prototype.unserialize = function(data) {
        var self = this;
        self.editable(data.editable);
        self.contents(ko.utils.arrayMap(data.contents || [], function(each) {
            return new self.ContentModel(self).unserialize(each);
        }));
        // Ensure at least one item is visible
        if (self.contents().length == 0) {
            self.addContent();
        }
    };

    ListViewModel.prototype.serialize = function() {
        return JSON.stringify({
            contents: ko.toJS(this.contents)
        });
    };

    ListViewModel.prototype.addContent = function() {
        this.contents.push(new this.ContentModel(this));
    };

    ListViewModel.prototype.removeContent = function(content) {
        var idx = this.contents().indexOf(content);
        this.contents.splice(idx, 1);
    };

    var JobViewModel = function() {

        var self = this;

        self.institution = ko.observable('').extend({
            required: true
        });
        self.department = ko.observable('');
        self.title = ko.observable('');

        self.start = ko.observable().extend({
            asDate: true,
            date: true
        });
        self.end = ko.observable().extend({
            asDate: true,
            date: true,
            minDate: self.start
        });

        var validated = ko.validatedObservable(self);
        self.isValid = ko.computed(function() {
            return validated.isValid();
        });

    };
    $.extend(JobViewModel.prototype, SerializeMixin.prototype);

    var SchoolViewModel = function() {

        var self = this;

        self.institution = ko.observable('').extend({
            required: true
        });
        self.department = ko.observable('');
        self.degree = ko.observable('');

        self.start = ko.observable().extend({
            asDate: true,
            date: true
        });
        self.end = ko.observable().extend({
            asDate: true,
            date: true,
            minDate: self.start
        });

        var validated = ko.validatedObservable(self);
        self.isValid = ko.computed(function() {
            return validated.isValid();
        });

    };
    $.extend(SchoolViewModel.prototype, SerializeMixin.prototype);

    var JobsViewModel = function(urls, modes) {

        var self = this;
        ListViewModel.call(self, JobViewModel, urls, modes);

        self.fetch();

    };
    JobsViewModel.prototype = Object.create(ListViewModel.prototype);

    var SchoolsViewModel = function(urls, modes) {

        var self = this;
        ListViewModel.call(self, SchoolViewModel, urls, modes);

        self.fetch();

    };
    SchoolsViewModel.prototype = Object.create(ListViewModel.prototype);

    var Names = function(selector, urls, modes) {
        this.viewModel = new NameViewModel(urls, modes);
        $.osf.applyBindings(this.viewModel, selector);
        window.nameModel = this.viewModel;
    };

    var Social = function(selector, urls, modes) {
        this.viewModel = new SocialViewModel(urls, modes);
        $.osf.applyBindings(this.viewModel, selector);
        window.social = this.viewModel;
    };

    var Jobs = function(selector, urls, modes) {
        this.viewModel = new JobsViewModel(urls, modes);
        $.osf.applyBindings(this.viewModel, selector);
        window.jobsModel = this.viewModel;
    };

    var Schools = function(selector, urls, modes) {
        this.viewModel = new SchoolsViewModel(urls, modes);
        $.osf.applyBindings(this.viewModel, selector);
    };

    return {
        Names: Names,
        Social: Social,
        Jobs: Jobs,
        Schools: Schools
    };

}));
