'use strict';

/*global require */
var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
require('knockout.validation');
require('knockout-sortable');

var $osf = require('./osfHelpers');
var koHelpers = require('./koHelpers');
require('js/objectCreateShim');



var socialRules = {
    orcid: /orcid\.org\/([-\d]+)/i,
    researcherId: /researcherid\.com\/rid\/([-\w]+)/i,
    scholar: /scholar\.google\.com\/citations\?user=(\w+)/i,
    twitter: /twitter\.com\/(\w+)/i,
    linkedIn: /.*\/?(in\/.*|profile\/.*|pub\/.*)/i,
    impactStory: /impactstory\.org\/([\w\.-]+)/i,
    github: /github\.com\/(\w+)/i,
    researchGate: /researchgate\.net\/profile\/(\w+)/i,
    academia: /(\w+)\.academia\.edu\/(\w+)/i,
    baiduScholar: /xueshu\.baidu\.com\/scholarID\/(\w+)/i,
    url: '^(https?:\\/\\/)?'+ // protocol
            '((([a-z\\d]([a-z\\d-]*[a-z\\d])*)\\.)+[a-z]{2,}|'+ // domain name
            '((\\d{1,3}\\.){3}\\d{1,3}))'+ // OR ip (v4) address
            '(\\:\\d+)?(\\/[-a-z\\d%_.~+]*)*'+ // port and path
            '(\\?[;&a-z\\d%_.~+=-]*)?'+ // query string
            '(\\#[-a-z\\d_]*)?$'
};

var cleanByRule = function(rule) {
    return function(value) {
        var match = value.match(rule);
        if (match) {
            return match[1];
        }
        return value;
    };
};

var noop = function() {};

var SerializeMixin = function() {};

