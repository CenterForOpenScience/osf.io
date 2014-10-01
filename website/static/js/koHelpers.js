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
            validator: function(value) {
                if (ko.validation.utils.isEmptyVal(value)) {
                    return true;
                }
                return match === regex.test(ko.utils.unwrapObservable(value));
            },
            message: message
        };
    };

    var printDate = function(date, dlm) {
        dlm = dlm || '/';
        var formatted = date.getFullYear() + dlm + pad((date.getMonth() + 1), 2);
        if (date.getDate()) {
            formatted += dlm + pad(date.getDate(), 2);
        }
        return formatted;
    };

    // Handy pad function from http://stackoverflow.com/a/10073788
    function pad(n, width, z) {
      z = z || '0';
      n = n + '';
      return n.length >= width ? n : new Array(width - n.length + 1).join(z) + n;
    }

//    addExtender('asDate', function(value) {
//        var out;
//        if (value) {
//            //value.replace(/-/g,'/');
//            var date;
//            if (value.match(/^\d{4}$/)) {
//                date = new Date(value, 0, 1);
//                //date = value;
//            } else {
//                date = '';
//            }
//            //out = date !== 'Invalid Date' ? value: '';
//        }
//        return date;
//    });

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

    ko.validation.rules['pyDate'] = {
        validator: function (val) {
            // Skip if values empty
            var uwVal = ko.utils.unwrapObservable(val);
            if (uwVal === null) {
                return true;
            }
            // Skip if dates invalid
            var dateVal = new Date(uwVal);
            if (dateVal == 'Invalid Date') {
                return true;
            }
            // Compare dates
            return dateVal.getFullYear() >= 1900;
        },
        message: 'Date must be greater than or equal to 1900.'
    };

    ko.validation.rules['notInFuture'] = {
        validator: function (val) {
            // Skip if values empty
            var uwVal = ko.utils.unwrapObservable(val);
            if (uwVal === null) {
                return true;
            }
            //Skip if dates invalid
            var dateVal = new Date(uwVal);
            if (dateVal == 'Invalid Date') {
                return true;
            }
            // Compare dates
            var now = new Date();
            return val < now;

        },
        message: 'Please enter a valid date'
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
