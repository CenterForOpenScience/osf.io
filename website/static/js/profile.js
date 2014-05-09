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

    /*
     * Miscellaneous helpers
     */

    var printDate = function(date, dlm) {
        dlm = dlm || '-';
        var formatted = date.getFullYear() + dlm + (date.getMonth() + 1);
        if (date.getDate()) {
            formatted += dlm + date.getDate()
        }
        return formatted;
    };

    var addExtender = function(label, interceptor) {
        ko.extenders[label] = function(target, options) {
            var result = ko.computed({
                read: target,
                write: function(value) {
                    var current = target();
                    var toWrite = interceptor(value, options);
                    if (current !== toWrite) {
                        target(toWrite);
                    } else {
                        if (current !== value) {
                            target.notifySubscribers(toWrite);
                        }
                    }
                }
            }).extend({
                notify: 'always'
            });
            result(target());
            return result;
        };
    };

    addExtender('asDate', function(value, options) {
        var out;
        if (value) {
            var date;
            if (value.match(/^\d{4}$/)) {
                date = new Date(value, 0, 1);
            } else {
                date = new Date(value);
            }
            out = date != 'Invalid Date' ? printDate(date) : value;
        }
        return out;
    });

    addExtender('sanitize', function(value, options) {
        if (!! value) {
            return value.replace(/<\/?[^>]+>/g, '');
        }
        return '';
    });

    ko.validation.rules['minDate'] = {
        validator: function (val, minDate) {
            // Skip if values empty
            var uwVal = ko.utils.unwrapObservable(val);
            var uwMin = ko.utils.unwrapObservable(minDate);
            if (uwVal === null || uwMin === null) {
                return true;
            }
            // Skip if dates invalid
            var dateVal = new Date(uwVal);
            var dateMin = new Date(uwMin);
            if (dateVal == 'Invalid Date' || dateMin == 'Invalid Date') {
                return true;
            }
            // Compare dates
            return dateVal >= dateMin;
        },
        message: 'Date must be greater than or equal to {0}.'
    };

    var addRegexValidator = function(label, regex, message) {
        ko.validation.rules[label] = {
            validator: function(value, options) {
                return ko.validation.utils.isEmptyVal(value) ||
                    regex.test(ko.utils.unwrapObservable(value))
            },
            message: message
        };
    };

    addRegexValidator(
        'url',
        /^(ftp|http|https):\/\/[^ "]+$/,
        'Please enter a valid URL.'
    );

    /*
     * End helpers
     */

    var BaseViewModel = function() {
        this.message = ko.observable();
        this.messageClass = ko.observable();
    };

    BaseViewModel.prototype.unserialize = function(data) {
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

    BaseViewModel.prototype.serialize = function() {
        return ko.toJSON(this);
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
        this.changeMessage(
            'Settings updated',
            'text-success',
            5000
        );
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
            success: this.unserialize.bind(this),
            error: this.handleError.bind(this, 'Could not fetch data')
        });
    };

    BaseViewModel.prototype.submit = function() {
        if (this.isValid() === false) {
            return
        }
        $.ajax({
            type: 'PUT',
            url: this.urls.crud,
            data: this.serialize(),
            contentType: 'application/json',
            dataType: 'json',
            success: this.handleSuccess.bind(this),
            error: this.handleError.bind(this)
        });
    };

    var sanitizedObservable = function(value) {
        return ko.observable(value).extend({
            sanitize: true
        });
    };

    var NameViewModel = function(urls) {

        var self = this;
        BaseViewModel.call(self);

        self.urls = urls;

        self.full = sanitizedObservable().extend({
            required: true
        });
        self.given = sanitizedObservable();
        self.middle = sanitizedObservable();
        self.family = sanitizedObservable();
        self.suffix = sanitizedObservable();

        var validated = ko.validatedObservable(self);
        self.isValid = ko.computed(function() {
            return validated.isValid();
        });

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

    var SocialViewModel = function(urls) {

        var self = this;
        BaseViewModel.call(self);

        self.urls = urls;

        self.personal = ko.observable().extend({
            url: true
        });
        self.orcid = ko.observable();
        self.researcherId = ko.observable();
        self.twitter = ko.observable();

        var validated = ko.validatedObservable(self);
        self.isValid = ko.computed(function() {
            return validated.isValid();
        });

        self.values = ko.computed(function() {
            return [
                {key: 'Personal Site', value: self.personal()},
                {key: 'ORCID', value: self.orcid()},
                {key: 'ResearcherId', value: self.researcherId()},
                {key: 'Twitter', value: self.twitter()}
            ];
        });

        self.fetch();

    };
    SocialViewModel.prototype = Object.create(BaseViewModel.prototype);

    var ListViewModel = function(ContentModel) {

        var self = this;
        BaseViewModel.call(self);

        self.ContentModel = ContentModel;
        self.contents = ko.observableArray();

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

    };
    ListViewModel.prototype = Object.create(BaseViewModel.prototype);

    ListViewModel.prototype.unserialize = function(data) {
        var self = this;
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
    JobViewModel.prototype = Object.create(BaseViewModel.prototype);

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
    SchoolViewModel.prototype = Object.create(BaseViewModel.prototype);

    var JobsViewModel = function(urls) {

        var self = this;
        self.urls = urls;
        ListViewModel.call(self, JobViewModel);

        self.fetch();

    };
    JobsViewModel.prototype = Object.create(ListViewModel.prototype);

    var SchoolsViewModel = function(urls) {

        var self = this;
        self.urls = urls;
        ListViewModel.call(self, SchoolViewModel);

        self.fetch();

    };
    SchoolsViewModel.prototype = Object.create(ListViewModel.prototype);

    var Names = function(selector, urls) {
        this.viewModel = new NameViewModel(urls);
        $.osf.applyBindings(this.viewModel, selector);
        window.nameModel = this.viewModel;
    };

    var Social = function(selector, urls) {
        this.viewModel = new SocialViewModel(urls);
        $.osf.applyBindings(this.viewModel, selector);
    };

    var Jobs = function(selector, urls) {
        this.viewModel = new JobsViewModel(urls);
        $.osf.applyBindings(this.viewModel, selector);
        window.jobsModel = this.viewModel;
    };

    var Schools = function(selector, urls) {
        this.viewModel = new SchoolsViewModel(urls);
        $.osf.applyBindings(this.viewModel, selector);
    };

    return {
        Names: Names,
        Social: Social,
        Jobs: Jobs,
        Schools: Schools
    };

}));