/** Serialize to a JS Object. */
SerializeMixin.prototype.serialize = function() {
    return ko.toJS(this);
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

/**
    * A mixin to handle custom date serialization on ContentModels with a separate month input.
    *
    * Months are converted to their integer equivalents on serialization
    * for db storage and back to strings on unserialization to display to the user.
    */
var DateMixin = function() {
    var self = this;
    self.ongoing = ko.observable(false);
    self.months = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
    self.endMonth = ko.observable();
    self.endYear = ko.observable();
    self.displayDate = ko.observable(' ');
    self.endView = ko.computed(function() {
        return (self.ongoing() ? 'ongoing' : self.displayDate());
    }, self);
    self.startMonth = ko.observable();
    self.startYear = ko.observable();
    self.start = ko.computed(function () {
        if (self.startMonth() && self.startYear()) {
            return new Date(self.startYear(),
                    (self.monthToInt(self.startMonth()) - 1).toString());
        } else if (self.startYear()) {
            return new Date(self.startYear(), '0', '1');
        }
    }, self).extend({
        notInFuture: true
    });
    self.end = ko.computed(function() {
        if (self.endMonth() && self.endYear()) {
            self.displayDate(self.endMonth() + ' ' + self.endYear());
            return new Date(self.endYear(),
                    (self.monthToInt(self.endMonth()) - 1).toString());
        } else if (!self.endMonth() && self.endYear()) {
            self.displayDate(self.endYear());
            var today = new Date();
            var date = new Date(self.endYear(), '11', '31');
            return today > date ? date : today;
        }
    }, self).extend({
        notInFuture:true,
        minDate: self.start
    });
    self.clearEnd = function() {
        self.endMonth('');
        self.endYear('');
        return true;
    };

    self.startYear.extend({
        required: {
            onlyIf: function() {
                return !!self.endMonth() || !!self.endYear() || self.ongoing() || !!self.startMonth();
            },
            message: 'Please enter a year for the start date.'
        },
        year: true,
        pyDate: true
    });

    self.endYear.extend({
        required: {
            onlyIf: function() {
                return !!self.endMonth() || ((!!self.startYear() || !!self.startMonth()) && !self.ongoing());
            },
            message: function() {
                if (!self.endMonth()) {
                    return 'Please enter an end date or mark as ongoing.';
                }
                else {
                    return 'Please enter a year for the end date.';
                }
            }
        },
        year: true,
        pyDate: true
    });
};

DateMixin.prototype.monthToInt = function(value) {
    var self = this;
    if (value !== undefined) {
        return self.months.indexOf(value) + 1;
    }
};

DateMixin.prototype.intToMonth = function(value) {
    var self = this;
    if (value !== undefined) {
        return self.months[(value - 1)];
    }
};

DateMixin.prototype.serialize = function() {
    var self = this;
    var content = ko.toJS(self);
    var startMonthInt = self.monthToInt(self.startMonth());
    var endMonthInt = self.monthToInt(self.endMonth());
    content.startMonth = startMonthInt;
    content.endMonth = endMonthInt;

    return content;
};

DateMixin.prototype.unserialize = function(data) {
    var self = this;
    SerializeMixin.prototype.unserialize.call(self, data);

    var startMonth = self.intToMonth(self.startMonth());
    var endMonth = self.intToMonth(self.endMonth());
    self.startMonth(startMonth);
    self.endMonth(endMonth);

    return self;
};

/** A mixin to set, keep and revert the state of a model's fields
    *
    *  A trackedProperties list attribute must defined, containing all fields
    *  to be tracked for changes. Generally, this will be any field that is
    *  filled from an external source, and will exclude calculated fields.
    * */
var TrackedMixin = function() {
    var self = this;
    self.originalValues = ko.observable();
};

/** Determine if the model has changed from its original state */
TrackedMixin.prototype.dirty = function() {
    var self = this;
    return ko.toJSON(self.trackedProperties) !== ko.toJSON(self.originalValues());
};

/** Store values in tracked fields for future use */
TrackedMixin.prototype.setOriginal = function () {
    var self = this;
    self.originalValues(ko.toJS(self.trackedProperties));
};

/** Restore fields to their values as of when setOriginal was called */
TrackedMixin.prototype.restoreOriginal = function () {
    var self = this;
    for (var i=0; i<self.trackedProperties.length; i++) {
        self.trackedProperties[i](self.originalValues()[i]);
    }
};

var BaseViewModel = function(urls, modes, preventUnsaved) {
    var self = this;

    self.urls = urls;
    self.modes = modes || ['view'];
    self.viewable = $.inArray('view', modes) >= 0;
    self.editAllowed = $.inArray('edit', self.modes) >= 0;
    self.editable = ko.observable(self.editAllowed);
    self.mode = ko.observable(self.editable() ? 'edit' : 'view');

    self.original = ko.observable();
    self.tracked = [];  // Define for each view model that inherits

    // Must be set after isValid is defined in inherited view models
    self.hasValidProperty = ko.observable(false);

    // Warn on URL change if dirty
    if (preventUnsaved !== false) {
        $(window).on('beforeunload', function() {
            if (self.dirty()) {
                return 'There are unsaved changes to your settings.';
            }
        });
    }

    // Warn on tab change if dirty
    $('body').on('show.bs.tab', function() {
        if (self.dirty()) {
            $osf.growl('There are unsaved changes to your settings.',
                    'Please save or discard your changes before switching ' +
                    'tabs.');
            return false;
        }
        return true;
    });

    this.message = ko.observable();
    this.messageClass = ko.observable();
    this.showMessages = ko.observable(false);
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

BaseViewModel.prototype.handleError = function(response) {
    var defaultMsg = 'Could not update settings';
    var msg = response.message_long || defaultMsg;
    this.changeMessage(
        msg,
        'text-danger',
        5000
    );
};

BaseViewModel.prototype.setOriginal = function() {};

BaseViewModel.prototype.dirty = function() { return false; };

BaseViewModel.prototype.fetch = function(callback) {
    var self = this;
    callback = callback || noop;
    $.ajax({
        type: 'GET',
        url: this.urls.crud,
        dataType: 'json',
        success: [this.unserialize.bind(this), self.setOriginal.bind(self), callback.bind(self)],
        error: this.handleError.bind(this, 'Could not fetch data')
    });
};

BaseViewModel.prototype.edit = function() {
    if (this.editable() && this.editAllowed) {
        this.mode('edit');
    }
};

BaseViewModel.prototype.cancel = function(data, event) {
    var self = this;
    event && event.preventDefault();

    if (this.dirty()) {
        bootbox.confirm({
            title: 'Discard changes?',
            message: 'Are you sure you want to discard your unsaved changes?',
            callback: function(confirmed) {
                if (confirmed) {
                    self.restoreOriginal();
                    if ($.inArray('view', self.modes) !== -1) {
                        self.mode('view');
                    }
                }
            },
            buttons:{
                confirm:{
                    label:'Discard',
                    className:'btn-danger'
                }
            }
        });
    } else {
        if ($.inArray('view', self.modes) !== -1) {
            self.mode('view');
        }
    }

};

BaseViewModel.prototype.submit = function() {
    if (this.hasValidProperty() && this.isValid()) {
        $osf.putJSON(
            this.urls.crud,
            this.serialize()
        ).done(
            this.handleSuccess.bind(this)
        ).done(
            this.setOriginal.bind(this)
        ).fail(
            this.handleError.bind(this)
        );
    } else {
        this.showMessages(true);
    }
};

var NameViewModel = function(urls, modes, preventUnsaved, fetchCallback) {
    var self = this;
    BaseViewModel.call(self, urls, modes, preventUnsaved);
    fetchCallback = fetchCallback || noop;
    TrackedMixin.call(self);

    self.full = koHelpers.sanitizedObservable().extend({
        trimmed: true,
        required: true
    });

    self.given = koHelpers.sanitizedObservable().extend({trimmed: true});
    self.middle = koHelpers.sanitizedObservable().extend({trimmed: true});
    self.family = koHelpers.sanitizedObservable().extend({trimmed: true});
    self.suffix = koHelpers.sanitizedObservable().extend({trimmed: true});

    self.trackedProperties = [
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

    self.impute = function(callback) {
        var cb = callback || noop;
        if (! self.hasFirst()) {
            return;
        }
        return $.ajax({
            type: 'GET',
            url: urls.impute,
            data: {
                name: self.full()
            },
            dataType: 'json',
            success: [self.unserialize.bind(self), cb],
            error: self.handleError.bind(self, 'Could not fetch names')
        });
    };

    self.initials = function(names) {
        names = $.trim(names);
        return names
            .split(/\s+/)
            .map(function(name) {
                return name[0].toUpperCase() + '.';
            })
            .filter(function(initial) {
                return initial.match(/^[a-z]/i);
            }).join(' ');
    };

    var suffix = function(suffix) {
        var suffixLower = suffix.toLowerCase();
        if ($.inArray(suffixLower, ['jr', 'sr']) !== -1) {
            suffix = suffix + '.';
            suffix = suffix.charAt(0).toUpperCase() + suffix.slice(1);
        } else if ($.inArray(suffixLower, ['ii', 'iii', 'iv', 'v']) !== -1) {
            suffix = suffix.toUpperCase();
        }
        return suffix;
    };

    self.citeApa = ko.computed(function() {
        var cite = self.family();
        var given = $.trim(self.given() + ' ' + self.middle());

        if (given) {
            cite = cite + ', ' + self.initials(given);
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
                cite = cite + ' ' + self.initials(self.middle());
            }
        }
        if (self.suffix()) {
            cite = cite + ', ' + suffix(self.suffix());
        }
        return cite;
    });

    self.fetch(fetchCallback);
};
NameViewModel.prototype = Object.create(BaseViewModel.prototype);
$.extend(NameViewModel.prototype, SerializeMixin.prototype, TrackedMixin.prototype);

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
    TrackedMixin.call(self);

    self.addons = ko.observableArray();

    self.profileWebsite = ko.observable('').extend({
        ensureHttp: true
    });

    // Start with blank profileWebsite for new users without a profile.
    self.profileWebsites = ko.observableArray([self.profileWebsite]);

    self.hasProfileWebsites = ko.pureComputed(function() {
        //Check to see if any valid profileWebsites exist
        var profileWebsites = ko.toJS(self.profileWebsites());
        for (var i=0; i<profileWebsites.length; i++) {
            if (profileWebsites[i]) {
                return true;
            }
        }
        return false;
    });

    self.hasValidWebsites = ko.pureComputed(function() {
        //Check to see if there are bad profile websites
        var profileWebsites = ko.toJS(self.profileWebsites());
        var urlexp = new RegExp(socialRules.url,'i'); // fragment locator
        for (var i=0; i<profileWebsites.length; i++) {
            if (profileWebsites[i] && !urlexp.test(profileWebsites[i])) {
                return false;
            }
        }
        return true;
    });

    self.orcid = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.orcid)}),
        self, 'orcid', 'http://orcid.org/'
    );
    self.researcherId = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.researcherId)}),
        self, 'researcherId', 'http://researcherId.com/rid/'
    );
    self.twitter = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.twitter)}),
        self, 'twitter', 'https://twitter.com/'
    );
    self.scholar = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.scholar)}),
        self, 'scholar', 'http://scholar.google.com/citations?user='
    );
    self.linkedIn = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.linkedIn)}),
        self, 'linkedIn', 'https://www.linkedin.com/'
    );
    self.impactStory = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.impactStory)}),
        self, 'impactStory', 'https://www.impactstory.org/'
    );
    self.github = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.github)}),
        self, 'github', 'https://github.com/'
    );
    self.researchGate = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.researchGate)}),
        self, 'researchGate', 'https://researchgate.net/profile/'
    );

    self.academiaInstitution = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.academia)}),
        self, 'academiaInstitution', 'https://'
    );
    self.academiaProfileID = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.academia)}),
        self, 'academiaProfileID', '.academia.edu/'
    );
    self.baiduScholar = extendLink(
        ko.observable().extend({trimmed: true, cleanup: cleanByRule(socialRules.baiduScholar)}),
        self, 'baiduScholar', 'http://xueshu.baidu.com/scholarID/'
    );

    self.trackedProperties = [
        self.profileWebsites,
        self.orcid,
        self.researcherId,
        self.twitter,
        self.scholar,
        self.linkedIn,
        self.impactStory,
        self.github,
        self.researchGate,
        self.academiaInstitution,
        self.academiaProfileID,
        self.baiduScholar
    ];

    var validated = ko.validatedObservable(self);
    self.isValid = ko.computed(function() {
        return validated.isValid();
    });
    self.hasValidProperty(true);

    self.values = ko.computed(function() {
        return [
            {label: 'ORCID', text: self.orcid(), value: self.orcid.url()},
            {label: 'ResearcherID', text: self.researcherId(), value: self.researcherId.url()},
            {label: 'Twitter', text: self.twitter(), value: self.twitter.url()},
            {label: 'GitHub', text: self.github(), value: self.github.url()},
            {label: 'LinkedIn', text: self.linkedIn(), value: self.linkedIn.url()},
            {label: 'ImpactStory', text: self.impactStory(), value: self.impactStory.url()},
            {label: 'Google Scholar', text: self.scholar(), value: self.scholar.url()},
            {label: 'ResearchGate', text: self.researchGate(), value: self.researchGate.url()},
            {label: 'Academia', text: self.academiaInstitution() + '.academia.edu/' + self.academiaProfileID(), value: self.academiaInstitution.url() + self.academiaProfileID.url()},
            {label: 'Baidu Scholar', text: self.baiduScholar(), value: self.baiduScholar.url()}
        ];
    });

    self.hasValues = ko.computed(function() {
        var values = self.values();
        if (self.hasProfileWebsites()) {
            return true;
        }
        for (var i=0; i<self.values().length; i++) {
            if (values[i].value) {
                return true;
            }
        }
        return false;
    });

    self.addWebsiteInput = function() {
        this.profileWebsites.push(ko.observable().extend({
            ensureHttp: true
        }));
    };

    self.removeWebsite = function(profileWebsite) {
        var profileWebsites = ko.toJS(self.profileWebsites());
            bootbox.confirm({
                title: 'Remove website?',
                message: 'Are you sure you want to remove this website from your profile?',
                callback: function(confirmed) {
                    if (confirmed) {
                        var idx = profileWebsites.indexOf(profileWebsite);
                        self.profileWebsites.splice(idx, 1);
                        self.submit();
                        self.changeMessage(
                            'Website removed',
                            'text-danger',
                            5000
                        );
                        if (self.profileWebsites().length === 0) {
                            self.addWebsiteInput();
                        }
                    }
                },
                buttons:{
                    confirm:{
                        label:'Remove',
                        className:'btn-danger'
                    }
                }
            });
    };

    self.fetch();
};
SocialViewModel.prototype = Object.create(BaseViewModel.prototype);
$.extend(SocialViewModel.prototype, SerializeMixin.prototype, TrackedMixin.prototype);

