'use strict';

var ko = require('knockout');

var makeExtender = function(interceptor) {
    return function(target, options) {
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

var addExtender = function(label, interceptor) {
    ko.extenders[label] = makeExtender(interceptor);
};

var makeRegexValidator = function(regex, message, match) {
    match = match || match === undefined;
    return {
        validator: function(value) {
            if (ko.validation.utils.isEmptyVal(value)) {
                return true;
            }
            return match === regex.test(ko.utils.unwrapObservable(value));
        },
        message: message
    };
};

addExtender('cleanup', function(value, cleaner) {
    return !!value ? cleaner(value) : '';
});

addExtender('ensureHttp', function(value) {
    if (!value || value.search(/^https?:\/\//i) === 0) {
        return value;
    }
    return 'http://' + value;
});

var sanitize = function(value) {
    return value.replace(/<\/?[^>]+>/g, '');
};

var sanitizedObservable = function(value) {
    return ko.observable(value).extend({
        cleanup: sanitize
    });
};

// Add custom validators

ko.validation.rules.minDate = {
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
        if (dateVal.toString() === 'Invalid Date' || dateMin.toString() === 'Invalid Date') {
            return true;
        }
        // Check if end date is ongoing
        if (uwVal === 'ongoing') {
            return true;
        }
        // Compare dates
        return dateVal >= dateMin;
    },
    message: 'End date must be greater than or equal to the start date.'
};

ko.validation.rules.pyDate = {
    validator: function (val) {
        // Skip if values empty
        var uwVal = ko.utils.unwrapObservable(val);
        if (uwVal === null) {
            return true;
        }
        // Skip if dates invalid
        var dateVal = new Date(uwVal);
        if (dateVal.toString() === 'Invalid Date') {
            return true;
        }
        // Compare years
        return parseInt(uwVal) >= 1900;
    },
    message: 'Date must be greater than or equal to 1900.'
};

ko.validation.rules.notInFuture = {
    validator: function (val) {
        // Skip if values empty
        var uwVal = ko.utils.unwrapObservable(val);
        if (uwVal === null || uwVal === undefined) {
            return true;
        }

        //Skip if dates invalid
        var dateVal = new Date(uwVal);

        if (dateVal.toString() === 'Invalid Date') {
            return true;
        }
        // Compare dates
        var now = new Date();
        return dateVal <= now;

    },
    message: 'Please enter a date prior to the current date.'
};


ko.validation.rules.year = makeRegexValidator(
    new RegExp('^\\d{4}$'),
    'Please enter a valid year.'
);


ko.validation.rules.url = makeRegexValidator(
    new RegExp(
        '^(?:http|ftp)s?://' +
            '(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\\.)+(?:[A-Z]{2,6}\\.?|[A-Z0-9-]{2,}\\.?)|' +
            'localhost|' +
            '\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}|' +
            '\\[?[A-F0-9]*:[A-F0-9:]+\\]?)' +
            '(?::\\d+)?' +
            '(?:/?|[/?]\\S+)$',
        'i'
    ),
    'Please enter a valid URL.'
);

// Expose public utilities

module.exports = {
    makeExtender: makeExtender,
    addExtender: addExtender,
    makeRegexValidator: makeRegexValidator,
    sanitizedObservable: sanitizedObservable
};
