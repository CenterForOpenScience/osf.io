'use strict';

var $ = require('jquery');
var ko = require('knockout');
require('knockout.validation');

var iconmap = require('js/iconmap');

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

addExtender('trimmed', function(value) {
    return $.trim(value);
});

var sanitize = function(value) {
    return value.replace(/<\/?[^>]+>/g, '');
};

var sanitizedObservable = function(value) {
    return ko.observable(value).extend({
        cleanup: sanitize
    });
};

/* maps js data one deep to observables
    options:
        exclude: adds listed parameters without making observable
*/
var mapJStoKO = function(data, options) {
    var settings = $.extend({
        exclude: []   //List of object parameters to exclude
    }, options || {});
    var dataOut = {};

    for (var key in data) {
        // checks for key, if in the exclude list
        if (data.hasOwnProperty(key) && $.inArray(key, settings.exclude) === -1) {
            if(Array.isArray(data[key])) {
                dataOut[key] = ko.observableArray(data[key]);
            } else {
                dataOut[key] = ko.observable(data[key]);
            }
        } else if (data.hasOwnProperty(key)) {
            dataOut[key] = data[key]; //excluded parameters
        }
    }
    return dataOut;
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

ko.validation.rules.mustEqual = {
    validator: function (val, otherVal) {
        return val === otherVal;
    },
    message: 'The field does not match the required input.'
};


// Add custom effects

// fadeVisible : http://knockoutjs.com/examples/animatedTransitions.html
ko.bindingHandlers.fadeVisible = {
    init: function(element, valueAccessor) {
        // Initially set the element to be instantly visible/hidden depending on the value
        var value = valueAccessor();
        $(element).toggle(ko.unwrap(value)); // Use "unwrapObservable" so we can handle values that may or may not be observable
    },
    update: function(element, valueAccessor) {
        // Whenever the value subsequently changes, slowly fade the element in or out
        var value = valueAccessor();
        ko.unwrap(value) ? $(element).fadeIn() : $(element).hide().fadeOut();
    }
};

var tooltip = function(el, valueAccessor) {
    var params = valueAccessor();
    $(el).tooltip(params);
};
// Run Bootstrap tooltip JS automagically
// http://getbootstrap.com/javascript/#tooltips
ko.bindingHandlers.tooltip = {
    init: tooltip,
    update: tooltip
};
// Attach view model logic to global keypress events
ko.bindingHandlers.onKeyPress = {
    init: function(el, valueAccessor) {
        $(window).keydown(function(e) {
            var params = valueAccessor();
            if (e.keyCode === params.keyCode) {
                params.listener(e);
            }
        });
    }
};

/* A binding handler to convert lists into formatted lists, e.g.:
 * [dog] -> dog
 * [dog, cat] -> dog and cat
 * [dog, cat, fish] -> dog, cat, and fish
 *
 * This handler should not be used for user inputs.
 *
 * Example use:
 * <span data-bind="listing: {data: ['Alpha', 'Beta', 'Gamma'],
 *                            map: function(item) {return item.charAt(0) + '.';}}"></span>
 * yields
 * <span ...>A., B., and G.</span>
 */
ko.bindingHandlers.listing = {
    update: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
        var value = valueAccessor();
        var valueUnwrapped = ko.unwrap(value);
        var map = valueUnwrapped.map || function(item) {return item;};
        var data = valueUnwrapped.data || [];
        var keys = [];
        if (!Array.isArray(data)) {
            keys = Object.keys(data);
        }
        else {
            keys = data;
        }
        var index = 1;
        var list = ko.utils.arrayMap(keys, function(key) {
            var ret;
            if (index === 1){
                ret = '';
            }
            else if (index === 2){
                if (valueUnwrapped.length === 2) {
                    ret = ' and ';
                }
                else {
                    ret = ', ';
                }
            }
            else {
                ret = ', and ';
            }
            ret += map(key, data[key]);
            index++;
            return ret;
        }).join('');
        $(element).text(list);
    }
};

/**
 * Takes over anchor scrolling and scrolls to anchor positions within elements
 * Example:
 * <span data-bind='anchorScroll'></span>
 */
ko.bindingHandlers.anchorScroll = {
    init: function(elem, valueAccessor) {
        var buffer = valueAccessor().buffer || 100;
        var element = valueAccessor().elem || elem;
        var offset;
        $(element).on('click', 'a[href^="#"]', function (event) {
            var $item = $(this);
            var $element = $(element);
            if(!$item.attr('data-model') && $item.attr('href') !== '#') {
                event.preventDefault();
                // get location of the target
                var target = $item.attr('href');
                // if target has a scrollbar scroll it, otherwise scroll the page
                if ( $element.get(0).scrollHeight > $element.innerHeight() ) {
                    offset = $(target).position();
                    $element.scrollTop(offset.top - buffer);
                } else {
                    offset = $(target).offset();
                    $(window).scrollTop(offset.top - 100); // This is fixed to 100 because of the fixed navigation menus on the page
                }
            }
        });
    }
};

/**
 * Required in render_node.mako to call getIcon. As a result of modularity there
 * are overlapping scopes. To temporarily escape the parent scope and allow other binding
 * stopBinding can be used. Only other option was to redo the structure of the scopes.
 * Example:
 * <span data-bind="stopBinding: true"></span>
 */
ko.bindingHandlers.stopBinding = {
    init: function() {
        return { controlsDescendantBindings: true };
    }
};

/**
 * Adds class returned from iconmap to the element. The value accessor should be the
 * category of the node.
 * Example:
 * <span data-bind="getIcon: 'analysis'"></span>
 */
ko.bindingHandlers.getIcon = {
    init: function(elem, valueAccessor) {
        var icon;
        var category = valueAccessor();
        if (Object.keys(iconmap.componentIcons).indexOf(category) >=0 ){
            icon = iconmap.componentIcons[category];
        }
        else {
            icon = iconmap.projectIcons[category];
        }
        $(elem).addClass(icon);
    }
};



// Expose public utilities

module.exports = {
    makeExtender: makeExtender,
    addExtender: addExtender,
    makeRegexValidator: makeRegexValidator,
    sanitizedObservable: sanitizedObservable,
    mapJStoKO: mapJStoKO
};