SocialViewModel.prototype.serialize = function() {
    var serializedData = ko.toJS(this);
    var profileWebsites = serializedData.profileWebsites;
    serializedData.profileWebsites = profileWebsites.filter(
        function (value) {
            return value;
        }
    );
    return serializedData;
};

SocialViewModel.prototype.unserialize = function(data) {
    var self = this;
    var websiteValue = [];
    $.each(data || {}, function(key, value) {
        if (ko.isObservable(self[key]) && key === 'profileWebsites') {
            if (value && value.length === 0) {
                value.push(ko.observable('').extend({
                    ensureHttp: true
                }));
            }
            for (var i = 0; i < value.length; i++) {
                websiteValue[i] = ko.observable(value[i]).extend({
                        ensureHttp: true
                });
            }
            self[key](websiteValue);
        }
        else if (ko.isObservable(self[key])) {
            self[key](value);
            // Ensure that validation errors are displayed
            self[key].notifySubscribers();
        }
    });
    return self;
};

SocialViewModel.prototype.submit = function() {
    if (!this.hasValidWebsites()) {
        this.changeMessage(
            'Please update your website',
            'text-danger',
            5000
        );
    }
    else if (this.hasValidProperty() && this.isValid()) {
        $osf.putJSON(
            this.urls.crud,
            this.serialize()
        ).done(
            this.handleSuccess.bind(this)
        ).done(
            this.setOriginal.bind(this)
        ).fail(
            this.handleError.bind(this)
        );
    } else {
        this.showMessages(true);
    }
};

