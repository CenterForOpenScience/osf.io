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
                date = new Date(value);
            }
            out = date != 'Invalid Date' ? printDate(date) : value;
        }
        return out;
    });

    addExtender('cleanup', function(value, cleaner) {
        return !!value ? cleaner(value) : '';
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
        new RegExp('\b((?:https?:\/\/|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}\/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[    ^\s`!()\[\]{};:\'".,<>?«»“”‘’]))', 'i'),
        'Please enter a valid URL.'
    );

    // Expose public utilities

    $.osf.ko.makeExtender = makeExtender;
    $.osf.ko.addExtender = addExtender;
    $.osf.ko.makeRegexValidator = makeRegexValidator;
    $.osf.ko.sanitizedObservable = sanitizedObservable;

}));
