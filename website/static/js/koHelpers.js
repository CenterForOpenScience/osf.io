////////////////////////////
// Site-wide JS utilities //
////////////////////////////
(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'knockout'], factory);
    } else {
        factory(jQuery, global.ko);
    }
}(this, function($, ko) {
    'use strict';

    // Namespace to put utility functions on
    $.osf.ko = {};

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
            validator: function(value, options) {
                if (ko.validation.utils.isEmptyVal(value))
                    return true;
                return match === regex.test(ko.utils.unwrapObservable(value));
            },
            message: message
        };
    };

    var printDate = function(date, dlm) {
        dlm = dlm || '-';
        var formatted = date.getFullYear() + dlm + (date.getMonth() + 1);
        if (date.getDate()) {
            formatted += dlm + date.getDate()
        }
        return formatted;
    };

    addExtender('asDate', function(value, options) {
        var out;
        if (value) {
            var date;
            if (value.match(/^\d{4}$/)) {
                date = new Date(value, 0, 1);
            } else {
                date = moment(value).toDate();
            }
            out = date != 'Invalid Date' ? printDate(date) : value;
        }
        return out;
    });

    addExtender('cleanup', function(value, cleaner) {
        return !!value ? cleaner(value) : '';
    });

    addExtender('ensureHttp', function(value, options) {
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

    ko.validation.rules['url'] = makeRegexValidator(
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

    $.osf.ko.makeExtender = makeExtender;
    $.osf.ko.addExtender = addExtender;
    $.osf.ko.makeRegexValidator = makeRegexValidator;
    $.osf.ko.sanitizedObservable = sanitizedObservable;

}));