var ListViewModel = function(ContentModel, urls, modes) {
    var self = this;
    BaseViewModel.call(self, urls, modes);

    self.ContentModel = ContentModel;
    self.contents = ko.observableArray();

    self.tracked = self.contents;

    self.canRemove = ko.computed(function() {
        return self.contents().length > 1;
    });

    self.institutionObjectsEmpty = ko.pureComputed(function(){
        for (var i=0; i<self.contents().length; i++) {
            if (self.contents()[i].institutionObjectEmpty()) {
                return true;
            }
        }
        return false;
    }, this);

    self.isValid = ko.computed(function() {
        for (var i=0; i<self.contents().length; i++) {
            if (! self.contents()[i].isValid()) {
                return false;
            }
        }
        return true;
    });

    self.contentsLength = ko.computed(function() {
        return self.contents().length;
    });

    self.hasValidProperty(true);

    /** Determine if any of the models in the list are dirty
    *
    * Emulates the interface of TrackedMixin.dirty
    * */
    self.dirty = function() {
        // if the length of the list has changed
        if (self.originalItems === undefined) {
            return false;
        }
        if (self.originalItems.length !== self.contents().length) {
            return true;
        }
        for (var i=0; i<self.contents().length; i++) {
            if (
                // object has changed
                self.contents()[i].dirty() ||
                // it's a different object
                self.contents()[i].originalValues() !== self.originalItems[i]
                ) { return true; }
        }
        return false;
    };

    /** Restore all items in the list to their original state
        *
        * Emulates the interface of TrackedMixin.restoreOriginal
        * */
    self.restoreOriginal = function() {
        self.contents([]);

        // We can't trust the original objects, as they're mutable
        for (var i=0; i<self.originalItems.length; i++) {

            // Reconstruct the item
            var item = new self.ContentModel(self);
            item.originalValues(self.originalItems[i]);
            item.restoreOriginal();

            self.contents.push(item);
        }
    };

    /** Store the state of all items in the list
        *
        * Emulates the interface of TrackedMixin.setOriginal
        * */
    self.setOriginal = function() {
        self.originalItems = [];
        for (var i=0; i<self.contents().length; i++) {
            self.contents()[i].setOriginal();
            self.originalItems.push(self.contents()[i].originalValues());
        }
    };
};
ListViewModel.prototype = Object.create(BaseViewModel.prototype);

ListViewModel.prototype.addContent = function() {
    if (!this.institutionObjectsEmpty() && this.isValid()) {
        this.contents.push(new this.ContentModel(this));
        this.showMessages(false);
    }
    else {
        this.showMessages(true);
    }
};

ListViewModel.prototype.removeContent = function(content) {
    // If there is more then one model, then delete it.  If there is only one, then delete it and add another
    // to preserve the fields in the view.
    var idx = this.contents().indexOf(content);
    var self = this;

    bootbox.confirm({
        title: 'Remove Institution?',
        message: 'Are you sure you want to remove this institution?',
        callback: function(confirmed) {
            if (confirmed) {
                self.contents.splice(idx, 1);
                if (!self.contentsLength()) {
                    self.contents.push(new self.ContentModel(self));
                }
                self.submit();
                self.changeMessage(
                    'Institution Removed',
                    'text-danger',
                    5000
                );
            }
        },
        buttons: {
            confirm: {
                label: 'Remove',
                className: 'btn-danger'
            }
        }
    });
};

ListViewModel.prototype.unserialize = function(data) {
    var self = this;
    if (self.editAllowed) {
        self.editable(data.editable);
    } else {
        self.editable(false);
    }
    self.contents(ko.utils.arrayMap(data.contents || [], function (each) {
        return new self.ContentModel(self).unserialize(each);
    }));

    // Ensure at least one item is visible
    if (self.mode() === 'edit') {
        if (self.contents().length === 0) {
            self.addContent();
        }
    }

    self.setOriginal();
};

ListViewModel.prototype.serialize = function() {
    var contents = [];
    if (this.contents().length !== 0 && typeof(this.contents()[0].serialize() !== undefined)) {
        for (var i=0; i < this.contents().length; i++) {
            // If the requiredField is empty, it will not save it and will delete the blank structure from the database.
            if (!this.contents()[i].institutionObjectEmpty()) {
                contents.push(this.contents()[i].serialize());
            }
            //Remove empty contents object unless there is only one
            else if (this.contents().length === 0) {
                this.contents.splice(i, 1);
            }
        }
    }
    else {
        contents = ko.toJS(this.contents);
    }
    return {contents: contents};
};

var JobViewModel = function() {
    var self = this;
    DateMixin.call(self);
    TrackedMixin.call(self);

    self.department = ko.observable('').extend({trimmed: true});
    self.title = ko.observable('').extend({trimmed: true});

    self.institution = ko.observable('').extend({
        trimmed: true,
        required: {
            onlyIf: function() {
               return !!self.department() || !!self.title();
            },
            message: 'Institution/Employer required'
        }
    });

    self.expandable = ko.computed(function() {
        return self.department().length > 1 ||
                self.title().length > 1 ||
                self.startYear() !== null;
    });

    self.expanded = ko.observable(false);

    self.toggle = function() {
        self.expanded(!self.expanded());
    };

    self.trackedProperties = [
        self.institution,
        self.department,
        self.title,
        self.startMonth,
        self.startYear,
        self.endMonth,
        self.endYear
    ];

    var validated = ko.validatedObservable(self);

    //In addition to normal knockout field checks, check to see if institution is not filled out when other fields are
    self.institutionObjectEmpty = ko.pureComputed(function() {
        return !self.institution() && !self.department() && !self.title();
    }, self);

    self.isValid = ko.computed(function() {
        return validated.isValid();
    });

};
$.extend(JobViewModel.prototype, DateMixin.prototype, TrackedMixin.prototype);

var SchoolViewModel = function() {
    var self = this;
    DateMixin.call(self);
    TrackedMixin.call(self);

    self.department = ko.observable('').extend({trimmed: true});
    self.degree = ko.observable('').extend({trimmed: true});

    self.institution = ko.observable('').extend({
        trimmed: true,
        required: {
            onlyIf: function() {
                return !!self.department() || !!self.degree();
            },
            message: 'Institution required'
        }
    });

    self.expandable = ko.computed(function() {
        return self.department().length > 1 ||
                self.degree().length > 1 ||
                self.startYear() !== null;
    });

    self.expanded = ko.observable(false);

    self.toggle = function() {
        self.expanded(!self.expanded());
    };

    self.trackedProperties = [
        self.institution,
        self.department,
        self.degree,
        self.startMonth,
        self.startYear,
        self.endMonth,
        self.endYear
    ];

    var validated = ko.validatedObservable(self);

    //In addition to normal knockout field checks, check to see if institution is not filled out when other fields are
    self.institutionObjectEmpty = ko.pureComputed(function() {
        return !self.institution() && !self.department() && !self.degree();
     });

    self.isValid = ko.computed(function() {
        return validated.isValid();
    });

};
$.extend(SchoolViewModel.prototype, DateMixin.prototype, TrackedMixin.prototype);

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
    $osf.applyBindings(this.viewModel, selector);
    window.nameModel = this.viewModel;
};

var Social = function(selector, urls, modes) {
    this.viewModel = new SocialViewModel(urls, modes);
    $osf.applyBindings(this.viewModel, selector);
    window.social = this.viewModel;
};

var Jobs = function(selector, urls, modes) {
    this.viewModel = new JobsViewModel(urls, modes);
    $osf.applyBindings(this.viewModel, selector);
    window.jobsModel = this.viewModel;
};

var Schools = function(selector, urls, modes) {
    this.viewModel = new SchoolsViewModel(urls, modes);
    $osf.applyBindings(this.viewModel, selector);
};

//making user settings panel sticky
$osf.stickIt('#usersettingspanel', 60);

/*global module */
module.exports = {
    Names: Names,
    Social: Social,
    Jobs: Jobs,
    Schools: Schools,
    // Expose private viewmodels
    _NameViewModel: NameViewModel,
    SocialViewModel: SocialViewModel,
    BaseViewModel: BaseViewModel
};

