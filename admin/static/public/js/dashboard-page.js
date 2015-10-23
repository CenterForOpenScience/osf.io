webpackJsonp([4],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

/**
 * Initialization code for the dashboard pages. Starts up the Project Organizer
 * and binds the onboarder Knockout components.
 */

'use strict';

var Raven = __webpack_require__(52);
var ko = __webpack_require__(48);
var $ = __webpack_require__(38);
var jstz = __webpack_require__(166).jstz;

// Knockout components for the onboarder
__webpack_require__(167);
var $osf = __webpack_require__(47);
var LogFeed = __webpack_require__(179);
var ProjectOrganizer = __webpack_require__(181).ProjectOrganizer;

var url = '/api/v1/dashboard/get_nodes/';
var request = $.getJSON(url, function(response) {
    var allNodes = response.nodes;
    //  For uploads, only show nodes for which user has write or admin permissions
    var uploadSelection = ko.utils.arrayFilter(allNodes, function(node) {
        return $.inArray(node.permissions, ['write', 'admin']) !== -1;
    });

    // If we need to change what nodes can be registered, filter here
    var registrationSelection = ko.utils.arrayFilter(allNodes, function(node) {
        return $.inArray(node.permissions, ['admin']) !== -1;
    });

    $osf.applyBindings({nodes: allNodes}, '#obGoToProject');
    $osf.applyBindings({nodes: registrationSelection, enableComponents: true}, '#obRegisterProject');
    $osf.applyBindings({nodes: uploadSelection}, '#obUploader');
    $osf.applyBindings({nodes: allNodes}, '#obCreateProject');
});
request.fail(function(xhr, textStatus, error) {
    Raven.captureMessage('Could not fetch dashboard nodes.', {
        url: url, textStatus: textStatus, error: error
    });
});

var ensureUserTimezone = function(savedTimezone, savedLocale, id) {
    var clientTimezone = jstz.determine().name();
    var clientLocale = window.navigator.userLanguage || window.navigator.language;

    if (savedTimezone !== clientTimezone || savedLocale !== clientLocale) {
        var url = '/api/v1/profile/';

        var request = $osf.putJSON(
            url,
            {
                'timezone': clientTimezone,
                'locale': clientLocale,
                'id': id
            }
        );
        request.fail(function(xhr, textStatus, error) {
            Raven.captureMessage('Could not set user timezone or locale', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
    }
};

$(document).ready(function() {
    $('#projectOrganizerScope').tooltip({selector: '[data-toggle=tooltip]'});

    var request = $.ajax({
        url:  '/api/v1/dashboard/'
    });
    request.done(function(data) {
        var po = new ProjectOrganizer({
            placement : 'dashboard',
            divID: 'project-grid',
            filesData: data.data,
            multiselect : true
        });

        ensureUserTimezone(data.timezone, data.locale, data.id);
    });
    request.fail(function(xhr, textStatus, error) {
        Raven.captureMessage('Failed to populate user dashboard', {
            url: url,
            textStatus: textStatus,
            error: error
        });
    });

});

// Initialize logfeed
new LogFeed('#logScope', '/api/v1/watched/logs/');


/***/ },

/***/ 152:
/***/ function(module, exports, __webpack_require__) {

/**
 * @license Knockout.Punches
 * Enhanced binding syntaxes for Knockout 3+
 * (c) Michael Best
 * License: MIT (http://www.opensource.org/licenses/mit-license.php)
 * Version 0.5.1
 */
var ko = __webpack_require__(48);

// Add a preprocess function to a binding handler.
function addBindingPreprocessor(bindingKeyOrHandler, preprocessFn) {
    return chainPreprocessor(getOrCreateHandler(bindingKeyOrHandler), 'preprocess', preprocessFn);
}

// These utility functions are separated out because they're also used by
// preprocessBindingProperty

// Get the binding handler or create a new, empty one
function getOrCreateHandler(bindingKeyOrHandler) {
    return typeof bindingKeyOrHandler === 'object' ? bindingKeyOrHandler :
        (ko.getBindingHandler(bindingKeyOrHandler) || (ko.bindingHandlers[bindingKeyOrHandler] = {}));
}
// Add a preprocess function
function chainPreprocessor(obj, prop, fn) {
    if (obj[prop]) {
        // If the handler already has a preprocess function, chain the new
        // one after the existing one. If the previous function in the chain
        // returns a falsy value (to remove the binding), the chain ends. This
        // method allows each function to modify and return the binding value.
        var previousFn = obj[prop];
        obj[prop] = function(value, binding, addBinding) {
            value = previousFn.call(this, value, binding, addBinding);
            if (value)
                return fn.call(this, value, binding, addBinding);
        };
    } else {
        obj[prop] = fn;
    }
    return obj;
}

// Add a preprocessNode function to the binding provider. If a
// function already exists, chain the new one after it. This calls
// each function in the chain until one modifies the node. This
// method allows only one function to modify the node.
function addNodePreprocessor(preprocessFn) {
    var provider = ko.bindingProvider.instance;
    if (provider.preprocessNode) {
        var previousPreprocessFn = provider.preprocessNode;
        provider.preprocessNode = function(node) {
            var newNodes = previousPreprocessFn.call(this, node);
            if (!newNodes)
                newNodes = preprocessFn.call(this, node);
            return newNodes;
        };
    } else {
        provider.preprocessNode = preprocessFn;
    }
}

function addBindingHandlerCreator(matchRegex, callbackFn) {
    var oldGetHandler = ko.getBindingHandler;
    ko.getBindingHandler = function(bindingKey) {
        var match;
        return oldGetHandler(bindingKey) || ((match = bindingKey.match(matchRegex)) && callbackFn(match, bindingKey));
    };
}

// Create shortcuts to commonly used ko functions
var ko_unwrap = ko.unwrap;

// Create "punches" object and export utility functions
var ko_punches = ko.punches = {
    utils: {
        addBindingPreprocessor: addBindingPreprocessor,
        addNodePreprocessor: addNodePreprocessor,
        addBindingHandlerCreator: addBindingHandlerCreator,

        // previous names retained for backwards compitibility
        setBindingPreprocessor: addBindingPreprocessor,
        setNodePreprocessor: addNodePreprocessor
    }
};

ko_punches.enableAll = function () {
    // Enable interpolation markup
    enableInterpolationMarkup();
    enableAttributeInterpolationMarkup();

    // Enable auto-namspacing of attr, css, event, and style
    enableAutoNamespacedSyntax('attr');
    enableAutoNamespacedSyntax('css');
    enableAutoNamespacedSyntax('event');
    enableAutoNamespacedSyntax('style');

    // Make sure that Knockout knows to bind checked after attr.value (see #40)
    ko.bindingHandlers.checked.after.push('attr.value');

    // Enable filter syntax for text, html, and attr
    enableTextFilter('text');
    enableTextFilter('html');
    addDefaultNamespacedBindingPreprocessor('attr', filterPreprocessor);

    // Enable wrapped callbacks for click, submit, event, optionsAfterRender, and template options
    enableWrappedCallback('click');
    enableWrappedCallback('submit');
    enableWrappedCallback('optionsAfterRender');
    addDefaultNamespacedBindingPreprocessor('event', wrappedCallbackPreprocessor);
    addBindingPropertyPreprocessor('template', 'beforeRemove', wrappedCallbackPreprocessor);
    addBindingPropertyPreprocessor('template', 'afterAdd', wrappedCallbackPreprocessor);
    addBindingPropertyPreprocessor('template', 'afterRender', wrappedCallbackPreprocessor);
};
// Convert input in the form of `expression | filter1 | filter2:arg1:arg2` to a function call format
// with filters accessed as ko.filters.filter1, etc.
function filterPreprocessor(input) {
    // Check if the input contains any | characters; if not, just return
    if (input.indexOf('|') === -1)
        return input;

    // Split the input into tokens, in which | and : are individual tokens, quoted strings are ignored, and all tokens are space-trimmed
    var tokens = input.match(/"([^"\\]|\\.)*"|'([^'\\]|\\.)*'|\|\||[|:]|[^\s|:"'][^|:"']*[^\s|:"']|[^\s|:"']/g);
    if (tokens && tokens.length > 1) {
        // Append a line so that we don't need a separate code block to deal with the last item
        tokens.push('|');
        input = tokens[0];
        var lastToken, token, inFilters = false, nextIsFilter = false;
        for (var i = 1, token; token = tokens[i]; ++i) {
            if (token === '|') {
                if (inFilters) {
                    if (lastToken === ':')
                        input += "undefined";
                    input += ')';
                }
                nextIsFilter = true;
                inFilters = true;
            } else {
                if (nextIsFilter) {
                    input = "ko.filters['" + token + "'](" + input;
                } else if (inFilters && token === ':') {
                    if (lastToken === ':')
                        input += "undefined";
                    input += ",";
                } else {
                    input += token;
                }
                nextIsFilter = false;
            }
            lastToken = token;
        }
    }
    return input;
}

// Set the filter preprocessor for a specific binding
function enableTextFilter(bindingKeyOrHandler) {
    addBindingPreprocessor(bindingKeyOrHandler, filterPreprocessor);
}

var filters = {};

// Convert value to uppercase
filters.uppercase = function(value) {
    return String.prototype.toUpperCase.call(ko_unwrap(value));
};

// Convert value to lowercase
filters.lowercase = function(value) {
    return String.prototype.toLowerCase.call(ko_unwrap(value));
};

// Return default value if the input value is empty or null
filters['default'] = function (value, defaultValue) {
    value = ko_unwrap(value);
    if (typeof value === "function") {
        return value;
    }
    if (typeof value === "string") {
        return trim(value) === '' ? defaultValue : value;
    }
    return value == null || value.length == 0 ? defaultValue : value;
};

// Return the value with the search string replaced with the replacement string
filters.replace = function(value, search, replace) {
    return String.prototype.replace.call(ko_unwrap(value), search, replace);
};

filters.fit = function(value, length, replacement, trimWhere) {
    value = ko_unwrap(value);
    if (length && ('' + value).length > length) {
        replacement = '' + (replacement || '...');
        length = length - replacement.length;
        value = '' + value;
        switch (trimWhere) {
            case 'left':
                return replacement + value.slice(-length);
            case 'middle':
                var leftLen = Math.ceil(length / 2);
                return value.substr(0, leftLen) + replacement + value.slice(leftLen-length);
            default:
                return value.substr(0, length) + replacement;
        }
    } else {
        return value;
    }
};

// Convert a model object to JSON
filters.json = function(rootObject, space, replacer) {     // replacer and space are optional
    return ko.toJSON(rootObject, replacer, space);
};

// Format a number using the browser's toLocaleString
filters.number = function(value) {
    return (+ko_unwrap(value)).toLocaleString();
};

// Export the filters object for general access
ko.filters = filters;

// Export the preprocessor functions
ko_punches.textFilter = {
    preprocessor: filterPreprocessor,
    enableForBinding: enableTextFilter
};
// Support dynamically-created, namespaced bindings. The binding key syntax is
// "namespace.binding". Within a certain namespace, we can dynamically create the
// handler for any binding. This is particularly useful for bindings that work
// the same way, but just set a different named value, such as for element
// attributes or CSS classes.
var namespacedBindingMatch = /([^\.]+)\.(.+)/, namespaceDivider = '.';
addBindingHandlerCreator(namespacedBindingMatch, function (match, bindingKey) {
    var namespace = match[1],
        namespaceHandler = ko.bindingHandlers[namespace];
    if (namespaceHandler) {
        var bindingName = match[2],
            handlerFn = namespaceHandler.getNamespacedHandler || defaultGetNamespacedHandler,
            handler = handlerFn.call(namespaceHandler, bindingName, namespace, bindingKey);
        ko.bindingHandlers[bindingKey] = handler;
        return handler;
    }
});

// Knockout's built-in bindings "attr", "event", "css" and "style" include the idea of
// namespaces, representing it using a single binding that takes an object map of names
// to values. This default handler translates a binding of "namespacedName: value"
// to "namespace: {name: value}" to automatically support those built-in bindings.
function defaultGetNamespacedHandler(name, namespace, namespacedName) {
    var handler = ko.utils.extend({}, this);
    function setHandlerFunction(funcName) {
        if (handler[funcName]) {
            handler[funcName] = function(element, valueAccessor) {
                function subValueAccessor() {
                    var result = {};
                    result[name] = valueAccessor();
                    return result;
                }
                var args = Array.prototype.slice.call(arguments, 0);
                args[1] = subValueAccessor;
                return ko.bindingHandlers[namespace][funcName].apply(this, args);
            };
        }
    }
    // Set new init and update functions that wrap the originals
    setHandlerFunction('init');
    setHandlerFunction('update');
    // Clear any preprocess function since preprocessing of the new binding would need to be different
    if (handler.preprocess)
        handler.preprocess = null;
    if (ko.virtualElements.allowedBindings[namespace])
        ko.virtualElements.allowedBindings[namespacedName] = true;
    return handler;
}

// Adds a preprocess function for every generated namespace.x binding. This can
// be called multiple times for the same binding, and the preprocess functions will
// be chained. If the binding has a custom getNamespacedHandler method, make sure that
// it's set before this function is used.
function addDefaultNamespacedBindingPreprocessor(namespace, preprocessFn) {
    var handler = ko.getBindingHandler(namespace);
    if (handler) {
        var previousHandlerFn = handler.getNamespacedHandler || defaultGetNamespacedHandler;
        handler.getNamespacedHandler = function() {
            return addBindingPreprocessor(previousHandlerFn.apply(this, arguments), preprocessFn);
        };
    }
}

function autoNamespacedPreprocessor(value, binding, addBinding) {
    if (value.charAt(0) !== "{")
        return value;

    // Handle two-level binding specified as "binding: {key: value}" by parsing inner
    // object and converting to "binding.key: value"
    var subBindings = ko.expressionRewriting.parseObjectLiteral(value);
    ko.utils.arrayForEach(subBindings, function(keyValue) {
        addBinding(binding + namespaceDivider + keyValue.key, keyValue.value);
    });
}

// Set the namespaced preprocessor for a specific binding
function enableAutoNamespacedSyntax(bindingKeyOrHandler) {
    addBindingPreprocessor(bindingKeyOrHandler, autoNamespacedPreprocessor);
}

// Export the preprocessor functions
ko_punches.namespacedBinding = {
    defaultGetHandler: defaultGetNamespacedHandler,
    setDefaultBindingPreprocessor: addDefaultNamespacedBindingPreprocessor,    // for backwards compat.
    addDefaultBindingPreprocessor: addDefaultNamespacedBindingPreprocessor,
    preprocessor: autoNamespacedPreprocessor,
    enableForBinding: enableAutoNamespacedSyntax
};
// Wrap a callback function in an anonymous function so that it is called with the appropriate
// "this" value.
function wrappedCallbackPreprocessor(val) {
    // Matches either an isolated identifier or something ending with a property accessor
    if (/^([$_a-z][$\w]*|.+(\.\s*[$_a-z][$\w]*|\[.+\]))$/i.test(val)) {
        return 'function(_x,_y,_z){return(' + val + ')(_x,_y,_z);}';
    } else {
        return val;
    }
}

// Set the wrappedCallback preprocessor for a specific binding
function enableWrappedCallback(bindingKeyOrHandler) {
    addBindingPreprocessor(bindingKeyOrHandler, wrappedCallbackPreprocessor);
}

// Export the preprocessor functions
ko_punches.wrappedCallback = {
    preprocessor: wrappedCallbackPreprocessor,
    enableForBinding: enableWrappedCallback
};
// Attach a preprocess function to a specific property of a binding. This allows you to
// preprocess binding "options" using the same preprocess functions that work for bindings.
function addBindingPropertyPreprocessor(bindingKeyOrHandler, property, preprocessFn) {
    var handler = getOrCreateHandler(bindingKeyOrHandler);
    if (!handler._propertyPreprocessors) {
        // Initialize the binding preprocessor
        chainPreprocessor(handler, 'preprocess', propertyPreprocessor);
        handler._propertyPreprocessors = {};
    }
    // Add the property preprocess function
    chainPreprocessor(handler._propertyPreprocessors, property, preprocessFn);
}

// In order to preprocess a binding property, we have to preprocess the binding itself.
// This preprocess function splits up the binding value and runs each property's preprocess
// function if it's set.
function propertyPreprocessor(value, binding, addBinding) {
    if (value.charAt(0) !== "{")
        return value;

    var subBindings = ko.expressionRewriting.parseObjectLiteral(value),
        resultStrings = [],
        propertyPreprocessors = this._propertyPreprocessors || {};
    ko.utils.arrayForEach(subBindings, function(keyValue) {
        var prop = keyValue.key, propVal = keyValue.value;
        if (propertyPreprocessors[prop]) {
            propVal = propertyPreprocessors[prop](propVal, prop, addBinding);
        }
        if (propVal) {
            resultStrings.push("'" + prop + "':" + propVal);
        }
    });
    return "{" + resultStrings.join(",") + "}";
}

// Export the preprocessor functions
ko_punches.preprocessBindingProperty = {
    setPreprocessor: addBindingPropertyPreprocessor,     // for backwards compat.
    addPreprocessor: addBindingPropertyPreprocessor
};
// Wrap an expression in an anonymous function so that it is called when the event happens
function makeExpressionCallbackPreprocessor(args) {
    return function expressionCallbackPreprocessor(val) {
        return 'function('+args+'){return(' + val + ');}';
    };
}

var eventExpressionPreprocessor = makeExpressionCallbackPreprocessor("$data,$event");

// Set the expressionCallback preprocessor for a specific binding
function enableExpressionCallback(bindingKeyOrHandler, args) {
    var args = Array.prototype.slice.call(arguments, 1).join();
    addBindingPreprocessor(bindingKeyOrHandler, makeExpressionCallbackPreprocessor(args));
}

// Export the preprocessor functions
ko_punches.expressionCallback = {
    makePreprocessor: makeExpressionCallbackPreprocessor,
    eventPreprocessor: eventExpressionPreprocessor,
    enableForBinding: enableExpressionCallback
};

// Create an "on" namespace for events to use the expression method
ko.bindingHandlers.on = {
    getNamespacedHandler: function(eventName) {
        var handler = ko.getBindingHandler('event' + namespaceDivider + eventName);
        return addBindingPreprocessor(handler, eventExpressionPreprocessor);
    }
};
// Performance comparison at http://jsperf.com/markup-interpolation-comparison
function parseInterpolationMarkup(textToParse, outerTextCallback, expressionCallback) {
    function innerParse(text) {
        var innerMatch = text.match(/^([\s\S]*)}}([\s\S]*?)\{\{([\s\S]*)$/);
        if (innerMatch) {
            innerParse(innerMatch[1]);
            outerTextCallback(innerMatch[2]);
            expressionCallback(innerMatch[3]);
        } else {
            expressionCallback(text);
        }
    }
    var outerMatch = textToParse.match(/^([\s\S]*?)\{\{([\s\S]*)}}([\s\S]*)$/);
    if (outerMatch) {
        outerTextCallback(outerMatch[1]);
        innerParse(outerMatch[2]);
        outerTextCallback(outerMatch[3]);
    }
}

function trim(string) {
    return string == null ? '' :
        string.trim ?
            string.trim() :
            string.toString().replace(/^[\s\xa0]+|[\s\xa0]+$/g, '');
}

function interpolationMarkupPreprocessor(node) {
    // only needs to work with text nodes
    if (node.nodeType === 3 && node.nodeValue && node.nodeValue.indexOf('{{') !== -1 && (node.parentNode || {}).nodeName != "TEXTAREA") {
        var nodes = [];
        function addTextNode(text) {
            if (text)
                nodes.push(document.createTextNode(text));
        }
        function wrapExpr(expressionText) {
            if (expressionText)
                nodes.push.apply(nodes, ko_punches_interpolationMarkup.wrapExpression(expressionText, node));
        }
        parseInterpolationMarkup(node.nodeValue, addTextNode, wrapExpr)

        if (nodes.length) {
            if (node.parentNode) {
                for (var i = 0, n = nodes.length, parent = node.parentNode; i < n; ++i) {
                    parent.insertBefore(nodes[i], node);
                }
                parent.removeChild(node);
            }
            return nodes;
        }
    }
}

if (!ko.virtualElements.allowedBindings.html) {
    // Virtual html binding
    // SO Question: http://stackoverflow.com/a/15348139
    var overridden = ko.bindingHandlers.html.update;
    ko.bindingHandlers.html.update = function (element, valueAccessor) {
        if (element.nodeType === 8) {
            var html = ko_unwrap(valueAccessor());
            if (html != null) {
                var parsedNodes = ko.utils.parseHtmlFragment('' + html);
                ko.virtualElements.setDomNodeChildren(element, parsedNodes);
            } else {
                ko.virtualElements.emptyNode(element);
            }
        } else {
            overridden(element, valueAccessor);
        }
    };
    ko.virtualElements.allowedBindings.html = true;
}

function wrapExpression(expressionText, node) {
    var ownerDocument = node ? node.ownerDocument : document,
        closeComment = true,
        binding,
        expressionText = trim(expressionText),
        firstChar = expressionText[0],
        lastChar = expressionText[expressionText.length - 1],
        result = [],
        matches;

    if (firstChar === '#') {
        if (lastChar === '/') {
            binding = expressionText.slice(1, -1);
        } else {
            binding = expressionText.slice(1);
            closeComment = false;
        }
        if (matches = binding.match(/^([^,"'{}()\/:[\]\s]+)\s+([^\s:].*)/)) {
            binding = matches[1] + ':' + matches[2];
        }
    } else if (firstChar === '/') {
        // replace only with a closing comment
    } else if (firstChar === '{' && lastChar === '}') {
        binding = "html:" + trim(expressionText.slice(1, -1));
    } else {
        binding = "text:" + trim(expressionText);
    }

    if (binding)
        result.push(ownerDocument.createComment("ko " + binding));
    if (closeComment)
        result.push(ownerDocument.createComment("/ko"));
    return result;
};

function enableInterpolationMarkup() {
    addNodePreprocessor(interpolationMarkupPreprocessor);
}

// Export the preprocessor functions
var ko_punches_interpolationMarkup = ko_punches.interpolationMarkup = {
    preprocessor: interpolationMarkupPreprocessor,
    enable: enableInterpolationMarkup,
    wrapExpression: wrapExpression
};


var dataBind = 'data-bind';
function attributeInterpolationMarkerPreprocessor(node) {
    if (node.nodeType === 1 && node.attributes.length) {
        var dataBindAttribute = node.getAttribute(dataBind);
        for (var attrs = ko.utils.arrayPushAll([], node.attributes), n = attrs.length, i = 0; i < n; ++i) {
            var attr = attrs[i];
            if (attr.specified && attr.name != dataBind && attr.value.indexOf('{{') !== -1) {
                var parts = [], attrValue = '';
                function addText(text) {
                    if (text)
                        parts.push('"' + text.replace(/"/g, '\\"') + '"');
                }
                function addExpr(expressionText) {
                    if (expressionText) {
                        attrValue = expressionText;
                        parts.push('ko.unwrap(' + expressionText + ')');
                    }
                }
                parseInterpolationMarkup(attr.value, addText, addExpr);

                if (parts.length > 1) {
                    attrValue = '""+' + parts.join('+');
                }

                if (attrValue) {
                    var attrName = attr.name.toLowerCase();
                    var attrBinding = ko_punches_attributeInterpolationMarkup.attributeBinding(attrName, attrValue, node) || attributeBinding(attrName, attrValue, node);
                    if (!dataBindAttribute) {
                        dataBindAttribute = attrBinding
                    } else {
                        dataBindAttribute += ',' + attrBinding;
                    }
                    node.setAttribute(dataBind, dataBindAttribute);
                    // Using removeAttribute instead of removeAttributeNode because IE clears the
                    // class if you use removeAttributeNode to remove the id.
                    node.removeAttribute(attr.name);
                }
            }
        }
    }
}

function attributeBinding(name, value, node) {
    if (ko.getBindingHandler(name)) {
        return name + ':' + value;
    } else {
        return 'attr.' + name + ':' + value;
    }
}

function enableAttributeInterpolationMarkup() {
    addNodePreprocessor(attributeInterpolationMarkerPreprocessor);
}

var ko_punches_attributeInterpolationMarkup = ko_punches.attributeInterpolationMarkup = {
    preprocessor: attributeInterpolationMarkerPreprocessor,
    enable: enableAttributeInterpolationMarkup,
    attributeBinding: attributeBinding
};


/***/ },

/***/ 166:
/***/ function(module, exports, __webpack_require__) {

/**
 * This script gives you the zone info key representing your device's time zone setting.
 *
 * @name jsTimezoneDetect
 * @version 1.0.5
 * @author Jon Nylander
 * @license MIT License - http://www.opensource.org/licenses/mit-license.php
 *
 * For usage and examples, visit:
 * http://pellepim.bitbucket.org/jstz/
 *
 * Copyright (c) Jon Nylander
 */

/*jslint undef: true */
/*global console, exports*/

(function(root) {
  /**
   * Namespace to hold all the code for timezone detection.
   */
  var jstz = (function () {
      'use strict';
      var HEMISPHERE_SOUTH = 's',
          
          /**
           * Gets the offset in minutes from UTC for a certain date.
           * @param {Date} date
           * @returns {Number}
           */
          get_date_offset = function (date) {
              var offset = -date.getTimezoneOffset();
              return (offset !== null ? offset : 0);
          },

          get_date = function (year, month, date) {
              var d = new Date();
              if (year !== undefined) {
                d.setFullYear(year);
              }
              d.setMonth(month);
              d.setDate(date);
              return d;
          },

          get_january_offset = function (year) {
              return get_date_offset(get_date(year, 0 ,2));
          },

          get_june_offset = function (year) {
              return get_date_offset(get_date(year, 5, 2));
          },

          /**
           * Private method.
           * Checks whether a given date is in daylight saving time.
           * If the date supplied is after august, we assume that we're checking
           * for southern hemisphere DST.
           * @param {Date} date
           * @returns {Boolean}
           */
          date_is_dst = function (date) {
              var is_southern = date.getMonth() > 7,
                  base_offset = is_southern ? get_june_offset(date.getFullYear()) : 
                                              get_january_offset(date.getFullYear()),
                  date_offset = get_date_offset(date),
                  is_west = base_offset < 0,
                  dst_offset = base_offset - date_offset;
                  
              if (!is_west && !is_southern) {
                  return dst_offset < 0;
              }

              return dst_offset !== 0;
          },

          /**
           * This function does some basic calculations to create information about
           * the user's timezone. It uses REFERENCE_YEAR as a solid year for which
           * the script has been tested rather than depend on the year set by the
           * client device.
           *
           * Returns a key that can be used to do lookups in jstz.olson.timezones.
           * eg: "720,1,2". 
           *
           * @returns {String}
           */

          lookup_key = function () {
              var january_offset = get_january_offset(),
                  june_offset = get_june_offset(),
                  diff = january_offset - june_offset;

              if (diff < 0) {
                  return january_offset + ",1";
              } else if (diff > 0) {
                  return june_offset + ",1," + HEMISPHERE_SOUTH;
              }

              return january_offset + ",0";
          },

          /**
           * Uses get_timezone_info() to formulate a key to use in the olson.timezones dictionary.
           *
           * Returns a primitive object on the format:
           * {'timezone': TimeZone, 'key' : 'the key used to find the TimeZone object'}
           *
           * @returns Object
           */
          determine = function () {
              var key = lookup_key();
              return new jstz.TimeZone(jstz.olson.timezones[key]);
          },

          /**
           * This object contains information on when daylight savings starts for
           * different timezones.
           *
           * The list is short for a reason. Often we do not have to be very specific
           * to single out the correct timezone. But when we do, this list comes in
           * handy.
           *
           * Each value is a date denoting when daylight savings starts for that timezone.
           */
          dst_start_for = function (tz_name) {

            var ru_pre_dst_change = new Date(2010, 6, 15, 1, 0, 0, 0), // In 2010 Russia had DST, this allows us to detect Russia :)
                dst_starts = {
                    'America/Denver': new Date(2011, 2, 13, 3, 0, 0, 0),
                    'America/Mazatlan': new Date(2011, 3, 3, 3, 0, 0, 0),
                    'America/Chicago': new Date(2011, 2, 13, 3, 0, 0, 0),
                    'America/Mexico_City': new Date(2011, 3, 3, 3, 0, 0, 0),
                    'America/Asuncion': new Date(2012, 9, 7, 3, 0, 0, 0),
                    'America/Santiago': new Date(2012, 9, 3, 3, 0, 0, 0),
                    'America/Campo_Grande': new Date(2012, 9, 21, 5, 0, 0, 0),
                    'America/Montevideo': new Date(2011, 9, 2, 3, 0, 0, 0),
                    'America/Sao_Paulo': new Date(2011, 9, 16, 5, 0, 0, 0),
                    'America/Los_Angeles': new Date(2011, 2, 13, 8, 0, 0, 0),
                    'America/Santa_Isabel': new Date(2011, 3, 5, 8, 0, 0, 0),
                    'America/Havana': new Date(2012, 2, 10, 2, 0, 0, 0),
                    'America/New_York': new Date(2012, 2, 10, 7, 0, 0, 0),
                    'Europe/Helsinki': new Date(2013, 2, 31, 5, 0, 0, 0),
                    'Pacific/Auckland': new Date(2011, 8, 26, 7, 0, 0, 0),
                    'America/Halifax': new Date(2011, 2, 13, 6, 0, 0, 0),
                    'America/Goose_Bay': new Date(2011, 2, 13, 2, 1, 0, 0),
                    'America/Miquelon': new Date(2011, 2, 13, 5, 0, 0, 0),
                    'America/Godthab': new Date(2011, 2, 27, 1, 0, 0, 0),
                    'Europe/Moscow': ru_pre_dst_change,
                    'Asia/Amman': new Date(2013, 2, 29, 1, 0, 0, 0),
                    'Asia/Beirut': new Date(2013, 2, 31, 2, 0, 0, 0),
                    'Asia/Damascus': new Date(2013, 3, 6, 2, 0, 0, 0),
                    'Asia/Jerusalem': new Date(2013, 2, 29, 5, 0, 0, 0),
                    'Asia/Yekaterinburg': ru_pre_dst_change,
                    'Asia/Omsk': ru_pre_dst_change,
                    'Asia/Krasnoyarsk': ru_pre_dst_change,
                    'Asia/Irkutsk': ru_pre_dst_change,
                    'Asia/Yakutsk': ru_pre_dst_change,
                    'Asia/Vladivostok': ru_pre_dst_change,
                    'Asia/Baku': new Date(2013, 2, 31, 4, 0, 0),
                    'Asia/Yerevan': new Date(2013, 2, 31, 3, 0, 0),
                    'Asia/Kamchatka': ru_pre_dst_change,
                    'Asia/Gaza': new Date(2010, 2, 27, 4, 0, 0),
                    'Africa/Cairo': new Date(2010, 4, 1, 3, 0, 0),
                    'Europe/Minsk': ru_pre_dst_change,
                    'Pacific/Apia': new Date(2010, 10, 1, 1, 0, 0, 0),
                    'Pacific/Fiji': new Date(2010, 11, 1, 0, 0, 0),
                    'Australia/Perth': new Date(2008, 10, 1, 1, 0, 0, 0)
                };

              return dst_starts[tz_name];
          };

      return {
          determine: determine,
          date_is_dst: date_is_dst,
          dst_start_for: dst_start_for 
      };
  }());

  /**
   * Simple object to perform ambiguity check and to return name of time zone.
   */
  jstz.TimeZone = function (tz_name) {
      'use strict';
        /**
         * The keys in this object are timezones that we know may be ambiguous after
         * a preliminary scan through the olson_tz object.
         *
         * The array of timezones to compare must be in the order that daylight savings
         * starts for the regions.
         */
      var AMBIGUITIES = {
              'America/Denver':       ['America/Denver', 'America/Mazatlan'],
              'America/Chicago':      ['America/Chicago', 'America/Mexico_City'],
              'America/Santiago':     ['America/Santiago', 'America/Asuncion', 'America/Campo_Grande'],
              'America/Montevideo':   ['America/Montevideo', 'America/Sao_Paulo'],
              'Asia/Beirut':          ['Asia/Amman', 'Asia/Jerusalem', 'Asia/Beirut', 'Europe/Helsinki','Asia/Damascus'],
              'Pacific/Auckland':     ['Pacific/Auckland', 'Pacific/Fiji'],
              'America/Los_Angeles':  ['America/Los_Angeles', 'America/Santa_Isabel'],
              'America/New_York':     ['America/Havana', 'America/New_York'],
              'America/Halifax':      ['America/Goose_Bay', 'America/Halifax'],
              'America/Godthab':      ['America/Miquelon', 'America/Godthab'],
              'Asia/Dubai':           ['Europe/Moscow'],
              'Asia/Dhaka':           ['Asia/Yekaterinburg'],
              'Asia/Jakarta':         ['Asia/Omsk'],
              'Asia/Shanghai':        ['Asia/Krasnoyarsk', 'Australia/Perth'],
              'Asia/Tokyo':           ['Asia/Irkutsk'],
              'Australia/Brisbane':   ['Asia/Yakutsk'],
              'Pacific/Noumea':       ['Asia/Vladivostok'],
              'Pacific/Tarawa':       ['Asia/Kamchatka', 'Pacific/Fiji'],
              'Pacific/Tongatapu':    ['Pacific/Apia'],
              'Asia/Baghdad':         ['Europe/Minsk'],
              'Asia/Baku':            ['Asia/Yerevan','Asia/Baku'],
              'Africa/Johannesburg':  ['Asia/Gaza', 'Africa/Cairo']
          },

          timezone_name = tz_name,
          
          /**
           * Checks if a timezone has possible ambiguities. I.e timezones that are similar.
           *
           * For example, if the preliminary scan determines that we're in America/Denver.
           * We double check here that we're really there and not in America/Mazatlan.
           *
           * This is done by checking known dates for when daylight savings start for different
           * timezones during 2010 and 2011.
           */
          ambiguity_check = function () {
              var ambiguity_list = AMBIGUITIES[timezone_name],
                  length = ambiguity_list.length,
                  i = 0,
                  tz = ambiguity_list[0];

              for (; i < length; i += 1) {
                  tz = ambiguity_list[i];

                  if (jstz.date_is_dst(jstz.dst_start_for(tz))) {
                      timezone_name = tz;
                      return;
                  }
              }
          },

          /**
           * Checks if it is possible that the timezone is ambiguous.
           */
          is_ambiguous = function () {
              return typeof (AMBIGUITIES[timezone_name]) !== 'undefined';
          };

      if (is_ambiguous()) {
          ambiguity_check();
      }

      return {
          name: function () {
              return timezone_name;
          }
      };
  };

  jstz.olson = {};

  /*
   * The keys in this dictionary are comma separated as such:
   *
   * First the offset compared to UTC time in minutes.
   *
   * Then a flag which is 0 if the timezone does not take daylight savings into account and 1 if it
   * does.
   *
   * Thirdly an optional 's' signifies that the timezone is in the southern hemisphere,
   * only interesting for timezones with DST.
   *
   * The mapped arrays is used for constructing the jstz.TimeZone object from within
   * jstz.determine_timezone();
   */
  jstz.olson.timezones = {
      '-720,0'   : 'Pacific/Majuro',
      '-660,0'   : 'Pacific/Pago_Pago',
      '-600,1'   : 'America/Adak',
      '-600,0'   : 'Pacific/Honolulu',
      '-570,0'   : 'Pacific/Marquesas',
      '-540,0'   : 'Pacific/Gambier',
      '-540,1'   : 'America/Anchorage',
      '-480,1'   : 'America/Los_Angeles',
      '-480,0'   : 'Pacific/Pitcairn',
      '-420,0'   : 'America/Phoenix',
      '-420,1'   : 'America/Denver',
      '-360,0'   : 'America/Guatemala',
      '-360,1'   : 'America/Chicago',
      '-360,1,s' : 'Pacific/Easter',
      '-300,0'   : 'America/Bogota',
      '-300,1'   : 'America/New_York',
      '-270,0'   : 'America/Caracas',
      '-240,1'   : 'America/Halifax',
      '-240,0'   : 'America/Santo_Domingo',
      '-240,1,s' : 'America/Santiago',
      '-210,1'   : 'America/St_Johns',
      '-180,1'   : 'America/Godthab',
      '-180,0'   : 'America/Argentina/Buenos_Aires',
      '-180,1,s' : 'America/Montevideo',
      '-120,0'   : 'America/Noronha',
      '-120,1'   : 'America/Noronha',
      '-60,1'    : 'Atlantic/Azores',
      '-60,0'    : 'Atlantic/Cape_Verde',
      '0,0'      : 'UTC',
      '0,1'      : 'Europe/London',
      '60,1'     : 'Europe/Berlin',
      '60,0'     : 'Africa/Lagos',
      '60,1,s'   : 'Africa/Windhoek',
      '120,1'    : 'Asia/Beirut',
      '120,0'    : 'Africa/Johannesburg',
      '180,0'    : 'Asia/Baghdad',
      '180,1'    : 'Europe/Moscow',
      '210,1'    : 'Asia/Tehran',
      '240,0'    : 'Asia/Dubai',
      '240,1'    : 'Asia/Baku',
      '270,0'    : 'Asia/Kabul',
      '300,1'    : 'Asia/Yekaterinburg',
      '300,0'    : 'Asia/Karachi',
      '330,0'    : 'Asia/Kolkata',
      '345,0'    : 'Asia/Kathmandu',
      '360,0'    : 'Asia/Dhaka',
      '360,1'    : 'Asia/Omsk',
      '390,0'    : 'Asia/Rangoon',
      '420,1'    : 'Asia/Krasnoyarsk',
      '420,0'    : 'Asia/Jakarta',
      '480,0'    : 'Asia/Shanghai',
      '480,1'    : 'Asia/Irkutsk',
      '525,0'    : 'Australia/Eucla',
      '525,1,s'  : 'Australia/Eucla',
      '540,1'    : 'Asia/Yakutsk',
      '540,0'    : 'Asia/Tokyo',
      '570,0'    : 'Australia/Darwin',
      '570,1,s'  : 'Australia/Adelaide',
      '600,0'    : 'Australia/Brisbane',
      '600,1'    : 'Asia/Vladivostok',
      '600,1,s'  : 'Australia/Sydney',
      '630,1,s'  : 'Australia/Lord_Howe',
      '660,1'    : 'Asia/Kamchatka',
      '660,0'    : 'Pacific/Noumea',
      '690,0'    : 'Pacific/Norfolk',
      '720,1,s'  : 'Pacific/Auckland',
      '720,0'    : 'Pacific/Tarawa',
      '765,1,s'  : 'Pacific/Chatham',
      '780,0'    : 'Pacific/Tongatapu',
      '780,1,s'  : 'Pacific/Apia',
      '840,0'    : 'Pacific/Kiritimati'
  };

  if (true) {
    exports.jstz = jstz;
  } else {
    root.jstz = jstz;
  }
})(this);



/***/ },

/***/ 167:
/***/ function(module, exports, __webpack_require__) {

/**
* Components and binding handlers for the dashboard "onboarding" interface.
* Includes a custom component for OSF project typeahead search, as well
* the viewmodels for each of the individual onboarding widgets.
*/
'use strict';

// CSS
__webpack_require__(168);
__webpack_require__(170);

var Dropzone = __webpack_require__(162);
var Raven = __webpack_require__(52);
var ko = __webpack_require__(48);
var $ = __webpack_require__(38);
__webpack_require__(172);


__webpack_require__(175);
var waterbutler = __webpack_require__(178);
var $osf = __webpack_require__(47);

function noop() {}
var MAX_RESULTS = 14;
var DEFAULT_FETCH_URL = '/api/v1/dashboard/get_nodes/';
var CREATE_URL = '/api/v1/project/new/';


var substringMatcher = function(strs) {
    return function findMatches(q, cb) {

        // an array that will be populated with substring matches
        var matches = [];

        // regex used to determine if a string contains the substring `q`

        var substrRegex = new RegExp(q, 'i');
        var count = 0;
        // iterate through the pool of strings and for any string that
        // contains the substring `q`, add it to the `matches` array
        $.each(strs, function(i, str) {
            if (substrRegex.test(str.name)) {
                count += 1;
                // the typeahead jQuery plugin expects suggestions to a
                // JavaScript object, refer to typeahead docs for more info
                matches.push({ value: str });

                //alex's hack to limit number of results
                if(count > MAX_RESULTS){
                    return false;
                }
                // above you can return name or a dict of name/node id,
            }
            // add an event to the input box -- listens for keystrokes and if there is a keystroke then it should clearrr
            //
        });

        cb(matches);
    };
};

function initTypeahead(element, nodes, viewModel, params){
    var $inputElem = $(element);
    var myProjects = nodes.map(serializeNode);
    $inputElem.typeahead({
        hint: false,
        highlight: true,
        minLength: 0
    },
    {
        // name: 'projectSearch' + nodeType + namespace,
        displayKey: function(data) {
            return data.value.name;
        },
        templates: {
            suggestion: function(data) {
                return '<p>' + data.value.name + '</p> ' +
                        '<p><small class="m-l-md text-muted">'+
                                        'modified ' + data.value.dateModified.local + '</small></p>';
            }
        },
        source: substringMatcher(myProjects)
    });

    $inputElem.bind('typeahead:selected', function(obj, datum) {
        // Call the parent viewModel's onSelected
        var onSelected = params.onSelected || viewModel.onSelected;
        onSelected(datum.value);
    });
    var onFetched = ko.unwrap(params.onFetched);
    if (onFetched) {
        onFetched(myProjects);
    }
    return $inputElem;
}

// Defines the format of items in the typeahead data source
function serializeNode(node) {
    var dateModified = new $osf.FormattableDate(node.date_modified);
    return {
        name: $osf.htmlDecode(node.title),
        id: node.id,
        dateModified: dateModified,
        urls: {
            web: node.url,
            api: node.api_url,
            register: node.url + 'register',
            files: node.url + 'files/',
            children: node.api_url + 'get_children/?permissions=write'
        }
    };
}

/**
    * Binding handler for attaching an OSF typeahead search input.
    * Takes an optional parameter onSelected, which is called when a project
    * is selected.
    *
    * Params:
    *  data: An Array of data or a URL where to fetch nodes. Defaults to the dashboard node endpoint.
    *  onSelected: Callback for when a node is selected.
    *  onFetched: Callback for when nodes are fetched from server.
    *
    * Example:
    *
    *  <div data-bind="projectSearch: {url: '/api/v1/dashboard/get_nodes/',
    *                                     onSelected: onSelected}></div>
    */
ko.bindingHandlers.projectSearch = {
    update: function(element, valueAccessor, allBindings, viewModel) {
        var params = valueAccessor() || {};
        // Either an Array of nodes or a URL
        var nodesOrURL = ko.unwrap(params.data);
        if (params.clearOn && params.clearOn()) {
            $(element).typeahead('destroy');
            return;
        }
        if (Array.isArray(nodesOrURL)) {
            var nodes = params.data;
            // Compute relevant URLs for each search result.
            initTypeahead(element, nodes, viewModel, params);
        } else if (typeof nodesOrURL === 'string') { // params.data is a URL
            var url = nodesOrURL;
            var request = $.getJSON(url, function (response) {
                // Compute relevant URLs for each search result
                initTypeahead(element, response.nodes, viewModel, params);
            });
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Could not fetch dashboard nodes.', {
                    url: url, textStatus: textStatus, error: error
                });
            });
        }
    }
};

/**
    * ViewModel for the OSF project typeahead search widget.
    *
    * Template: osf-project-search element in components/dashboard_templates.mako
    *
    * Params:
    *  onSubmit: Function to call on submit. Receives the selected item.
    *  onSelected: Function to call when a typeahead selection is made.
    *  onFetchedComponents: Function to call when components for the selected project
    *      are fetched.
    *  onClear: Function to call when the clear button is clicked.
    */
function ProjectSearchViewModel(params) {
    var self = this;
    self.params = params || {};
    self.heading = params.heading;
    // Data passed to the project typehead
    self.data = params.data  || DEFAULT_FETCH_URL;
    self.submitText = params.submitText || 'Submit';
    self.projectPlaceholder = params.projectPlaceholder || 'Type to search for a project';
    self.componentPlaceholder = params.componentPlaceholder || 'Optional: Type to search for a component';

    /* Observables */
    // If params.enableComponents is passed in, use that value, otherwise default to true
    var enableComps = params.enableComponents;
    self.enableComponents = typeof enableComps !== 'undefined' ? enableComps : true;
    self.showComponents = ko.observable(self.enableComponents);
    self.selectedProject = ko.observable(null);
    self.selectedComponent = ko.observable(null);
    self.btnClass = params.btnClass || 'btn btn-primary pull-right';
    // The current user input. we store these so that we can show an error message
    // if the user clicks "Submit" when their selection isn't complete
    self.projectInput = ko.observable('');
    self.componentInput = ko.observable('');

    /* Computeds */
    self.hasSelectedProject = ko.computed(function() {
        return self.selectedProject() !== null;
    });
    self.hasSelectedComponent = ko.computed(function() {
        return self.selectedComponent() !== null;
    });

    self.showSubmit = ko.computed(function() {
        return self.hasSelectedProject();
    });

    // Used by the projectSearch binding to trigger teardown of the component typeahead
    // when the clear button is clicked
    self.cleared = ko.computed(function() {
        return self.selectedProject() == null;
    });

    // Project name to display in the text input
    self.selectedProjectName = ko.computed(function() {
        return self.selectedProject() ? self.selectedProject().name : '';
    });
    // Component name to display in the text input
    self.selectedComponentName = ko.computed(function() {
        return self.selectedComponent() ? self.selectedComponent().name : self.componentInput();
    });

    self.componentURL = ko.computed(function() {
        return self.selectedProject() ? self.selectedProject().urls.children : null;
    });

    /* Functions */
    self.onSubmit = function() {
        var func = params.onSubmit || noop;
        func(self.selectedProject(), self.selectedComponent(), self.projectInput(), self.componentInput());
    };
    self.onSelectedProject = function(selected) {
        self.selectedProject(selected);
        self.projectInput(selected.name);
        var func = params.onSelected || noop;
        func(selected);
    };
    self.onSelectedComponent = function(selected) {
        self.selectedComponent(selected);
        self.componentInput(selected.name);
        var func = params.onSelected || noop;
        func(selected);
    };
    self.onFetchedComponents = function(components) {
        // Show component search only if selected project has components
        self.showComponents(Boolean(components.length));
        var func = params.onFetchedComponents || noop;
        func(components);
    };
    self.clearSearch = function() {
        self.selectedComponent(null);
        self.componentInput('');
        self.selectedProject(null);
        self.projectInput('');
        // This must be set after clearing selectedProject
        // to avoid sending extra request in the projectSearch
        // binding handler
        self.showComponents(true);
        var func = params.onClear || noop;
        func();
    };
    self.clearComponentSearch = function() {
        self.selectedComponent(null);
        self.componentInput('');
        self.showComponents(true);
    };
}

ko.components.register('osf-project-search', {
    viewModel: ProjectSearchViewModel,
    template: {element: 'osf-project-search'}
});


///// Register /////

/**
    * ViewModel for the onboarding project registration component.
    *
    * Template: osf-ob-register element in components/dashboard_templates.mako
    */
function OBRegisterViewModel(params) {
    var self = this;
    self.params = params || {};
    self.data = params.data || DEFAULT_FETCH_URL;
    /* Observables */
    self.isOpen = ko.observable(false);
    /* Functions */
    self.open = function() {
        self.isOpen(true);
    };
    self.close = function() {
        self.isOpen(false);
    };
    self.toggle = function() {
        if (!self.isOpen()) {
            self.open();
        } else {
            self.close();
        }
    };
    /* On submit, redirect to the selected page's registration page */
    self.onRegisterSubmit = function(selected) {
        window.location = selected.urls.register;
    };
}

ko.components.register('osf-ob-register', {
    viewModel: OBRegisterViewModel,
    template: {element: 'osf-ob-register'}
});

///// UPLOADER //////
var iconList = [
'_blank',
'_page',
'aac',
'ai',
'aiff',
'avi',
'bmp',
'c',
'cpp',
'css',
'dat',
'dmg',
'doc',
'dotx',
'dwg',
'dxf',
'eps',
'exe',
'flv',
'gif',
'h',
'hpp',
'html',
'ics',
'iso',
'java',
'jpg',
'js',
'key',
'less',
'mid',
'mp3',
'mp4',
'mpg',
'odf',
'ods',
'odt',
'otp',
'ots',
'ott',
'pdf',
'php',
'png',
'ppt',
'psd',
'py',
'qt',
'rar',
'rb',
'rtf',
'sass',
'scss',
'sql',
'tga',
'tgz',
'tiff',
'txt',
'wav',
'xls',
'xlsx',
'xml',
'yml',
'zip'
];

// this takes a filename and finds the icon for it
function getFiletypeIcon(file_name){
    var baseUrl ='/static/img/upload_icons/';
    var ext = file_name.split('.').pop().toLowerCase();
    if(iconList.indexOf(ext)  !== -1){
        return baseUrl + ext + '.png';
    }else{
        return baseUrl + '_blank.png';
    }
}

// if has an extention return it, else return the last three chars
function getExtension(string){
    if(string.indexOf('.') !== -1){
        return string.split('.').pop().toLowerCase();
    }else{
        return string.substring(string.length - 3);
    }
}

// truncate long file names
function truncateFilename(string){
    var ext = getExtension(string);
    if (string.length > 40){
        return string.substring(0, 40-ext.length-3) + '...' + ext;
    } else{
        return string;
    }
}

/**
    * ViewModel for the onboarding uploader
    */
function OBUploaderViewModel(params) {
    var self = this;
    self.params = params || {};
    self.selector = self.params.selector || '#obDropzone';
    self.data = params.data || DEFAULT_FETCH_URL;
    /* Observables */
    self.isOpen = ko.observable(true);
    self.progress = ko.observable(0);
    self.showProgress = ko.observable(false);
    self.errorMessage = ko.observable('');
    self.enableUpload = ko.observable(true);
    self.filename = ko.observable('');
    self.iconSrc = ko.observable('');
    self.newProjectName = ko.observable(null);
    self.uploadCount = ko.observable(1);
    self.disableComponents = ko.observable(false);
    self.createAndUpload = ko.observable(true);
    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');
    // The target node to upload to to
    self.target = ko.observable(null);
    //Boolean to track if upload was successful
    self.success = false;
    /* Functions */
    self.toggle = function() {
        self.isOpen(!self.isOpen());
    };
    self.startUpload = function(selectedProject, selectedComponent, projectInput, componentInput) {
        if (!selectedComponent && componentInput.length) {
            var msg = 'Not a valid component selection. Clear your search or select a component from the dropdown.';
            self.changeMessage(msg, 'text-warning');
            return false;
        }
        if (self.dropzone.getUploadingFiles().length) {
            self.changeMessage('Please wait until the pending uploads are finished.');
            return false;
        }
        if (!self.dropzone.getQueuedFiles().length) {
            self.changeMessage('Please select at least one file to upload.', 'text-danger');
            return false;
        }
        var selected = selectedComponent || selectedProject;
        self.target(selected);
        self.clearMessages();
        self.showProgress(true);
        self.dropzone.options.url = function(files) {
            //Files is always an array but we only support uploading a single file at once
            var file = files[0];
            return waterbutler.buildUploadUrl('/', 'osfstorage', selected.id, file);
        };
        self.dropzone.processQueue(); // Tell Dropzone to process all queued files.
    };
    self.clearMessages = function() {
        self.message('');
        self.messageClass('text-info');
    };

    self.showCreateAndUpload = function() {
        self.clearMessages();
        self.createAndUpload(true);
    };

    self.hideCreateAndUpload = function(selected) {
        self.clearMessages();
        self.createAndUpload(false);
    };

    self.clearDropzone = function() {
        if (self.dropzone.getUploadingFiles().length) {
            self.changeMessage('Upload canceled.', 'text-info');
        } else {
            self.clearMessages();
        }
        self.enableUpload(true);
        // Pass true so that pending uploads are canceled
        self.dropzone.removeAllFiles(true);
        self.filename('');
        self.iconSrc('');
        self.progress = ko.observable(0);
        self.showProgress(false);
        self.uploadCount(1);
    };
    self.onFetchedComponents = function(components) {
        if (!components.length) {
            self.disableComponents(true);
        }
    };
    /** Change the flashed message. */
    self.changeMessage = function(text, css, timeout) {
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(function() {
                self.clearMessages();
            }, timeout);
        }
    };

    var dropzoneOpts = {

        sending: function(file, xhr) {
            //Inject Bearer token
            xhr = $osf.setXHRAuthorization(xhr);
            //Hack to remove webkitheaders
            var _send = xhr.send;
            xhr.send = function() {
                _send.call(xhr, file);
            };
        },

        clickable: '#obDropzone',
        url: '/', // specified per upload
        autoProcessQueue: false,
        createImageThumbnails: false,
        //over
        maxFiles: 9001,
        uploadMultiple: false,
        //in mib
        maxFilesize: 128,

        acceptDirectories: false,

        method: 'PUT',
        uploadprogress: function(file, progress) { // progress bar update
            self.progress(progress);
        },
        parallelUploads: 1,
        // Don't use dropzone's default preview
        previewsContainer: false,
        // Custom error messages
        dictFileTooBig: 'File is too big ({{filesize}} MB). Max filesize: {{maxFilesize}} MB.',
        // Set up listeners on initialization
        init: function() {
            var dropzone = this;

            // file add error logic
            this.on('error', function(file, message){
                dropzone.removeFile(file);
                if (dropzone.files.length === 0){
                    self.enableUpload(true);
                    dropzone.removeAllFiles(true);
                }

                if(message.message) {
                    message = JSON.parse(message.message);
                }

                // Use OSF-provided error message if possible
                // Otherwise, use generic message
                var msg = message.message_long || message;
                if (msg === 'Server responded with 0 code.' || msg.indexOf('409') !== -1) {
                    msg = 'Could not upload file. The file may be invalid.';
                }
                self.changeMessage(msg, 'text-danger');
            });
            this.on('drop',function(){ // clear errors on drop or click
                self.clearMessages();
            });
            // upload and process queue logic
            this.on('success',function(){
                self.filename(self.uploadCount() + ' / ' + dropzone.files.length + ' files');
                dropzone.processQueue(); // this is a bit hackish -- it fails to process full queue but this ensures it runs the process again after each success.
                var oldCount = self.uploadCount();
                self.uploadCount(oldCount + 1);

                if(self.uploadCount() > dropzone.files.length){ // when finished redirect to project/component page where uploaded.
                    self.success = true;
                    self.changeMessage('Success!', 'text-success');
                    window.location = self.target().urls.files;
                }
            });

            // add file logic and dropzone to file display swap
            this.on('addedfile', function(file) {
                if(dropzone.files.length > 1){
                    self.iconSrc('/static/img/upload_icons/multiple_blank.png');
                    self.filename(dropzone.files.length + ' files');
                }else{
                    var fileName = truncateFilename(dropzone.files[0].name);
                    self.iconSrc(getFiletypeIcon(fileName));
                    self.filename(fileName);
                }
                self.enableUpload(false);
            });
        }
    };
    self.dropzone = new Dropzone(self.selector, dropzoneOpts);

    //Drag & drop is non-functional in IE; change instructional header to indicate this to the user.
    if($osf.isIE()){
        $('#obDropzone-header').replaceWith('<h4 id=\'obDropzone-header\'>1. Click below to select file</h4>');
    }

    //stop user from leaving if file is staged for upload
    $(window).on('beforeunload', function() {
        if(!self.enableUpload() && !self.success) {
            return 'You have a pending upload. If you leave ' +
                'the page now, your file will not be stored.';
        }
    });

    self.submitCreateAndUpload = function() {
        if (!self.dropzone.getQueuedFiles().length) {
            self.changeMessage('Please select at least one file to upload.', 'text-danger');
            return false;
        }
        if (self.newProjectName() === null || self.newProjectName().trim() === '') {
            self.changeMessage('Please select a project.', 'text-danger');
            return false;
        }
        if (self.newProjectName() && self.dropzone.getQueuedFiles().length !== 0) {
            var request = $osf.postJSON(
                CREATE_URL,
                {
                    title: self.newProjectName()
                }
            );
            request.done(self.createSuccess);
            request.fail(self.createFailure);
        }
    };

    self.createSuccess = function(response) {
        var node = serializeNode(response.newNode);
        self.startUpload(node, self.selectedComponent, node.title, '');
    };

    self.createFailure = function(xhr, textStatus, error) {
         Raven.captureMessage('Could not create a new project.', {
            textStatus: textStatus,
            error: error
         });
    };
}
ko.components.register('osf-ob-uploader', {
    viewModel: OBUploaderViewModel,
    template: {element: 'osf-ob-uploader'}
});


function OBGoToViewModel(params) {
    var self = this;
    self.params = params;
    self.data = params.data || DEFAULT_FETCH_URL;
    /* Observables */
    self.isOpen = ko.observable(true);
    self.hasFocus = ko.observable(true);
        self.submitText = '<i class="fa fa-angle-double-right"></i> Go';
    /* Functions */
    self.toggle = function() {
        if (!self.isOpen()) {
            self.isOpen(true);
            self.hasFocus = ko.observable(true);
        } else {
            self.isOpen(false);
            self.hasFocus = ko.observable(false);
        }
    };
    self.onSubmit = function(selectedProject, selectedComponent) {
        var node = selectedComponent || selectedProject;
        window.location = node.urls.web;
    };
}

ko.components.register('osf-ob-goto', {
    viewModel: OBGoToViewModel,
    template: {element: 'osf-ob-goto'}
});


function ProjectCreateViewModel(response) {
    var self = this;
    self.isOpen = ko.observable(false);
    self.focus = ko.observable(false);
    self.toggle = function() {
        self.isOpen(!self.isOpen());
        self.focus(self.isOpen());
    };
    self.nodes = response.data;
}

ko.components.register('osf-ob-create', {
    viewModel: ProjectCreateViewModel,
    template: {element: 'osf-ob-create'}
});

/***/ },

/***/ 168:
/***/ function(module, exports, __webpack_require__) {

// style-loader: Adds some css to the DOM by adding a <style> tag

// load the styles
var content = __webpack_require__(169);
if(typeof content === 'string') content = [[module.id, content, '']];
// add the styles to the DOM
var update = __webpack_require__(19)(content, {});
// Hot Module Replacement
if(false) {
	// When the styles change, update the <style> tags
	module.hot.accept("!!/Users/laurenbarker/GitHub/osf.io/node_modules/css-loader/index.js!/Users/laurenbarker/GitHub/osf.io/website/static/css/onboarding.css", function() {
		var newContent = require("!!/Users/laurenbarker/GitHub/osf.io/node_modules/css-loader/index.js!/Users/laurenbarker/GitHub/osf.io/website/static/css/onboarding.css");
		if(typeof newContent === 'string') newContent = [[module.id, newContent, '']];
		update(newContent);
	});
	// When the module is disposed, remove the <style> tags
	module.hot.dispose(function() { update(); });
}

/***/ },

/***/ 169:
/***/ function(module, exports, __webpack_require__) {

exports = module.exports = __webpack_require__(16)();
exports.push([module.id, "/* class css */\n.ob-heading {\n\tdisplay:inline;\n}\n\n.ob-search{\n\tposition:relative;\n}\n\n.ob-expand-icon{\n\tmargin-top:6px;\n\theight: 14px;\n}\n\nul.ob-widget-list {\n    padding: 0;\n}\n\n.ob-reveal {\n\tdisplay: none;\n}\n\n.ob-reveal-btn {\n\theight: 100%;\n\twidth: 100%;\n}\n\n.ob-dropzone-box {\n\tposition:relative;\n\theight: 150px;\n\twidth: 100%;\n\tfont-size: 12px;\n\ttext-align: center;\n\tcursor: pointer;\n}\n\n.ob-clear-button{\n\tposition: absolute;\n\tz-index: 1;\n\ttop: -5px;\n\tright: -12px;\n}\n\n.ob-input {\n    position: relative;\n}\n\n.ob-clear-uploads-button{\n\tposition: relative;\n\tz-index: 1;\n\ttop: -140px;\n\tright: -12px;\n}\n\n.ob-unselectable{\n\t-webkit-user-select: none; /* Chrome/Safari */\n\t-moz-user-select: none; /* Firefox */\n\t-ms-user-select: none; /* IE10+ */\n\n\t/* Rules below not implemented in browsers yet */\n\t-o-user-select: none;\n\tuser-select: none;\n}\n\n.ob-clear-button:hover{\n\tcursor: pointer;\n}\n\n/*this exists to force sizing properly as typeahead tries desperately to overwrite it...*/\n.twitter-typeahead{\n\tdisplay: block !important;\n}\n\n.ob-dropzone{\n\tbackground-image: url(\"/static/img/upload.png\");\n\tbackground-repeat:no-repeat;\n\tbackground-size: 60px 60px;\n\n\tbackground-position:center;\n}\n\ndiv.ob-dropzone-selected{\n\tborder: solid 2px #3C763D;\n\tbackground-color:  #f5f5f5;\n}\n\nimg.ob-dropzone-icon{\n\theight:90px;\n\tmargin-left:auto;\n\tmargin-right:auto;\n}\n\n.ob-upload-progress {\n\ttext-align: center;\n}\n\n.resize-vertical{\n    resize:vertical;\n}", ""]);

/***/ },

/***/ 170:
/***/ function(module, exports, __webpack_require__) {

// style-loader: Adds some css to the DOM by adding a <style> tag

// load the styles
var content = __webpack_require__(171);
if(typeof content === 'string') content = [[module.id, content, '']];
// add the styles to the DOM
var update = __webpack_require__(19)(content, {});
// Hot Module Replacement
if(false) {
	// When the styles change, update the <style> tags
	module.hot.accept("!!/Users/laurenbarker/GitHub/osf.io/node_modules/css-loader/index.js!/Users/laurenbarker/GitHub/osf.io/website/static/css/typeahead.css", function() {
		var newContent = require("!!/Users/laurenbarker/GitHub/osf.io/node_modules/css-loader/index.js!/Users/laurenbarker/GitHub/osf.io/website/static/css/typeahead.css");
		if(typeof newContent === 'string') newContent = [[module.id, newContent, '']];
		update(newContent);
	});
	// When the module is disposed, remove the <style> tags
	module.hot.dispose(function() { update(); });
}

/***/ },

/***/ 171:
/***/ function(module, exports, __webpack_require__) {

exports = module.exports = __webpack_require__(16)();
exports.push([module.id, "/* Typeahead autocomplete box */\n\ninput.typeahead.tt-input {\n    width: 100%;\n    height: 110%;\n}\n\n.organize-project-controls span.twitter-typeahead {\n    width: 100%;\n\n}\n\n/* Typeahead scaffolding */\n/* ----------- */\n\n.tt-dropdown-menu,\n.gist {\n    text-align: left;\n}\n\n/* Typeahead base styles */\n/* ----------- */\n\n.typeahead,\n.tt-query,\n.tt-hint {\n    width: 100%;\n    height: 30px;\n    padding: 8px 12px;\n    font-size: 14px;\n    border: 2px solid #ccc;\n    -webkit-border-radius: 8px;\n    -moz-border-radius: 8px;\n    border-radius: 8px;\n    outline: none;\n}\n\n.typeahead {\n    background-color: #fff;\n}\n\n.tt-query {\n    -webkit-box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.075);\n    -moz-box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.075);\n    box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.075);\n}\n\n.tt-hint {\n    color: #999;\n\tpadding-top: 21px;\n}\n\n.tt-dropdown-menu {\n    /*display:inline-block;*/\n    width:100%;\n    /*width: 422px;*/\n    padding: 8px 0;\n    background-color: #fff;\n    border: 1px solid #ccc;\n    border: 1px solid rgba(0, 0, 0, 0.2);\n    -webkit-border-radius: 8px;\n    -moz-border-radius: 8px;\n    border-radius: 8px;\n    -webkit-box-shadow: 0 5px 10px rgba(0, 0, 0, .2);\n    -moz-box-shadow: 0 5px 10px rgba(0, 0, 0, .2);\n    box-shadow: 0 5px 10px rgba(0, 0, 0, .2);\n\tmargin-top: 12px;\n\tcursor: pointer;\n}\n\n.tt-suggestion:hover .text-muted{\n    color: white;\n}\n\n.tt-suggestion {\n    padding: 3px 20px;\n    font-size: 14px;\n    line-height: 24px;\n}\n\n.tt-suggestion.tt-cursor {\n    color: #fff;\n    background-color: #0097cf;\n\n}\n\n.tt-suggestion p {\n    margin: 0;\n}\n\n.gist {\n    font-size: 14px;\n}", ""]);

/***/ },

/***/ 172:
/***/ function(module, exports, __webpack_require__) {

/* WEBPACK VAR INJECTION */(function(setImmediate) {/*!
 * typeahead.js 0.10.5
 * https://github.com/twitter/typeahead.js
 * Copyright 2013-2014 Twitter, Inc. and other contributors; Licensed MIT
 */

(function($) {
    var _ = function() {
        "use strict";
        return {
            isMsie: function() {
                return /(msie|trident)/i.test(navigator.userAgent) ? navigator.userAgent.match(/(msie |rv:)(\d+(.\d+)?)/i)[2] : false;
            },
            isBlankString: function(str) {
                return !str || /^\s*$/.test(str);
            },
            escapeRegExChars: function(str) {
                return str.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&");
            },
            isString: function(obj) {
                return typeof obj === "string";
            },
            isNumber: function(obj) {
                return typeof obj === "number";
            },
            isArray: $.isArray,
            isFunction: $.isFunction,
            isObject: $.isPlainObject,
            isUndefined: function(obj) {
                return typeof obj === "undefined";
            },
            toStr: function toStr(s) {
                return _.isUndefined(s) || s === null ? "" : s + "";
            },
            bind: $.proxy,
            each: function(collection, cb) {
                $.each(collection, reverseArgs);
                function reverseArgs(index, value) {
                    return cb(value, index);
                }
            },
            map: $.map,
            filter: $.grep,
            every: function(obj, test) {
                var result = true;
                if (!obj) {
                    return result;
                }
                $.each(obj, function(key, val) {
                    if (!(result = test.call(null, val, key, obj))) {
                        return false;
                    }
                });
                return !!result;
            },
            some: function(obj, test) {
                var result = false;
                if (!obj) {
                    return result;
                }
                $.each(obj, function(key, val) {
                    if (result = test.call(null, val, key, obj)) {
                        return false;
                    }
                });
                return !!result;
            },
            mixin: $.extend,
            getUniqueId: function() {
                var counter = 0;
                return function() {
                    return counter++;
                };
            }(),
            templatify: function templatify(obj) {
                return $.isFunction(obj) ? obj : template;
                function template() {
                    return String(obj);
                }
            },
            defer: function(fn) {
                setTimeout(fn, 0);
            },
            debounce: function(func, wait, immediate) {
                var timeout, result;
                return function() {
                    var context = this, args = arguments, later, callNow;
                    later = function() {
                        timeout = null;
                        if (!immediate) {
                            result = func.apply(context, args);
                        }
                    };
                    callNow = immediate && !timeout;
                    clearTimeout(timeout);
                    timeout = setTimeout(later, wait);
                    if (callNow) {
                        result = func.apply(context, args);
                    }
                    return result;
                };
            },
            throttle: function(func, wait) {
                var context, args, timeout, result, previous, later;
                previous = 0;
                later = function() {
                    previous = new Date();
                    timeout = null;
                    result = func.apply(context, args);
                };
                return function() {
                    var now = new Date(), remaining = wait - (now - previous);
                    context = this;
                    args = arguments;
                    if (remaining <= 0) {
                        clearTimeout(timeout);
                        timeout = null;
                        previous = now;
                        result = func.apply(context, args);
                    } else if (!timeout) {
                        timeout = setTimeout(later, remaining);
                    }
                    return result;
                };
            },
            noop: function() {}
        };
    }();
    var VERSION = "0.10.5";
    var tokenizers = function() {
        "use strict";
        return {
            nonword: nonword,
            whitespace: whitespace,
            obj: {
                nonword: getObjTokenizer(nonword),
                whitespace: getObjTokenizer(whitespace)
            }
        };
        function whitespace(str) {
            str = _.toStr(str);
            return str ? str.split(/\s+/) : [];
        }
        function nonword(str) {
            str = _.toStr(str);
            return str ? str.split(/\W+/) : [];
        }
        function getObjTokenizer(tokenizer) {
            return function setKey() {
                var args = [].slice.call(arguments, 0);
                return function tokenize(o) {
                    var tokens = [];
                    _.each(args, function(k) {
                        tokens = tokens.concat(tokenizer(_.toStr(o[k])));
                    });
                    return tokens;
                };
            };
        }
    }();
    var LruCache = function() {
        "use strict";
        function LruCache(maxSize) {
            this.maxSize = _.isNumber(maxSize) ? maxSize : 100;
            this.reset();
            if (this.maxSize <= 0) {
                this.set = this.get = $.noop;
            }
        }
        _.mixin(LruCache.prototype, {
            set: function set(key, val) {
                var tailItem = this.list.tail, node;
                if (this.size >= this.maxSize) {
                    this.list.remove(tailItem);
                    delete this.hash[tailItem.key];
                }
                if (node = this.hash[key]) {
                    node.val = val;
                    this.list.moveToFront(node);
                } else {
                    node = new Node(key, val);
                    this.list.add(node);
                    this.hash[key] = node;
                    this.size++;
                }
            },
            get: function get(key) {
                var node = this.hash[key];
                if (node) {
                    this.list.moveToFront(node);
                    return node.val;
                }
            },
            reset: function reset() {
                this.size = 0;
                this.hash = {};
                this.list = new List();
            }
        });
        function List() {
            this.head = this.tail = null;
        }
        _.mixin(List.prototype, {
            add: function add(node) {
                if (this.head) {
                    node.next = this.head;
                    this.head.prev = node;
                }
                this.head = node;
                this.tail = this.tail || node;
            },
            remove: function remove(node) {
                node.prev ? node.prev.next = node.next : this.head = node.next;
                node.next ? node.next.prev = node.prev : this.tail = node.prev;
            },
            moveToFront: function(node) {
                this.remove(node);
                this.add(node);
            }
        });
        function Node(key, val) {
            this.key = key;
            this.val = val;
            this.prev = this.next = null;
        }
        return LruCache;
    }();
    var PersistentStorage = function() {
        "use strict";
        var ls, methods;
        try {
            ls = window.localStorage;
            ls.setItem("~~~", "!");
            ls.removeItem("~~~");
        } catch (err) {
            ls = null;
        }
        function PersistentStorage(namespace) {
            this.prefix = [ "__", namespace, "__" ].join("");
            this.ttlKey = "__ttl__";
            this.keyMatcher = new RegExp("^" + _.escapeRegExChars(this.prefix));
        }
        if (ls && window.JSON) {
            methods = {
                _prefix: function(key) {
                    return this.prefix + key;
                },
                _ttlKey: function(key) {
                    return this._prefix(key) + this.ttlKey;
                },
                get: function(key) {
                    if (this.isExpired(key)) {
                        this.remove(key);
                    }
                    return decode(ls.getItem(this._prefix(key)));
                },
                set: function(key, val, ttl) {
                    if (_.isNumber(ttl)) {
                        ls.setItem(this._ttlKey(key), encode(now() + ttl));
                    } else {
                        ls.removeItem(this._ttlKey(key));
                    }
                    return ls.setItem(this._prefix(key), encode(val));
                },
                remove: function(key) {
                    ls.removeItem(this._ttlKey(key));
                    ls.removeItem(this._prefix(key));
                    return this;
                },
                clear: function() {
                    var i, key, keys = [], len = ls.length;
                    for (i = 0; i < len; i++) {
                        if ((key = ls.key(i)).match(this.keyMatcher)) {
                            keys.push(key.replace(this.keyMatcher, ""));
                        }
                    }
                    for (i = keys.length; i--; ) {
                        this.remove(keys[i]);
                    }
                    return this;
                },
                isExpired: function(key) {
                    var ttl = decode(ls.getItem(this._ttlKey(key)));
                    return _.isNumber(ttl) && now() > ttl ? true : false;
                }
            };
        } else {
            methods = {
                get: _.noop,
                set: _.noop,
                remove: _.noop,
                clear: _.noop,
                isExpired: _.noop
            };
        }
        _.mixin(PersistentStorage.prototype, methods);
        return PersistentStorage;
        function now() {
            return new Date().getTime();
        }
        function encode(val) {
            return JSON.stringify(_.isUndefined(val) ? null : val);
        }
        function decode(val) {
            return JSON.parse(val);
        }
    }();
    var Transport = function() {
        "use strict";
        var pendingRequestsCount = 0, pendingRequests = {}, maxPendingRequests = 6, sharedCache = new LruCache(10);
        function Transport(o) {
            o = o || {};
            this.cancelled = false;
            this.lastUrl = null;
            this._send = o.transport ? callbackToDeferred(o.transport) : $.ajax;
            this._get = o.rateLimiter ? o.rateLimiter(this._get) : this._get;
            this._cache = o.cache === false ? new LruCache(0) : sharedCache;
        }
        Transport.setMaxPendingRequests = function setMaxPendingRequests(num) {
            maxPendingRequests = num;
        };
        Transport.resetCache = function resetCache() {
            sharedCache.reset();
        };
        _.mixin(Transport.prototype, {
            _get: function(url, o, cb) {
                var that = this, jqXhr;
                if (this.cancelled || url !== this.lastUrl) {
                    return;
                }
                if (jqXhr = pendingRequests[url]) {
                    jqXhr.done(done).fail(fail);
                } else if (pendingRequestsCount < maxPendingRequests) {
                    pendingRequestsCount++;
                    pendingRequests[url] = this._send(url, o).done(done).fail(fail).always(always);
                } else {
                    this.onDeckRequestArgs = [].slice.call(arguments, 0);
                }
                function done(resp) {
                    cb && cb(null, resp);
                    that._cache.set(url, resp);
                }
                function fail() {
                    cb && cb(true);
                }
                function always() {
                    pendingRequestsCount--;
                    delete pendingRequests[url];
                    if (that.onDeckRequestArgs) {
                        that._get.apply(that, that.onDeckRequestArgs);
                        that.onDeckRequestArgs = null;
                    }
                }
            },
            get: function(url, o, cb) {
                var resp;
                if (_.isFunction(o)) {
                    cb = o;
                    o = {};
                }
                this.cancelled = false;
                this.lastUrl = url;
                if (resp = this._cache.get(url)) {
                    _.defer(function() {
                        cb && cb(null, resp);
                    });
                } else {
                    this._get(url, o, cb);
                }
                return !!resp;
            },
            cancel: function() {
                this.cancelled = true;
            }
        });
        return Transport;
        function callbackToDeferred(fn) {
            return function customSendWrapper(url, o) {
                var deferred = $.Deferred();
                fn(url, o, onSuccess, onError);
                return deferred;
                function onSuccess(resp) {
                    _.defer(function() {
                        deferred.resolve(resp);
                    });
                }
                function onError(err) {
                    _.defer(function() {
                        deferred.reject(err);
                    });
                }
            };
        }
    }();
    var SearchIndex = function() {
        "use strict";
        function SearchIndex(o) {
            o = o || {};
            if (!o.datumTokenizer || !o.queryTokenizer) {
                $.error("datumTokenizer and queryTokenizer are both required");
            }
            this.datumTokenizer = o.datumTokenizer;
            this.queryTokenizer = o.queryTokenizer;
            this.reset();
        }
        _.mixin(SearchIndex.prototype, {
            bootstrap: function bootstrap(o) {
                this.datums = o.datums;
                this.trie = o.trie;
            },
            add: function(data) {
                var that = this;
                data = _.isArray(data) ? data : [ data ];
                _.each(data, function(datum) {
                    var id, tokens;
                    id = that.datums.push(datum) - 1;
                    tokens = normalizeTokens(that.datumTokenizer(datum));
                    _.each(tokens, function(token) {
                        var node, chars, ch;
                        node = that.trie;
                        chars = token.split("");
                        while (ch = chars.shift()) {
                            node = node.children[ch] || (node.children[ch] = newNode());
                            node.ids.push(id);
                        }
                    });
                });
            },
            get: function get(query) {
                var that = this, tokens, matches;
                tokens = normalizeTokens(this.queryTokenizer(query));
                _.each(tokens, function(token) {
                    var node, chars, ch, ids;
                    if (matches && matches.length === 0) {
                        return false;
                    }
                    node = that.trie;
                    chars = token.split("");
                    while (node && (ch = chars.shift())) {
                        node = node.children[ch];
                    }
                    if (node && chars.length === 0) {
                        ids = node.ids.slice(0);
                        matches = matches ? getIntersection(matches, ids) : ids;
                    } else {
                        matches = [];
                        return false;
                    }
                });
                return matches ? _.map(unique(matches), function(id) {
                    return that.datums[id];
                }) : [];
            },
            reset: function reset() {
                this.datums = [];
                this.trie = newNode();
            },
            serialize: function serialize() {
                return {
                    datums: this.datums,
                    trie: this.trie
                };
            }
        });
        return SearchIndex;
        function normalizeTokens(tokens) {
            tokens = _.filter(tokens, function(token) {
                return !!token;
            });
            tokens = _.map(tokens, function(token) {
                return token.toLowerCase();
            });
            return tokens;
        }
        function newNode() {
            return {
                ids: [],
                children: {}
            };
        }
        function unique(array) {
            var seen = {}, uniques = [];
            for (var i = 0, len = array.length; i < len; i++) {
                if (!seen[array[i]]) {
                    seen[array[i]] = true;
                    uniques.push(array[i]);
                }
            }
            return uniques;
        }
        function getIntersection(arrayA, arrayB) {
            var ai = 0, bi = 0, intersection = [];
            arrayA = arrayA.sort(compare);
            arrayB = arrayB.sort(compare);
            var lenArrayA = arrayA.length, lenArrayB = arrayB.length;
            while (ai < lenArrayA && bi < lenArrayB) {
                if (arrayA[ai] < arrayB[bi]) {
                    ai++;
                } else if (arrayA[ai] > arrayB[bi]) {
                    bi++;
                } else {
                    intersection.push(arrayA[ai]);
                    ai++;
                    bi++;
                }
            }
            return intersection;
            function compare(a, b) {
                return a - b;
            }
        }
    }();
    var oParser = function() {
        "use strict";
        return {
            local: getLocal,
            prefetch: getPrefetch,
            remote: getRemote
        };
        function getLocal(o) {
            return o.local || null;
        }
        function getPrefetch(o) {
            var prefetch, defaults;
            defaults = {
                url: null,
                thumbprint: "",
                ttl: 24 * 60 * 60 * 1e3,
                filter: null,
                ajax: {}
            };
            if (prefetch = o.prefetch || null) {
                prefetch = _.isString(prefetch) ? {
                    url: prefetch
                } : prefetch;
                prefetch = _.mixin(defaults, prefetch);
                prefetch.thumbprint = VERSION + prefetch.thumbprint;
                prefetch.ajax.type = prefetch.ajax.type || "GET";
                prefetch.ajax.dataType = prefetch.ajax.dataType || "json";
                !prefetch.url && $.error("prefetch requires url to be set");
            }
            return prefetch;
        }
        function getRemote(o) {
            var remote, defaults;
            defaults = {
                url: null,
                cache: true,
                wildcard: "%QUERY",
                replace: null,
                rateLimitBy: "debounce",
                rateLimitWait: 300,
                send: null,
                filter: null,
                ajax: {}
            };
            if (remote = o.remote || null) {
                remote = _.isString(remote) ? {
                    url: remote
                } : remote;
                remote = _.mixin(defaults, remote);
                remote.rateLimiter = /^throttle$/i.test(remote.rateLimitBy) ? byThrottle(remote.rateLimitWait) : byDebounce(remote.rateLimitWait);
                remote.ajax.type = remote.ajax.type || "GET";
                remote.ajax.dataType = remote.ajax.dataType || "json";
                delete remote.rateLimitBy;
                delete remote.rateLimitWait;
                !remote.url && $.error("remote requires url to be set");
            }
            return remote;
            function byDebounce(wait) {
                return function(fn) {
                    return _.debounce(fn, wait);
                };
            }
            function byThrottle(wait) {
                return function(fn) {
                    return _.throttle(fn, wait);
                };
            }
        }
    }();
    (function(root) {
        "use strict";
        var old, keys;
        old = root.Bloodhound;
        keys = {
            data: "data",
            protocol: "protocol",
            thumbprint: "thumbprint"
        };
        root.Bloodhound = Bloodhound;
        function Bloodhound(o) {
            if (!o || !o.local && !o.prefetch && !o.remote) {
                $.error("one of local, prefetch, or remote is required");
            }
            this.limit = o.limit || 5;
            this.sorter = getSorter(o.sorter);
            this.dupDetector = o.dupDetector || ignoreDuplicates;
            this.local = oParser.local(o);
            this.prefetch = oParser.prefetch(o);
            this.remote = oParser.remote(o);
            this.cacheKey = this.prefetch ? this.prefetch.cacheKey || this.prefetch.url : null;
            this.index = new SearchIndex({
                datumTokenizer: o.datumTokenizer,
                queryTokenizer: o.queryTokenizer
            });
            this.storage = this.cacheKey ? new PersistentStorage(this.cacheKey) : null;
        }
        Bloodhound.noConflict = function noConflict() {
            root.Bloodhound = old;
            return Bloodhound;
        };
        Bloodhound.tokenizers = tokenizers;
        _.mixin(Bloodhound.prototype, {
            _loadPrefetch: function loadPrefetch(o) {
                var that = this, serialized, deferred;
                if (serialized = this._readFromStorage(o.thumbprint)) {
                    this.index.bootstrap(serialized);
                    deferred = $.Deferred().resolve();
                } else {
                    deferred = $.ajax(o.url, o.ajax).done(handlePrefetchResponse);
                }
                return deferred;
                function handlePrefetchResponse(resp) {
                    that.clear();
                    that.add(o.filter ? o.filter(resp) : resp);
                    that._saveToStorage(that.index.serialize(), o.thumbprint, o.ttl);
                }
            },
            _getFromRemote: function getFromRemote(query, cb) {
                var that = this, url, uriEncodedQuery;
                if (!this.transport) {
                    return;
                }
                query = query || "";
                uriEncodedQuery = encodeURIComponent(query);
                url = this.remote.replace ? this.remote.replace(this.remote.url, query) : this.remote.url.replace(this.remote.wildcard, uriEncodedQuery);
                return this.transport.get(url, this.remote.ajax, handleRemoteResponse);
                function handleRemoteResponse(err, resp) {
                    err ? cb([]) : cb(that.remote.filter ? that.remote.filter(resp) : resp);
                }
            },
            _cancelLastRemoteRequest: function cancelLastRemoteRequest() {
                this.transport && this.transport.cancel();
            },
            _saveToStorage: function saveToStorage(data, thumbprint, ttl) {
                if (this.storage) {
                    this.storage.set(keys.data, data, ttl);
                    this.storage.set(keys.protocol, location.protocol, ttl);
                    this.storage.set(keys.thumbprint, thumbprint, ttl);
                }
            },
            _readFromStorage: function readFromStorage(thumbprint) {
                var stored = {}, isExpired;
                if (this.storage) {
                    stored.data = this.storage.get(keys.data);
                    stored.protocol = this.storage.get(keys.protocol);
                    stored.thumbprint = this.storage.get(keys.thumbprint);
                }
                isExpired = stored.thumbprint !== thumbprint || stored.protocol !== location.protocol;
                return stored.data && !isExpired ? stored.data : null;
            },
            _initialize: function initialize() {
                var that = this, local = this.local, deferred;
                deferred = this.prefetch ? this._loadPrefetch(this.prefetch) : $.Deferred().resolve();
                local && deferred.done(addLocalToIndex);
                this.transport = this.remote ? new Transport(this.remote) : null;
                return this.initPromise = deferred.promise();
                function addLocalToIndex() {
                    that.add(_.isFunction(local) ? local() : local);
                }
            },
            initialize: function initialize(force) {
                return !this.initPromise || force ? this._initialize() : this.initPromise;
            },
            add: function add(data) {
                this.index.add(data);
            },
            get: function get(query, cb) {
                var that = this, matches = [], cacheHit = false;
                matches = this.index.get(query);
                matches = this.sorter(matches).slice(0, this.limit);
                matches.length < this.limit ? cacheHit = this._getFromRemote(query, returnRemoteMatches) : this._cancelLastRemoteRequest();
                if (!cacheHit) {
                    (matches.length > 0 || !this.transport) && cb && cb(matches);
                }
                function returnRemoteMatches(remoteMatches) {
                    var matchesWithBackfill = matches.slice(0);
                    _.each(remoteMatches, function(remoteMatch) {
                        var isDuplicate;
                        isDuplicate = _.some(matchesWithBackfill, function(match) {
                            return that.dupDetector(remoteMatch, match);
                        });
                        !isDuplicate && matchesWithBackfill.push(remoteMatch);
                        return matchesWithBackfill.length < that.limit;
                    });
                    cb && cb(that.sorter(matchesWithBackfill));
                }
            },
            clear: function clear() {
                this.index.reset();
            },
            clearPrefetchCache: function clearPrefetchCache() {
                this.storage && this.storage.clear();
            },
            clearRemoteCache: function clearRemoteCache() {
                this.transport && Transport.resetCache();
            },
            ttAdapter: function ttAdapter() {
                return _.bind(this.get, this);
            }
        });
        return Bloodhound;
        function getSorter(sortFn) {
            return _.isFunction(sortFn) ? sort : noSort;
            function sort(array) {
                return array.sort(sortFn);
            }
            function noSort(array) {
                return array;
            }
        }
        function ignoreDuplicates() {
            return false;
        }
    })(this);
    var html = function() {
        return {
            wrapper: '<span class="twitter-typeahead"></span>',
            dropdown: '<span class="tt-dropdown-menu"></span>',
            dataset: '<div class="tt-dataset-%CLASS%"></div>',
            suggestions: '<span class="tt-suggestions"></span>',
            suggestion: '<div class="tt-suggestion"></div>'
        };
    }();
    var css = function() {
        "use strict";
        var css = {
            wrapper: {
                position: "relative",
                display: "inline-block"
            },
            hint: {
                position: "absolute",
                top: "0",
                left: "0",
                borderColor: "transparent",
                boxShadow: "none",
                opacity: "1"
            },
            input: {
                position: "relative",
                verticalAlign: "top",
                backgroundColor: "transparent"
            },
            inputWithNoHint: {
                position: "relative",
                verticalAlign: "top"
            },
            dropdown: {
                position: "absolute",
                top: "100%",
                left: "0",
                zIndex: "100",
                display: "none"
            },
            suggestions: {
                display: "block"
            },
            suggestion: {
                whiteSpace: "nowrap",
                cursor: "pointer"
            },
            suggestionChild: {
                whiteSpace: "normal"
            },
            ltr: {
                left: "0",
                right: "auto"
            },
            rtl: {
                left: "auto",
                right: " 0"
            }
        };
        if (_.isMsie()) {
            _.mixin(css.input, {
                backgroundImage: "url(data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7)"
            });
        }
        if (_.isMsie() && _.isMsie() <= 7) {
            _.mixin(css.input, {
                marginTop: "-1px"
            });
        }
        return css;
    }();
    var EventBus = function() {
        "use strict";
        var namespace = "typeahead:";
        function EventBus(o) {
            if (!o || !o.el) {
                $.error("EventBus initialized without el");
            }
            this.$el = $(o.el);
        }
        _.mixin(EventBus.prototype, {
            trigger: function(type) {
                var args = [].slice.call(arguments, 1);
                this.$el.trigger(namespace + type, args);
            }
        });
        return EventBus;
    }();
    var EventEmitter = function() {
        "use strict";
        var splitter = /\s+/, nextTick = getNextTick();
        return {
            onSync: onSync,
            onAsync: onAsync,
            off: off,
            trigger: trigger
        };
        function on(method, types, cb, context) {
            var type;
            if (!cb) {
                return this;
            }
            types = types.split(splitter);
            cb = context ? bindContext(cb, context) : cb;
            this._callbacks = this._callbacks || {};
            while (type = types.shift()) {
                this._callbacks[type] = this._callbacks[type] || {
                    sync: [],
                    async: []
                };
                this._callbacks[type][method].push(cb);
            }
            return this;
        }
        function onAsync(types, cb, context) {
            return on.call(this, "async", types, cb, context);
        }
        function onSync(types, cb, context) {
            return on.call(this, "sync", types, cb, context);
        }
        function off(types) {
            var type;
            if (!this._callbacks) {
                return this;
            }
            types = types.split(splitter);
            while (type = types.shift()) {
                delete this._callbacks[type];
            }
            return this;
        }
        function trigger(types) {
            var type, callbacks, args, syncFlush, asyncFlush;
            if (!this._callbacks) {
                return this;
            }
            types = types.split(splitter);
            args = [].slice.call(arguments, 1);
            while ((type = types.shift()) && (callbacks = this._callbacks[type])) {
                syncFlush = getFlush(callbacks.sync, this, [ type ].concat(args));
                asyncFlush = getFlush(callbacks.async, this, [ type ].concat(args));
                syncFlush() && nextTick(asyncFlush);
            }
            return this;
        }
        function getFlush(callbacks, context, args) {
            return flush;
            function flush() {
                var cancelled;
                for (var i = 0, len = callbacks.length; !cancelled && i < len; i += 1) {
                    cancelled = callbacks[i].apply(context, args) === false;
                }
                return !cancelled;
            }
        }
        function getNextTick() {
            var nextTickFn;
            if (window.setImmediate) {
                nextTickFn = function nextTickSetImmediate(fn) {
                    setImmediate(function() {
                        fn();
                    });
                };
            } else {
                nextTickFn = function nextTickSetTimeout(fn) {
                    setTimeout(function() {
                        fn();
                    }, 0);
                };
            }
            return nextTickFn;
        }
        function bindContext(fn, context) {
            return fn.bind ? fn.bind(context) : function() {
                fn.apply(context, [].slice.call(arguments, 0));
            };
        }
    }();
    var highlight = function(doc) {
        "use strict";
        var defaults = {
            node: null,
            pattern: null,
            tagName: "strong",
            className: null,
            wordsOnly: false,
            caseSensitive: false
        };
        return function hightlight(o) {
            var regex;
            o = _.mixin({}, defaults, o);
            if (!o.node || !o.pattern) {
                return;
            }
            o.pattern = _.isArray(o.pattern) ? o.pattern : [ o.pattern ];
            regex = getRegex(o.pattern, o.caseSensitive, o.wordsOnly);
            traverse(o.node, hightlightTextNode);
            function hightlightTextNode(textNode) {
                var match, patternNode, wrapperNode;
                if (match = regex.exec(textNode.data)) {
                    wrapperNode = doc.createElement(o.tagName);
                    o.className && (wrapperNode.className = o.className);
                    patternNode = textNode.splitText(match.index);
                    patternNode.splitText(match[0].length);
                    wrapperNode.appendChild(patternNode.cloneNode(true));
                    textNode.parentNode.replaceChild(wrapperNode, patternNode);
                }
                return !!match;
            }
            function traverse(el, hightlightTextNode) {
                var childNode, TEXT_NODE_TYPE = 3;
                for (var i = 0; i < el.childNodes.length; i++) {
                    childNode = el.childNodes[i];
                    if (childNode.nodeType === TEXT_NODE_TYPE) {
                        i += hightlightTextNode(childNode) ? 1 : 0;
                    } else {
                        traverse(childNode, hightlightTextNode);
                    }
                }
            }
        };
        function getRegex(patterns, caseSensitive, wordsOnly) {
            var escapedPatterns = [], regexStr;
            for (var i = 0, len = patterns.length; i < len; i++) {
                escapedPatterns.push(_.escapeRegExChars(patterns[i]));
            }
            regexStr = wordsOnly ? "\\b(" + escapedPatterns.join("|") + ")\\b" : "(" + escapedPatterns.join("|") + ")";
            return caseSensitive ? new RegExp(regexStr) : new RegExp(regexStr, "i");
        }
    }(window.document);
    var Input = function() {
        "use strict";
        var specialKeyCodeMap;
        specialKeyCodeMap = {
            9: "tab",
            27: "esc",
            37: "left",
            39: "right",
            13: "enter",
            38: "up",
            40: "down"
        };
        function Input(o) {
            var that = this, onBlur, onFocus, onKeydown, onInput;
            o = o || {};
            if (!o.input) {
                $.error("input is missing");
            }
            onBlur = _.bind(this._onBlur, this);
            onFocus = _.bind(this._onFocus, this);
            onKeydown = _.bind(this._onKeydown, this);
            onInput = _.bind(this._onInput, this);
            this.$hint = $(o.hint);
            this.$input = $(o.input).on("blur.tt", onBlur).on("focus.tt", onFocus).on("keydown.tt", onKeydown);
            if (this.$hint.length === 0) {
                this.setHint = this.getHint = this.clearHint = this.clearHintIfInvalid = _.noop;
            }
            if (!_.isMsie()) {
                this.$input.on("input.tt", onInput);
            } else {
                this.$input.on("keydown.tt keypress.tt cut.tt paste.tt", function($e) {
                    if (specialKeyCodeMap[$e.which || $e.keyCode]) {
                        return;
                    }
                    _.defer(_.bind(that._onInput, that, $e));
                });
            }
            this.query = this.$input.val();
            this.$overflowHelper = buildOverflowHelper(this.$input);
        }
        Input.normalizeQuery = function(str) {
            return (str || "").replace(/^\s*/g, "").replace(/\s{2,}/g, " ");
        };
        _.mixin(Input.prototype, EventEmitter, {
            _onBlur: function onBlur() {
                this.resetInputValue();
                this.trigger("blurred");
            },
            _onFocus: function onFocus() {
                this.trigger("focused");
            },
            _onKeydown: function onKeydown($e) {
                var keyName = specialKeyCodeMap[$e.which || $e.keyCode];
                this._managePreventDefault(keyName, $e);
                if (keyName && this._shouldTrigger(keyName, $e)) {
                    this.trigger(keyName + "Keyed", $e);
                }
            },
            _onInput: function onInput() {
                this._checkInputValue();
            },
            _managePreventDefault: function managePreventDefault(keyName, $e) {
                var preventDefault, hintValue, inputValue;
                switch (keyName) {
                  case "tab":
                    hintValue = this.getHint();
                    inputValue = this.getInputValue();
                    preventDefault = hintValue && hintValue !== inputValue && !withModifier($e);
                    break;

                  case "up":
                  case "down":
                    preventDefault = !withModifier($e);
                    break;

                  default:
                    preventDefault = false;
                }
                preventDefault && $e.preventDefault();
            },
            _shouldTrigger: function shouldTrigger(keyName, $e) {
                var trigger;
                switch (keyName) {
                  case "tab":
                    trigger = !withModifier($e);
                    break;

                  default:
                    trigger = true;
                }
                return trigger;
            },
            _checkInputValue: function checkInputValue() {
                var inputValue, areEquivalent, hasDifferentWhitespace;
                inputValue = this.getInputValue();
                areEquivalent = areQueriesEquivalent(inputValue, this.query);
                hasDifferentWhitespace = areEquivalent ? this.query.length !== inputValue.length : false;
                this.query = inputValue;
                if (!areEquivalent) {
                    this.trigger("queryChanged", this.query);
                } else if (hasDifferentWhitespace) {
                    this.trigger("whitespaceChanged", this.query);
                }
            },
            focus: function focus() {
                this.$input.focus();
            },
            blur: function blur() {
                this.$input.blur();
            },
            getQuery: function getQuery() {
                return this.query;
            },
            setQuery: function setQuery(query) {
                this.query = query;
            },
            getInputValue: function getInputValue() {
                return this.$input.val();
            },
            setInputValue: function setInputValue(value, silent) {
                this.$input.val(value);
                silent ? this.clearHint() : this._checkInputValue();
            },
            resetInputValue: function resetInputValue() {
                this.setInputValue(this.query, true);
            },
            getHint: function getHint() {
                return this.$hint.val();
            },
            setHint: function setHint(value) {
                this.$hint.val(value);
            },
            clearHint: function clearHint() {
                this.setHint("");
            },
            clearHintIfInvalid: function clearHintIfInvalid() {
                var val, hint, valIsPrefixOfHint, isValid;
                val = this.getInputValue();
                hint = this.getHint();
                valIsPrefixOfHint = val !== hint && hint.indexOf(val) === 0;
                isValid = val !== "" && valIsPrefixOfHint && !this.hasOverflow();
                !isValid && this.clearHint();
            },
            getLanguageDirection: function getLanguageDirection() {
                return (this.$input.css("direction") || "ltr").toLowerCase();
            },
            hasOverflow: function hasOverflow() {
                var constraint = this.$input.width() - 2;
                this.$overflowHelper.text(this.getInputValue());
                return this.$overflowHelper.width() >= constraint;
            },
            isCursorAtEnd: function() {
                var valueLength, selectionStart, range;
                valueLength = this.$input.val().length;
                selectionStart = this.$input[0].selectionStart;
                if (_.isNumber(selectionStart)) {
                    return selectionStart === valueLength;
                } else if (document.selection) {
                    range = document.selection.createRange();
                    range.moveStart("character", -valueLength);
                    return valueLength === range.text.length;
                }
                return true;
            },
            destroy: function destroy() {
                this.$hint.off(".tt");
                this.$input.off(".tt");
                this.$hint = this.$input = this.$overflowHelper = null;
            }
        });
        return Input;
        function buildOverflowHelper($input) {
            return $('<pre aria-hidden="true"></pre>').css({
                position: "absolute",
                visibility: "hidden",
                whiteSpace: "pre",
                fontFamily: $input.css("font-family"),
                fontSize: $input.css("font-size"),
                fontStyle: $input.css("font-style"),
                fontVariant: $input.css("font-variant"),
                fontWeight: $input.css("font-weight"),
                wordSpacing: $input.css("word-spacing"),
                letterSpacing: $input.css("letter-spacing"),
                textIndent: $input.css("text-indent"),
                textRendering: $input.css("text-rendering"),
                textTransform: $input.css("text-transform")
            }).insertAfter($input);
        }
        function areQueriesEquivalent(a, b) {
            return Input.normalizeQuery(a) === Input.normalizeQuery(b);
        }
        function withModifier($e) {
            return $e.altKey || $e.ctrlKey || $e.metaKey || $e.shiftKey;
        }
    }();
    var Dataset = function() {
        "use strict";
        var datasetKey = "ttDataset", valueKey = "ttValue", datumKey = "ttDatum";
        function Dataset(o) {
            o = o || {};
            o.templates = o.templates || {};
            if (!o.source) {
                $.error("missing source");
            }
            if (o.name && !isValidName(o.name)) {
                $.error("invalid dataset name: " + o.name);
            }
            this.query = null;
            this.highlight = !!o.highlight;
            this.name = o.name || _.getUniqueId();
            this.source = o.source;
            this.displayFn = getDisplayFn(o.display || o.displayKey);
            this.templates = getTemplates(o.templates, this.displayFn);
            this.$el = $(html.dataset.replace("%CLASS%", this.name));
        }
        Dataset.extractDatasetName = function extractDatasetName(el) {
            return $(el).data(datasetKey);
        };
        Dataset.extractValue = function extractDatum(el) {
            return $(el).data(valueKey);
        };
        Dataset.extractDatum = function extractDatum(el) {
            return $(el).data(datumKey);
        };
        _.mixin(Dataset.prototype, EventEmitter, {
            _render: function render(query, suggestions) {
                if (!this.$el) {
                    return;
                }
                var that = this, hasSuggestions;
                this.$el.empty();
                hasSuggestions = suggestions && suggestions.length;
                if (!hasSuggestions && this.templates.empty) {
                    this.$el.html(getEmptyHtml()).prepend(that.templates.header ? getHeaderHtml() : null).append(that.templates.footer ? getFooterHtml() : null);
                } else if (hasSuggestions) {
                    this.$el.html(getSuggestionsHtml()).prepend(that.templates.header ? getHeaderHtml() : null).append(that.templates.footer ? getFooterHtml() : null);
                }
                this.trigger("rendered");
                function getEmptyHtml() {
                    return that.templates.empty({
                        query: query,
                        isEmpty: true
                    });
                }
                function getSuggestionsHtml() {
                    var $suggestions, nodes;
                    $suggestions = $(html.suggestions).css(css.suggestions);
                    nodes = _.map(suggestions, getSuggestionNode);
                    $suggestions.append.apply($suggestions, nodes);
                    that.highlight && highlight({
                        className: "tt-highlight",
                        node: $suggestions[0],
                        pattern: query
                    });
                    return $suggestions;
                    function getSuggestionNode(suggestion) {
                        var $el;
                        $el = $(html.suggestion).append(that.templates.suggestion(suggestion)).data(datasetKey, that.name).data(valueKey, that.displayFn(suggestion)).data(datumKey, suggestion);
                        $el.children().each(function() {
                            $(this).css(css.suggestionChild);
                        });
                        return $el;
                    }
                }
                function getHeaderHtml() {
                    return that.templates.header({
                        query: query,
                        isEmpty: !hasSuggestions
                    });
                }
                function getFooterHtml() {
                    return that.templates.footer({
                        query: query,
                        isEmpty: !hasSuggestions
                    });
                }
            },
            getRoot: function getRoot() {
                return this.$el;
            },
            update: function update(query) {
                var that = this;
                this.query = query;
                this.canceled = false;
                this.source(query, render);
                function render(suggestions) {
                    if (!that.canceled && query === that.query) {
                        that._render(query, suggestions);
                    }
                }
            },
            cancel: function cancel() {
                this.canceled = true;
            },
            clear: function clear() {
                this.cancel();
                this.$el.empty();
                this.trigger("rendered");
            },
            isEmpty: function isEmpty() {
                return this.$el.is(":empty");
            },
            destroy: function destroy() {
                this.$el = null;
            }
        });
        return Dataset;
        function getDisplayFn(display) {
            display = display || "value";
            return _.isFunction(display) ? display : displayFn;
            function displayFn(obj) {
                return obj[display];
            }
        }
        function getTemplates(templates, displayFn) {
            return {
                empty: templates.empty && _.templatify(templates.empty),
                header: templates.header && _.templatify(templates.header),
                footer: templates.footer && _.templatify(templates.footer),
                suggestion: templates.suggestion || suggestionTemplate
            };
            function suggestionTemplate(context) {
                return "<p>" + displayFn(context) + "</p>";
            }
        }
        function isValidName(str) {
            return /^[_a-zA-Z0-9-]+$/.test(str);
        }
    }();
    var Dropdown = function() {
        "use strict";
        function Dropdown(o) {
            var that = this, onSuggestionClick, onSuggestionMouseEnter, onSuggestionMouseLeave;
            o = o || {};
            if (!o.menu) {
                $.error("menu is required");
            }
            this.isOpen = false;
            this.isEmpty = true;
            this.datasets = _.map(o.datasets, initializeDataset);
            onSuggestionClick = _.bind(this._onSuggestionClick, this);
            onSuggestionMouseEnter = _.bind(this._onSuggestionMouseEnter, this);
            onSuggestionMouseLeave = _.bind(this._onSuggestionMouseLeave, this);
            this.$menu = $(o.menu).on("click.tt", ".tt-suggestion", onSuggestionClick).on("mouseenter.tt", ".tt-suggestion", onSuggestionMouseEnter).on("mouseleave.tt", ".tt-suggestion", onSuggestionMouseLeave);
            _.each(this.datasets, function(dataset) {
                that.$menu.append(dataset.getRoot());
                dataset.onSync("rendered", that._onRendered, that);
            });
        }
        _.mixin(Dropdown.prototype, EventEmitter, {
            _onSuggestionClick: function onSuggestionClick($e) {
                this.trigger("suggestionClicked", $($e.currentTarget));
            },
            _onSuggestionMouseEnter: function onSuggestionMouseEnter($e) {
                this._removeCursor();
                this._setCursor($($e.currentTarget), true);
            },
            _onSuggestionMouseLeave: function onSuggestionMouseLeave() {
                this._removeCursor();
            },
            _onRendered: function onRendered() {
                this.isEmpty = _.every(this.datasets, isDatasetEmpty);
                this.isEmpty ? this._hide() : this.isOpen && this._show();
                this.trigger("datasetRendered");
                function isDatasetEmpty(dataset) {
                    return dataset.isEmpty();
                }
            },
            _hide: function() {
                this.$menu.hide();
            },
            _show: function() {
                this.$menu.css("display", "block");
            },
            _getSuggestions: function getSuggestions() {
                return this.$menu.find(".tt-suggestion");
            },
            _getCursor: function getCursor() {
                return this.$menu.find(".tt-cursor").first();
            },
            _setCursor: function setCursor($el, silent) {
                $el.first().addClass("tt-cursor");
                !silent && this.trigger("cursorMoved");
            },
            _removeCursor: function removeCursor() {
                this._getCursor().removeClass("tt-cursor");
            },
            _moveCursor: function moveCursor(increment) {
                var $suggestions, $oldCursor, newCursorIndex, $newCursor;
                if (!this.isOpen) {
                    return;
                }
                $oldCursor = this._getCursor();
                $suggestions = this._getSuggestions();
                this._removeCursor();
                newCursorIndex = $suggestions.index($oldCursor) + increment;
                newCursorIndex = (newCursorIndex + 1) % ($suggestions.length + 1) - 1;
                if (newCursorIndex === -1) {
                    this.trigger("cursorRemoved");
                    return;
                } else if (newCursorIndex < -1) {
                    newCursorIndex = $suggestions.length - 1;
                }
                this._setCursor($newCursor = $suggestions.eq(newCursorIndex));
                this._ensureVisible($newCursor);
            },
            _ensureVisible: function ensureVisible($el) {
                var elTop, elBottom, menuScrollTop, menuHeight;
                elTop = $el.position().top;
                elBottom = elTop + $el.outerHeight(true);
                menuScrollTop = this.$menu.scrollTop();
                menuHeight = this.$menu.height() + parseInt(this.$menu.css("paddingTop"), 10) + parseInt(this.$menu.css("paddingBottom"), 10);
                if (elTop < 0) {
                    this.$menu.scrollTop(menuScrollTop + elTop);
                } else if (menuHeight < elBottom) {
                    this.$menu.scrollTop(menuScrollTop + (elBottom - menuHeight));
                }
            },
            close: function close() {
                if (this.isOpen) {
                    this.isOpen = false;
                    this._removeCursor();
                    this._hide();
                    this.trigger("closed");
                }
            },
            open: function open() {
                if (!this.isOpen) {
                    this.isOpen = true;
                    !this.isEmpty && this._show();
                    this.trigger("opened");
                }
            },
            setLanguageDirection: function setLanguageDirection(dir) {
                this.$menu.css(dir === "ltr" ? css.ltr : css.rtl);
            },
            moveCursorUp: function moveCursorUp() {
                this._moveCursor(-1);
            },
            moveCursorDown: function moveCursorDown() {
                this._moveCursor(+1);
            },
            getDatumForSuggestion: function getDatumForSuggestion($el) {
                var datum = null;
                if ($el.length) {
                    datum = {
                        raw: Dataset.extractDatum($el),
                        value: Dataset.extractValue($el),
                        datasetName: Dataset.extractDatasetName($el)
                    };
                }
                return datum;
            },
            getDatumForCursor: function getDatumForCursor() {
                return this.getDatumForSuggestion(this._getCursor().first());
            },
            getDatumForTopSuggestion: function getDatumForTopSuggestion() {
                return this.getDatumForSuggestion(this._getSuggestions().first());
            },
            update: function update(query) {
                _.each(this.datasets, updateDataset);
                function updateDataset(dataset) {
                    dataset.update(query);
                }
            },
            empty: function empty() {
                _.each(this.datasets, clearDataset);
                this.isEmpty = true;
                function clearDataset(dataset) {
                    dataset.clear();
                }
            },
            isVisible: function isVisible() {
                return this.isOpen && !this.isEmpty;
            },
            destroy: function destroy() {
                this.$menu.off(".tt");
                this.$menu = null;
                _.each(this.datasets, destroyDataset);
                function destroyDataset(dataset) {
                    dataset.destroy();
                }
            }
        });
        return Dropdown;
        function initializeDataset(oDataset) {
            return new Dataset(oDataset);
        }
    }();
    var Typeahead = function() {
        "use strict";
        var attrsKey = "ttAttrs";
        function Typeahead(o) {
            var $menu, $input, $hint;
            o = o || {};
            if (!o.input) {
                $.error("missing input");
            }
            this.isActivated = false;
            this.autoselect = !!o.autoselect;
            this.minLength = _.isNumber(o.minLength) ? o.minLength : 1;
            this.$node = buildDom(o.input, o.withHint);
            $menu = this.$node.find(".tt-dropdown-menu");
            $input = this.$node.find(".tt-input");
            $hint = this.$node.find(".tt-hint");
            $input.on("blur.tt", function($e) {
                var active, isActive, hasActive;
                active = document.activeElement;
                isActive = $menu.is(active);
                hasActive = $menu.has(active).length > 0;
                if (_.isMsie() && (isActive || hasActive)) {
                    $e.preventDefault();
                    $e.stopImmediatePropagation();
                    _.defer(function() {
                        $input.focus();
                    });
                }
            });
            $menu.on("mousedown.tt", function($e) {
                $e.preventDefault();
            });
            this.eventBus = o.eventBus || new EventBus({
                el: $input
            });
            this.dropdown = new Dropdown({
                menu: $menu,
                datasets: o.datasets
            }).onSync("suggestionClicked", this._onSuggestionClicked, this).onSync("cursorMoved", this._onCursorMoved, this).onSync("cursorRemoved", this._onCursorRemoved, this).onSync("opened", this._onOpened, this).onSync("closed", this._onClosed, this).onAsync("datasetRendered", this._onDatasetRendered, this);
            this.input = new Input({
                input: $input,
                hint: $hint
            }).onSync("focused", this._onFocused, this).onSync("blurred", this._onBlurred, this).onSync("enterKeyed", this._onEnterKeyed, this).onSync("tabKeyed", this._onTabKeyed, this).onSync("escKeyed", this._onEscKeyed, this).onSync("upKeyed", this._onUpKeyed, this).onSync("downKeyed", this._onDownKeyed, this).onSync("leftKeyed", this._onLeftKeyed, this).onSync("rightKeyed", this._onRightKeyed, this).onSync("queryChanged", this._onQueryChanged, this).onSync("whitespaceChanged", this._onWhitespaceChanged, this);
            this._setLanguageDirection();
        }
        _.mixin(Typeahead.prototype, {
            _onSuggestionClicked: function onSuggestionClicked(type, $el) {
                var datum;
                if (datum = this.dropdown.getDatumForSuggestion($el)) {
                    this._select(datum);
                }
            },
            _onCursorMoved: function onCursorMoved() {
                var datum = this.dropdown.getDatumForCursor();
                this.input.setInputValue(datum.value, true);
                this.eventBus.trigger("cursorchanged", datum.raw, datum.datasetName);
            },
            _onCursorRemoved: function onCursorRemoved() {
                this.input.resetInputValue();
                this._updateHint();
            },
            _onDatasetRendered: function onDatasetRendered() {
                this._updateHint();
            },
            _onOpened: function onOpened() {
                this._updateHint();
                this.eventBus.trigger("opened");
            },
            _onClosed: function onClosed() {
                this.input.clearHint();
                this.eventBus.trigger("closed");
            },
            _onFocused: function onFocused() {
                this.isActivated = true;
                this.dropdown.open();
            },
            _onBlurred: function onBlurred() {
                this.isActivated = false;
                this.dropdown.empty();
                this.dropdown.close();
            },
            _onEnterKeyed: function onEnterKeyed(type, $e) {
                var cursorDatum, topSuggestionDatum;
                cursorDatum = this.dropdown.getDatumForCursor();
                topSuggestionDatum = this.dropdown.getDatumForTopSuggestion();
                if (cursorDatum) {
                    this._select(cursorDatum);
                    $e.preventDefault();
                } else if (this.autoselect && topSuggestionDatum) {
                    this._select(topSuggestionDatum);
                    $e.preventDefault();
                }
            },
            _onTabKeyed: function onTabKeyed(type, $e) {
                var datum;
                if (datum = this.dropdown.getDatumForCursor()) {
                    this._select(datum);
                    $e.preventDefault();
                } else {
                    this._autocomplete(true);
                }
            },
            _onEscKeyed: function onEscKeyed() {
                this.dropdown.close();
                this.input.resetInputValue();
            },
            _onUpKeyed: function onUpKeyed() {
                var query = this.input.getQuery();
                this.dropdown.isEmpty && query.length >= this.minLength ? this.dropdown.update(query) : this.dropdown.moveCursorUp();
                this.dropdown.open();
            },
            _onDownKeyed: function onDownKeyed() {
                var query = this.input.getQuery();
                this.dropdown.isEmpty && query.length >= this.minLength ? this.dropdown.update(query) : this.dropdown.moveCursorDown();
                this.dropdown.open();
            },
            _onLeftKeyed: function onLeftKeyed() {
                this.dir === "rtl" && this._autocomplete();
            },
            _onRightKeyed: function onRightKeyed() {
                this.dir === "ltr" && this._autocomplete();
            },
            _onQueryChanged: function onQueryChanged(e, query) {
                this.input.clearHintIfInvalid();
                query.length >= this.minLength ? this.dropdown.update(query) : this.dropdown.empty();
                this.dropdown.open();
                this._setLanguageDirection();
            },
            _onWhitespaceChanged: function onWhitespaceChanged() {
                this._updateHint();
                this.dropdown.open();
            },
            _setLanguageDirection: function setLanguageDirection() {
                var dir;
                if (this.dir !== (dir = this.input.getLanguageDirection())) {
                    this.dir = dir;
                    this.$node.css("direction", dir);
                    this.dropdown.setLanguageDirection(dir);
                }
            },
            _updateHint: function updateHint() {
                var datum, val, query, escapedQuery, frontMatchRegEx, match;
                datum = this.dropdown.getDatumForTopSuggestion();
                if (datum && this.dropdown.isVisible() && !this.input.hasOverflow()) {
                    val = this.input.getInputValue();
                    query = Input.normalizeQuery(val);
                    escapedQuery = _.escapeRegExChars(query);
                    frontMatchRegEx = new RegExp("^(?:" + escapedQuery + ")(.+$)", "i");
                    match = frontMatchRegEx.exec(datum.value);
                    match ? this.input.setHint(val + match[1]) : this.input.clearHint();
                } else {
                    this.input.clearHint();
                }
            },
            _autocomplete: function autocomplete(laxCursor) {
                var hint, query, isCursorAtEnd, datum;
                hint = this.input.getHint();
                query = this.input.getQuery();
                isCursorAtEnd = laxCursor || this.input.isCursorAtEnd();
                if (hint && query !== hint && isCursorAtEnd) {
                    datum = this.dropdown.getDatumForTopSuggestion();
                    datum && this.input.setInputValue(datum.value);
                    this.eventBus.trigger("autocompleted", datum.raw, datum.datasetName);
                }
            },
            _select: function select(datum) {
                this.input.setQuery(datum.value);
                this.input.setInputValue(datum.value, true);
                this._setLanguageDirection();
                this.eventBus.trigger("selected", datum.raw, datum.datasetName);
                this.dropdown.close();
                _.defer(_.bind(this.dropdown.empty, this.dropdown));
            },
            open: function open() {
                this.dropdown.open();
            },
            close: function close() {
                this.dropdown.close();
            },
            setVal: function setVal(val) {
                val = _.toStr(val);
                if (this.isActivated) {
                    this.input.setInputValue(val);
                } else {
                    this.input.setQuery(val);
                    this.input.setInputValue(val, true);
                }
                this._setLanguageDirection();
            },
            getVal: function getVal() {
                return this.input.getQuery();
            },
            destroy: function destroy() {
                this.input.destroy();
                this.dropdown.destroy();
                destroyDomStructure(this.$node);
                this.$node = null;
            }
        });
        return Typeahead;
        function buildDom(input, withHint) {
            var $input, $wrapper, $dropdown, $hint;
            $input = $(input);
            $wrapper = $(html.wrapper).css(css.wrapper);
            $dropdown = $(html.dropdown).css(css.dropdown);
            $hint = $input.clone().css(css.hint).css(getBackgroundStyles($input));
            $hint.val("").removeData().addClass("tt-hint").removeAttr("id name placeholder required").prop("readonly", true).attr({
                autocomplete: "off",
                spellcheck: "false",
                tabindex: -1
            });
            $input.data(attrsKey, {
                dir: $input.attr("dir"),
                autocomplete: $input.attr("autocomplete"),
                spellcheck: $input.attr("spellcheck"),
                style: $input.attr("style")
            });
            $input.addClass("tt-input").attr({
                autocomplete: "off",
                spellcheck: false
            }).css(withHint ? css.input : css.inputWithNoHint);
            try {
                !$input.attr("dir") && $input.attr("dir", "auto");
            } catch (e) {}
            return $input.wrap($wrapper).parent().prepend(withHint ? $hint : null).append($dropdown);
        }
        function getBackgroundStyles($el) {
            return {
                backgroundAttachment: $el.css("background-attachment"),
                backgroundClip: $el.css("background-clip"),
                backgroundColor: $el.css("background-color"),
                backgroundImage: $el.css("background-image"),
                backgroundOrigin: $el.css("background-origin"),
                backgroundPosition: $el.css("background-position"),
                backgroundRepeat: $el.css("background-repeat"),
                backgroundSize: $el.css("background-size")
            };
        }
        function destroyDomStructure($node) {
            var $input = $node.find(".tt-input");
            _.each($input.data(attrsKey), function(val, key) {
                _.isUndefined(val) ? $input.removeAttr(key) : $input.attr(key, val);
            });
            $input.detach().removeData(attrsKey).removeClass("tt-input").insertAfter($node);
            $node.remove();
        }
    }();
    (function() {
        "use strict";
        var old, typeaheadKey, methods;
        old = $.fn.typeahead;
        typeaheadKey = "ttTypeahead";
        methods = {
            initialize: function initialize(o, datasets) {
                datasets = _.isArray(datasets) ? datasets : [].slice.call(arguments, 1);
                o = o || {};
                return this.each(attach);
                function attach() {
                    var $input = $(this), eventBus, typeahead;
                    _.each(datasets, function(d) {
                        d.highlight = !!o.highlight;
                    });
                    typeahead = new Typeahead({
                        input: $input,
                        eventBus: eventBus = new EventBus({
                            el: $input
                        }),
                        withHint: _.isUndefined(o.hint) ? true : !!o.hint,
                        minLength: o.minLength,
                        autoselect: o.autoselect,
                        datasets: datasets
                    });
                    $input.data(typeaheadKey, typeahead);
                }
            },
            open: function open() {
                return this.each(openTypeahead);
                function openTypeahead() {
                    var $input = $(this), typeahead;
                    if (typeahead = $input.data(typeaheadKey)) {
                        typeahead.open();
                    }
                }
            },
            close: function close() {
                return this.each(closeTypeahead);
                function closeTypeahead() {
                    var $input = $(this), typeahead;
                    if (typeahead = $input.data(typeaheadKey)) {
                        typeahead.close();
                    }
                }
            },
            val: function val(newVal) {
                return !arguments.length ? getVal(this.first()) : this.each(setVal);
                function setVal() {
                    var $input = $(this), typeahead;
                    if (typeahead = $input.data(typeaheadKey)) {
                        typeahead.setVal(newVal);
                    }
                }
                function getVal($input) {
                    var typeahead, query;
                    if (typeahead = $input.data(typeaheadKey)) {
                        query = typeahead.getVal();
                    }
                    return query;
                }
            },
            destroy: function destroy() {
                return this.each(unattach);
                function unattach() {
                    var $input = $(this), typeahead;
                    if (typeahead = $input.data(typeaheadKey)) {
                        typeahead.destroy();
                        $input.removeData(typeaheadKey);
                    }
                }
            }
        };
        $.fn.typeahead = function(method) {
            var tts;
            if (methods[method] && method !== "initialize") {
                tts = this.filter(function() {
                    return !!$(this).data(typeaheadKey);
                });
                return methods[method].apply(tts, [].slice.call(arguments, 1));
            } else {
                return methods.initialize.apply(this, arguments);
            }
        };
        $.fn.typeahead.noConflict = function noConflict() {
            $.fn.typeahead = old;
            return this;
        };
    })();
})(window.jQuery);
/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(173).setImmediate))

/***/ },

/***/ 173:
/***/ function(module, exports, __webpack_require__) {

/* WEBPACK VAR INJECTION */(function(setImmediate, clearImmediate) {var nextTick = __webpack_require__(174).nextTick;
var apply = Function.prototype.apply;
var slice = Array.prototype.slice;
var immediateIds = {};
var nextImmediateId = 0;

// DOM APIs, for completeness

exports.setTimeout = function() {
  return new Timeout(apply.call(setTimeout, window, arguments), clearTimeout);
};
exports.setInterval = function() {
  return new Timeout(apply.call(setInterval, window, arguments), clearInterval);
};
exports.clearTimeout =
exports.clearInterval = function(timeout) { timeout.close(); };

function Timeout(id, clearFn) {
  this._id = id;
  this._clearFn = clearFn;
}
Timeout.prototype.unref = Timeout.prototype.ref = function() {};
Timeout.prototype.close = function() {
  this._clearFn.call(window, this._id);
};

// Does not start the time, just sets up the members needed.
exports.enroll = function(item, msecs) {
  clearTimeout(item._idleTimeoutId);
  item._idleTimeout = msecs;
};

exports.unenroll = function(item) {
  clearTimeout(item._idleTimeoutId);
  item._idleTimeout = -1;
};

exports._unrefActive = exports.active = function(item) {
  clearTimeout(item._idleTimeoutId);

  var msecs = item._idleTimeout;
  if (msecs >= 0) {
    item._idleTimeoutId = setTimeout(function onTimeout() {
      if (item._onTimeout)
        item._onTimeout();
    }, msecs);
  }
};

// That's not how node.js implements it but the exposed api is the same.
exports.setImmediate = typeof setImmediate === "function" ? setImmediate : function(fn) {
  var id = nextImmediateId++;
  var args = arguments.length < 2 ? false : slice.call(arguments, 1);

  immediateIds[id] = true;

  nextTick(function onNextTick() {
    if (immediateIds[id]) {
      // fn.call() is faster so we optimize for the common use-case
      // @see http://jsperf.com/call-apply-segu
      if (args) {
        fn.apply(null, args);
      } else {
        fn.call(null);
      }
      // Prevent ids from leaking
      exports.clearImmediate(id);
    }
  });

  return id;
};

exports.clearImmediate = typeof clearImmediate === "function" ? clearImmediate : function(id) {
  delete immediateIds[id];
};
/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(173).setImmediate, __webpack_require__(173).clearImmediate))

/***/ },

/***/ 174:
/***/ function(module, exports) {

// shim for using process in browser

var process = module.exports = {};
var queue = [];
var draining = false;
var currentQueue;
var queueIndex = -1;

function cleanUpNextTick() {
    draining = false;
    if (currentQueue.length) {
        queue = currentQueue.concat(queue);
    } else {
        queueIndex = -1;
    }
    if (queue.length) {
        drainQueue();
    }
}

function drainQueue() {
    if (draining) {
        return;
    }
    var timeout = setTimeout(cleanUpNextTick);
    draining = true;

    var len = queue.length;
    while(len) {
        currentQueue = queue;
        queue = [];
        while (++queueIndex < len) {
            if (currentQueue) {
                currentQueue[queueIndex].run();
            }
        }
        queueIndex = -1;
        len = queue.length;
    }
    currentQueue = null;
    draining = false;
    clearTimeout(timeout);
}

process.nextTick = function (fun) {
    var args = new Array(arguments.length - 1);
    if (arguments.length > 1) {
        for (var i = 1; i < arguments.length; i++) {
            args[i - 1] = arguments[i];
        }
    }
    queue.push(new Item(fun, args));
    if (queue.length === 1 && !draining) {
        setTimeout(drainQueue, 0);
    }
};

// v8 likes predictible objects
function Item(fun, array) {
    this.fun = fun;
    this.array = array;
}
Item.prototype.run = function () {
    this.fun.apply(null, this.array);
};
process.title = 'browser';
process.browser = true;
process.env = {};
process.argv = [];
process.version = ''; // empty string to avoid regexp issues
process.versions = {};

function noop() {}

process.on = noop;
process.addListener = noop;
process.once = noop;
process.off = noop;
process.removeListener = noop;
process.removeAllListeners = noop;
process.emit = noop;

process.binding = function (name) {
    throw new Error('process.binding is not supported');
};

process.cwd = function () { return '/' };
process.chdir = function (dir) {
    throw new Error('process.chdir is not supported');
};
process.umask = function() { return 0; };


/***/ },

/***/ 175:
/***/ function(module, exports, __webpack_require__) {

/**
* A KO component for the project creation form.
*/
'use strict';

var $ = __webpack_require__(38);
__webpack_require__(176);
var ko = __webpack_require__(48);
var bootbox = __webpack_require__(138);

var $osf = __webpack_require__(47);
var nodeCategories = __webpack_require__(177);

var CREATE_URL = '/api/v1/project/new/';

/*
    * ViewModel for the project creation form.
    *
    * Template: osf-project-creat-form in component/dashboard_templates.mako
    *
    * Params:
    *  - data: Data to populate the template selection input
    */
function ProjectCreatorViewModel(params) {
    var self = this;
    self.params = params || {};
    self.minSearchLength = 2;
    self.title = ko.observable('');
    self.description = ko.observable();

    self.category = ko.observable('project');
    self.categoryMap = nodeCategories;
    self.categories = Object.keys(nodeCategories);

    self.errorMessage = ko.observable('');

    self.hasFocus = params.hasFocus;

    self.usingTemplate = ko.observable(false);
    self.enableCreateBtn =  ko.observable(true);

    self.disableSubmitBtn = function (){
        self.enableCreateBtn(false);
    };
    self.enableSubmitBtn = function (){
        self.enableCreateBtn(true);
    };

    self.submitForm = function () {
        if (self.title().trim() === '') {
            self.errorMessage('This field is required.');
        } else {
            self.disableSubmitBtn();
            self.createProject();
        }
    };

    self.createProject = function() {
        $osf.postJSON(
            CREATE_URL,
            self.serialize()
        ).done(
            self.createSuccess
        ).fail(
            self.createFailure
        );
    };

    self.createSuccess = function(data) {
        window.location = data.projectUrl;
    };

    self.createFailure = function() {
        self.enableSubmitBtn();
        $osf.growl('Could not create a new project.', 'Please try again. If the problem persists, email <a href="mailto:support@osf.io.">support@osf.io</a>');

    };

    self.serialize = function() {
        var category = self.category();
        var template;
        //select behavior differently in IE from all other browser. The input tag is 1 in other browser but 3 in IE
        if($osf.isIE()){
            template = $('.create-node-templates')[3].value;
        } else {
            template = $('.create-node-templates')[1].value;
        }
        return {
            title: self.title(),
            category: category,
            description: self.description(),
            template: template
        };
    };
    /**
        * Query the current users projects from a local cache
        *
        * @method ownProjects
        * @param {String} q a string query
        * @return {Array} A filtered array of strings
        */
    self.ownProjects = function(q) {
        if (q === '') {
            return self.templates;
        }
        return self.templates.filter(function(item) {
            return item.text.toLowerCase().indexOf(q.toLowerCase()) !== -1;
        });
    };

    self.query = function(query) {
        if (query.term.length > self.minSearchLength) {
            self.fetchNodes(query.term, query.callback);
            return;
        }
        query.callback({
            results: [{
                text: 'Your Projects',
                children: self.ownProjects(query.term)
            }]
        });
    };

    /**
        * Fetch Nodes from the search api and concat. them with the current users projects
        *
        * @method fetchNodes
        * @param {String} q A string query
        * @param {Function} cb A callback to call with the list of projects
        * @return null
        */
    self.fetchNodes = function(q, cb) {
        $osf.postJSON(
            '/api/v1/search/node/',
            {
                includePublic: true,
                query: q,
            }
        ).done(function(data) {
            var results = [];
            var local = self.ownProjects(q);
            var fetched = self.loadNodes(data.nodes);

            // Filter against local projects so that duplicates are not shown
            fetched = fetched.filter(function(element) {
                for (var i = 0; i < local.length; i++) {
                    if (element.id === local[i].id) {
                        return false;
                    }
                }
                return true;
            });

            if (fetched.length > 0) {
                results.push({
                    text: 'Other Projects',
                    children: fetched
                });
            }

            if (local.length > 0) {
                results.push({
                    text: 'Your Projects',
                    children: local
                });
            }

            cb({results: results});
        }).fail(function() {
            //Silently error by just returning your projects
            cb({
                results: [{
                    text: 'Your Projects',
                    children: self.ownProjects(q)
                }]
            });
        });
    };

    self.loadNodes = function(nodes) {
        return ko.utils.arrayMap(nodes, function(node) {
            return {
                'id': node.id,
                // TODO: Remove htmlDecode when pre-sanitized strings are no longer stored
                'text': $osf.htmlDecode(node.title)
            };
        });
    };

    self.templates = self.loadNodes(params.data);

    // IE won't select template with id correctly. so we replace #createNodeTemplates with .createNodeTemplates
    // More explanation -- https://github.com/CenterForOpenScience/osf.io/pull/2858
    $('.create-node-templates').select2({
        allowClear: true,
        placeholder: 'Select a project to use as a template',
        query: self.query
    });
}

ko.components.register('osf-project-create-form', {
    viewModel: ProjectCreatorViewModel,
    template: {element: 'osf-project-create-form'}
});


/***/ },

/***/ 177:
/***/ function(module, exports) {

module.exports = {
	"": "Uncategorized",
	"project": "Project",
	"hypothesis": "Hypothesis",
	"methods and measures": "Methods and Measures",
	"procedure": "Procedure",
	"instrumentation": "Instrumentation",
	"data": "Data",
	"analysis": "Analysis",
	"communication": "Communication",
	"other": "Other"
}

/***/ },

/***/ 179:
/***/ function(module, exports, __webpack_require__) {

/**
 * Renders a log feed.
 *
 */
'use strict';
var ko = __webpack_require__(48);
var $ = __webpack_require__(38);
var moment = __webpack_require__(53);
var Paginator = __webpack_require__(180);
var oop = __webpack_require__(146);
__webpack_require__(152);

var $osf = __webpack_require__(47);  // Injects 'listing' binding handler to to Knockout
var nodeCategories = __webpack_require__(177);

ko.punches.enableAll();  // Enable knockout punches

/**
  * Log model.
  */
var Log = function(params) {
    var self = this;

    $.extend(self, params);
    self.date = new $osf.FormattableDate(params.date);
    self.wikiUrl = ko.computed(function() {
        return self.nodeUrl + 'wiki/' + encodeURIComponent(self.params.page);
    });
    self.wikiIdUrl = ko.computed(function() {
        return self.nodeUrl + 'wiki/id/' + encodeURIComponent(self.params.page_id);
    });

    /**
      * Given an item in self.contributors, return its anchor element representation.
      */
    self._asContribLink = function(person) {
        var fullnameText = $osf.htmlEscape(person.fullname);
        return '<a class="contrib-link" href="/profile/' + person.id + '/">' + fullnameText + '</a>';
    };

    /**
      * Return whether a knockout template exists for the log.
      */
    self.hasTemplate = ko.computed(function() {
        if (!self.user) {
            return $('script#' + self.action + '_no_user').length > 0;
        } else {
            return $('script#' + self.action).length > 0;
        }
    });

    self.hasUser = ko.pureComputed(function() {
        return Boolean(self.user && self.user.fullname);
    });

    self.mapUpdates = function(key, item) {
        if (key === 'category') {
            return key + ' to ' + nodeCategories[item['new']];
        }
        else {
            return key + ' to ' + item;
        }
    };

    /**
      * Return the html for a comma-delimited list of contributor links, formatted
      * with correct list grammar.
      * e.g. "Dasher and Dancer", "Comet, Cupid, and Blitzen"
      */
    self.displayContributors = ko.computed(function(){
        var ret = '';
        if (self.anonymous){
            ret += '<span class="contributor-anonymous">some anonymous contributor(s)</span>';
        } else {
            for (var i = 0; i < self.contributors.length; i++) {
                var person = self.contributors[i];
                if (i === self.contributors.length - 1 && self.contributors.length > 2) {
                    ret += ' and ';
                }
                if (person.registered) {
                    ret += self._asContribLink(person);
                } else {
                    var fullnameText = $osf.htmlEscape(person.fullname);
                    ret += '<span>' + fullnameText + '</span>';
                }
                if (i < self.contributors.length - 1 && self.contributors.length > 2) {
                    ret += ', ';
                } else if (i < self.contributors.length - 1 && self.contributors.length === 2) {
                    ret += ' and ';
                }
            }
        }
        return ret;
    });

    //helper function to strip the slash for file or folder in log template
    self.stripSlash = function(path){
        return path.replace(/(^\/)|(\/$)/g, '');
    };

    //helper funtion to determine the type for removing in log template
    self.pathType = function(path){
        return path.match(/\/$/) ? 'folder' : 'file';
    };
};

/**
  * View model for a log list.
  * @param {Log[]} logs An array of Log model objects to render.
  * @param url the url ajax request post to
  */
var LogsViewModel = oop.extend(Paginator, {
    constructor: function(logs, url) {
        this.super.constructor.call(this);
        var self = this;
        self.loading = ko.observable(false);
        self.logs = ko.observableArray(logs);
        self.url = url;
        self.anonymousUserName = '<em>A user</em>';

        self.tzname = ko.pureComputed(function() {
            var logs = self.logs();
            if (logs.length) {
                var tz =  moment(logs[0].date.date).format('ZZ');
                return tz;
            }
            return '';
        });
    },
    //send request to get more logs when the more button is clicked
    fetchResults: function(){
        var self = this;
        self.loading(true); // show loading indicator

        return $.ajax({
            type: 'get',
            url: self.url,
            data:{
                page: self.pageToGet()
            },
            cache: false
        }).done(function(response) {
            // Initialize LogViewModel
            var logModelObjects = createLogs(response.logs); // Array of Log model objects
            self.logs.removeAll();
            for (var i=0; i<logModelObjects.length; i++) {
                self.logs.push(logModelObjects[i]);
            }
            self.currentPage(response.page);
            self.numberOfPages(response.pages);
            self.addNewPaginators();
        }).fail(
            $osf.handleJSONError
        ).always( function (){
            self.loading(false);
        });

    }
});


/**
  * Create an Array of Log model objects from data returned from an endpoint
  * @param  {Object[]} logData Log data returned from an endpoint.
  * @return {Log[]}         Array of Log objects.
  */
var createLogs = function(logData){
    var mappedLogs = $.map(logData, function(item) {
        return new Log({
            anonymous: item.anonymous,
            action: item.action,
            date: item.date,
            // The node type, either 'project' or 'component'
            // NOTE: This is NOT the component category (e.g. 'hypothesis')
            nodeType: item.node.is_registration ? 'registration': item.node.node_type,
            nodeCategory: item.node.category,
            contributors: item.contributors,
            nodeUrl: item.node.url,
            userFullName: item.user.fullname,
            userURL: item.user.url,
            params: item.params,
            nodeTitle: item.node.title,
            nodeDescription: item.params.description_new,
            nodePath: item.node.path,
            user: item.user
        });
    });
    return mappedLogs;
};

////////////////
// Public API //
////////////////

var defaults = {
    /** Selector for the progress bar. */
    progBar: '#logProgressBar'
};


var initViewModel = function(self, logs, url){
    self.logs = createLogs(logs);
    self.viewModel = new LogsViewModel(self.logs, url);
    if(url) {
        self.viewModel.fetchResults();
    }
    self.init();
};

/**
  * A log list feed.
  * @param {string} selector
  * @param {string} url
  * @param {object} options
  */
function LogFeed(selector, data, options) {
    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.options = $.extend({}, defaults, options);
    self.$progBar = $(self.options.progBar);
    //for recent activities logs
    if (Array.isArray(data)) { // data is an array of log object from server
        initViewModel(self, data, self.options.url);
    } else { // data is an URL, for watch logs and project logs
        var noLogs =[];
        initViewModel(self, noLogs, data);
    }
}

LogFeed.prototype.init = function() {
    var self = this;
    self.$progBar.hide();
    ko.cleanNode(self.$element[0]);
    $osf.applyBindings(self.viewModel, self.selector);
};

module.exports = LogFeed;


/***/ },

/***/ 180:
/***/ function(module, exports, __webpack_require__) {

/**
 * Paginator model
 */
'use strict';
var ko = __webpack_require__(48);
var oop = __webpack_require__(146);
var MAX_PAGES_ON_PAGINATOR = 7;
var MAX_PAGES_ON_PAGINATOR_SIDE = 5;




var Paginator = oop.defclass({
    constructor: function() {
        this.pageToGet = ko.observable(0);
        this.numberOfPages = ko.observable(0);
        this.currentPage = ko.observable(0);
        this.paginators = ko.observableArray([]);
    },
    addNewPaginators: function() {
        var self = this;
        var i;
        self.paginators.removeAll();
        if (self.numberOfPages() > 1) {
            self.paginators.push({
                style: (self.currentPage() === 0) ? 'disabled' : '',
                handler: self.previousPage.bind(self),
                text: '&lt;'
            }); /* jshint ignore:line */
                /* functions defined inside loop */

            self.paginators.push({
                style: (self.currentPage() === 0) ? 'active' : '',
                text: '1',
                handler: function() {
                    self.pageToGet(0);
                    if (self.pageToGet() !== self.currentPage()) {
                        self.fetchResults();
                    }
                }
            });
            if (self.numberOfPages() <= MAX_PAGES_ON_PAGINATOR) {
                for (i = 1; i < self.numberOfPages() - 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.pageToGet(parseInt(this.text) - 1);
                            if (self.pageToGet() !== self.currentPage()) {
                                self.fetchResults();
                            }
                        }
                    });/* jshint ignore:line */
                    // function defined inside loop
                }
            } else if (self.currentPage() < MAX_PAGES_ON_PAGINATOR_SIDE - 1) { // One ellipse at the end
                for (i = 1; i < MAX_PAGES_ON_PAGINATOR_SIDE; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.pageToGet(parseInt(this.text) - 1);
                            if (self.pageToGet() !== self.currentPage()) {
                                self.fetchResults();
                            }
                        }
                    });/* jshint ignore:line */
                    // functions defined inside loop

                }
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
            } else if (self.currentPage() > self.numberOfPages() - MAX_PAGES_ON_PAGINATOR_SIDE) { // one ellipses at the beginning
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
                for (i = self.numberOfPages() - MAX_PAGES_ON_PAGINATOR_SIDE; i < self.numberOfPages() - 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.pageToGet(parseInt(this.text) - 1);
                            if (self.pageToGet() !== self.currentPage()) {
                                self.fetchResults();
                            }
                        }
                    });/* jshint ignore:line */
                    // function defined inside loop

                }
            } else { // two ellipses
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
                for (i = self.currentPage() - 1; i <= self.currentPage() + 1; i++) {
                    self.paginators.push({
                        style: (self.currentPage() === i) ? 'active' : '',
                        text: i + 1,
                        handler: function() {
                            self.pageToGet(parseInt(this.text) - 1);
                            if (self.pageToGet() !== self.currentPage()) {
                                self.fetchResults();
                            }
                        }
                    });/* jshint ignore:line */
                    // functions defined inside loop

                }
                self.paginators.push({
                    style: 'disabled',
                    text: '...',
                    handler: function() {}
                });
            }
            self.paginators.push({
                style: (self.currentPage() === self.numberOfPages() - 1) ? 'active' : '',
                text: self.numberOfPages(),
                handler: function() {
                    self.pageToGet(self.numberOfPages() - 1);
                    if (self.pageToGet() !== self.currentPage()) {
                        self.fetchResults();
                    }
                }
            });
            self.paginators.push({
                style: (self.currentPage() === self.numberOfPages() - 1) ? 'disabled' : '',
                handler: self.nextPage.bind(self),
                text: '&gt;'
            });
        }
    },
    nextPage: function() {
        this.pageToGet(this.currentPage() + 1);
        if (this.pageToGet() < this.numberOfPages()){
            this.fetchResults();
        }
    },
    previousPage: function() {
        this.pageToGet(this.currentPage() - 1);
        if (this.pageToGet() >= 0) {
            this.fetchResults();
        }
    },
    fetchResults: function() {
        throw new Error('Paginator subclass must define a "fetchResults" method.');
    }
});


module.exports = Paginator;


/***/ },

/***/ 181:
/***/ function(module, exports, __webpack_require__) {

/**
 * Handles Project Organizer on dashboard page of OSF.
 * For Treebeard and _item API's check: https://github.com/caneruguz/treebeard/wiki
 */
'use strict';

var Treebeard = __webpack_require__(159);

// CSS
__webpack_require__(170);
__webpack_require__(182);
__webpack_require__(184);

var $ = __webpack_require__(38);
var m = __webpack_require__(158);
var Fangorn = __webpack_require__(186);
var bootbox = __webpack_require__(138);
var Bloodhound = __webpack_require__(188);
var moment = __webpack_require__(53);
var Raven = __webpack_require__(52);
var $osf = __webpack_require__(47);
var iconmap = __webpack_require__(139);
var legendView = __webpack_require__(189).view;
var Fangorn = __webpack_require__(186);

var nodeCategories = __webpack_require__(177);

// copyMode can be 'copy', 'move', 'forbidden', or null.
// This is set at draglogic and is used as global within this module
var copyMode = null;
// Initialize projectOrganizer object (separate from the ProjectOrganizer constructor at the end)
var projectOrganizer = {};

// Link ID's used to add existing project to folder
var linkName;
var linkID;

// Cross browser key codes for the Command key
var COMMAND_KEYS = [224, 17, 91, 93];
var ESCAPE_KEY = 27;
var ENTER_KEY = 13;

var projectOrganizerCategories = $.extend({}, {
    collection: 'Collections',
    smartCollection: 'Smart Collections',
    project: 'Project',
    link:  'Link'
}, nodeCategories);

/**
 * Bloodhound is a typeahead suggestion engine. Searches here for public projects
 * @type {Bloodhound}
 */
projectOrganizer.publicProjects = new Bloodhound({
    datumTokenizer: function (d) {
        return Bloodhound.tokenizers.whitespace(d.name);
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
        url: '/api/v1/search/projects/?term=%QUERY&maxResults=20&includePublic=yes&includeContributed=no',
        filter: function (projects) {
            return $.map(projects, function (project) {
                return {
                    name: project.value,
                    node_id: project.id,
                    category: project.category
                };
            });
        },
        limit: 10
    }
});

/**
 * Bloodhound is a typeahead suggestion engine. Searches here for users projects
 * @type {Bloodhound}
 */
projectOrganizer.myProjects = new Bloodhound({
    datumTokenizer: function (d) {
        return Bloodhound.tokenizers.whitespace(d.name);
    },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: {
        url: '/api/v1/search/projects/?term=%QUERY&maxResults=20&includePublic=no&includeContributed=yes',
        filter: function (projects) {
            return $.map(projects, function (project) {
                return {
                    name: project.value,
                    node_id: project.id,
                    category: project.category
                };
            });
        },
        limit: 10
    }
});

/**
 * Edits the template for the column titles.
 * Used here to make smart folder italicized
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller Check Treebeard API for methods available
 * @private
 */
function _poTitleColumn(item) {
    var tb = this;
    var preventSelect = function(e){
        e.stopImmediatePropagation();
    };
    var css = item.data.isSmartFolder ? 'project-smart-folder smart-folder' : '';
    if(item.data.archiving) {
        return  m('span', {'class': 'registration-archiving'}, item.data.name + ' [Archiving]');
    } else if(item.data.urls.fetch){
        return m('a.fg-file-links', { 'class' : css, href : item.data.urls.fetch, onclick : preventSelect}, item.data.name);
    } else {
        return  m('span', { 'class' : css}, item.data.name);
    }
}

/**
 * Links for going to project pages on the action column
 * @param event Click event
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @param {Object} col Column options
 * @this Treebeard.controller Check Treebeard API for methods available
 * @private
 */
function _gotoEvent(event, item) {
    var tb = this;
    if (COMMAND_KEYS.indexOf(tb.pressedKey) !== -1) {
        window.open(item.data.urls.fetch, '_blank');
    } else {
        window.open(item.data.urls.fetch, '_self');
    }
}


/**
 * Watching for escape key press
 * @param {String} nodeID Unique ID of the node
 */
function addFormKeyBindings(nodeID) {
    $('#ptd-' + nodeID).keyup(function (e) {
        if (e.which === 27) {
            $('#ptd-' + nodeID).find('.cancel-button-' + nodeID).filter(':visible').click();
            return false;
        }
    });
}


function triggerClickOnItem(item, force) {
    var row = $('.tb-row[data-id="' + item.id + '"]');
    if (force) {
        row.trigger('click');
    }

    if (row.hasClass(this.options.hoverClassMultiselect)) {
        row.trigger('click');
    }
}

/**
 * Saves the expand state of a folder so that it can be loaded based on that state
 * @param {Object} item Node data
 * @param {Function} callback
 */
function saveExpandState(item, callback) {
    var collapseUrl,
        postAction,
        expandUrl;
    if (!item.apiURL) {
        return;
    }
    if (item.expand) {
        // turn to false
        collapseUrl = item.apiURL + 'collapse/';
        postAction = $osf.postJSON(collapseUrl, {});
        postAction.done(function () {
            item.expand = false;
            if (callback !== undefined) {
                callback();
            }
        }).fail($osf.handleJSONError);
    } else {
        // turn to true
        expandUrl = item.apiURL + 'expand/';
        postAction = $osf.postJSON(expandUrl, {});
        postAction.done(function () {
            item.expand = true;
            if (callback !== undefined) {
                callback();
            }
        }).fail($osf.handleJSONError);
    }
}

/**
 * Contributors have first person's name and then number of contributors. This function returns the proper html
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @returns {Object} A Mithril virtual DOM template object
 * @private
 */
function _poContributors(item) {
    if (!item.data.contributors) {
        return '';
    }

    return item.data.contributors.map(function (person, index, arr) {
        var comma;
        if (index === 0) {
            comma = '';
        } else {
            comma = ', ';
        }
        if (index > 2) {
            return;
        }
        if (index === 2) {
            return m('span', ' + ' + (arr.length - 2));
        }
        return m('span', comma + person.name);
    });
}

/**
 * Displays who modified the data and when. i.e. "6 days ago, by Uguz"
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @private
 */
function _poModified(item) {
    var personString = '';
    var dateString = '';
    if (item.data.modifiedDelta === 0) {
        return m('span');
    }
    dateString = moment.utc(item.data.dateModified).fromNow();
    if (item.data.modifiedBy !== '') {
        personString = ', by ' + item.data.modifiedBy.toString();
    }
    return m('span', dateString + personString);
}

/**
 * Organizes all the row displays based on what that item requires.
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @returns {Array} An array of columns as col objects
 * @this Treebeard.controller Check Treebeard API For available methods
 * @private
 */
function _poResolveRows(item) {
    var css = '',
        draggable = false,
        default_columns;
    if (item.data.permissions) {
        draggable = item.data.permissions.movable || item.data.permissions.copyable;
    }
    if(this.isMultiselected(item.id)){
        item.css = 'fangorn-selected';
    } else {
        item.css = '';
    }

    if (draggable) {
        css = 'po-draggable';
    }

    default_columns = [{
        data : 'name',  // Data field name
        folderIcons : true,
        filter : true,
        css : css,
        custom : _poTitleColumn
    }, {
        data : 'contributors',
        filter : false,
        custom : _poContributors
    }, {
        data : 'dateModified',
        filter : false,
        custom : _poModified
    }];
    return default_columns;
}

/**
 * Organizes the information for Column title row.
 * @returns {Array} An array of columns with pertinent column information
 * @private
 */
function _poColumnTitles() {
    var columns = [];
    columns.push({
        title: 'Name',
        width : '50%',
        sort : true,
        sortType : 'text'
    }, {
        title : 'Contributors',
        width : '25%',
        sort : false
    }, {
        title : 'Modified',
        width : '25%',
        sort : false
    });
    return columns;
}

/**
 * Checks if folder toggle is permitted (i.e. contents are private)
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {boolean}
 * @private
 */
function _poToggleCheck(item) {
    if (item.data.permissions.view) {
        return true;
    }
    item.notify.update('Not allowed: Private folder', 'warning', 1, undefined);
    return false;
}

/**
 * Returns custom folder toggle icons for OSF
 * @param {Object} item A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {string} Returns a mithril template with m() function, or empty string.
 * @private
 */
function _poResolveToggle(item) {
    var toggleMinus = m('i.fa.fa-minus'),
        togglePlus = m('i.fa.fa-plus'),
        childrenCount = item.data.childrenCount || item.children.length;
    if (item.kind === 'folder' && childrenCount > 0 && item.depth > 1) {
        if (item.open) {
            return toggleMinus;
        }
        return togglePlus;
    }
    return '';
}

/**
 * Resolves lazy load url for fetching children
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @returns {String|Boolean} Returns the fetch URL in string or false if there is no url.
 * @private
 */
function _poResolveLazyLoad(item) {

    return '/api/v1/dashboard/' + item.data.node_id;
}

/**
 * Hook to run after lazyloading has successfully loaded
 * @param {Object} item A Treebeard _item object for the row involved. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function expandStateLoad(item) {
    var tb = this,
        i;
    if (item.children.length === 0 && item.data.childrenCount > 0){
        item.data.childrenCount = 0;
        tb.updateFolder(null, item);
    }

    if (item.data.isPointer && !item.data.parentIsFolder) {
        item.data.expand = false;
    }
    if (item.children.length > 0 && item.depth > 0) {
        for (i = 0; i < item.children.length; i++) {
            if (item.children[i].data.expand) {
                tb.updateFolder(null, item.children[i]);
            }
            if (tb.multiselected()[0] && item.children[i].data.node_id === tb.multiselected()[0].data.node_id) {
                triggerClickOnItem.call(tb, item.children[i], true);
            }
        }
    }
    _cleanupMithril();
}

/**
 * Loads the children of an item that need to be expanded. Unique to Projectorganizer
 * @private
 */
function _poLoadOpenChildren() {
    var tb = this;
    tb.treeData.children.map(function (item) {
        if (item.data.expand) {
            tb.updateFolder(null, item);
        }
    });
}

/**
 * Hook to run after multiselect is run when an item is selected.
 * @param event Browser click event object
 * @param {Object} tree A Treebeard _item object. Node information is inside item.data
 * @this Treebeard.controller
 * @private
 */
function _poMultiselect(event, tree) {
    var tb = this;
    filterRowsNotInParent.call(tb, tb.multiselected());
    var scrollToItem = false;
    if (tb.toolbarMode() === 'search') {
        _dismissToolbar.call(tb);
        scrollToItem = true;
        // recursively open parents of the selected item but do not lazyload;
        Fangorn.Utils.openParentFolders.call(tb, tree);
    }
    if (tb.multiselected().length === 1) {
        // temporarily remove classes until mithril redraws raws with another hover.
        tb.inputValue(tb.multiselected()[0].data.name);
        tb.select('#tb-tbody').removeClass('unselectable');
        if (scrollToItem) {
            Fangorn.Utils.scrollToFile.call(tb, tb.multiselected()[0].id);
        }
    } else if (tb.multiselected().length > 1) {
        tb.select('#tb-tbody').addClass('unselectable');
    }
    m.redraw();
}

/**
 * Deletes pointers based on their ids from the folder specified
 * @param {String} pointerIds Unique node ids
 * @param folderToDeleteFrom  What it says
 */
function deleteMultiplePointersFromFolder(pointerIds, folderToDeleteFrom) {
    var tb = this,
        folderNodeId,
        url,
        postData,
        deleteAction;
    if (pointerIds.length > 0) {
        folderNodeId = folderToDeleteFrom.data.node_id;
        url = '/api/v1/folder/' + folderNodeId + '/pointers/';
        postData = JSON.stringify({pointerIds: pointerIds});
        deleteAction = $.ajax({
            type: 'DELETE',
            url: url,
            data: postData,
            contentType: 'application/json',
            dataType: 'json'
        });
        deleteAction.done(function () {
            tb.updateFolder(null, folderToDeleteFrom);
            tb.clearMultiselect();
        });
        deleteAction.fail(function (jqxhr, textStatus, errorThrown) {
            $osf.growl('Error:', textStatus + '. ' + errorThrown);
        });
    }
}

/**
 * When multiple rows are selected remove those that are not in the parent
 * @param {Array} rows List of item objects
 * @returns {Array} newRows Returns the revised list of rows
 */
function filterRowsNotInParent(rows) {
    var tb = this;
    if (tb.multiselected().length < 2) {
        return tb.multiselected();
    }
    var i, newRows = [],
        originalRow = tb.find(tb.multiselected()[0].id),
        originalParent,
        currentItem;
    var changeColor = function() { $(this).css('background-color', ''); };
    if (typeof originalRow !== 'undefined') {
        originalParent = originalRow.parentID;
        for (i = 0; i < rows.length; i++) {
            currentItem = rows[i];
            if (currentItem.parentID === originalParent && currentItem.id !== -1) {
                newRows.push(rows[i]);
            } else {
                $('.tb-row[data-id="' + rows[i].id + '"]').stop().css('background-color', '#D18C93').animate({ backgroundColor: '#fff'}, 500, changeColor);
            }
        }
    }
    tb.multiselected(newRows);
    tb.highlightMultiselect();
    return newRows;
}

/**
 * Hook for the drag start event on jquery
 * @param event jQuery UI drggable event object
 * @param ui jQuery UI draggable ui object
 * @private
 */
function _poDragStart(event, ui) {
    var tb = this;
    var itemID = $(event.target).attr('data-id'),
        item = tb.find(itemID);
    if (tb.multiselected().length < 2) {
        tb.multiselected([item]);
    }
}

/**
 * Hook for the drop event of jQuery UI droppable
 * @param event jQuery UI droppable event object
 * @param ui jQuery UI droppable ui object
 * @private
 */
function _poDrop(event, ui) {
    var tb = this;
    var items = tb.multiselected().length === 0 ? [tb.find(tb.selected)] : tb.multiselected(),
        folder = tb.find($(event.target).attr('data-id'));
    dropLogic.call(tb, event, items, folder);
}

/**
 * Hook for the over event of jQuery UI droppable
 * @param event jQuery UI droppable event object
 * @param ui jQuery UI droppable ui object
 * @private
 */
function _poOver(event, ui) {
    var tb = this;
    var items = tb.multiselected().length === 0 ? [tb.find(tb.selected)] : tb.multiselected(),
        folder = tb.find($(event.target).attr('data-id')),
        dragState = dragLogic.call(tb, event, items, ui);
    $('.tb-row').removeClass('tb-h-success po-hover');
    if (dragState !== 'forbidden') {
        $('.tb-row[data-id="' + folder.id + '"]').addClass('tb-h-success');
    } else {
        $('.tb-row[data-id="' + folder.id + '"]').addClass('po-hover');
    }
}

// Sets the state of the alt key by listening for key presses in the document.
var altKey = false;
$(document).keydown(function (e) {
    if (e.altKey) {
        altKey = true;
    }
});
$(document).keyup(function (e) {
    if (!e.altKey) {
        altKey = false;
    }
});

/**
 * Sets the copy state based on which item is being dragged on which other item
 * @param {Object} event Browser drag event
 * @param {Array} items List of items being dragged at the time. Each item is a _item object
 * @param {Object} ui jQuery UI draggable drag ui object
 * @returns {String} copyMode One of the copy states, from 'copy', 'move', 'forbidden'
 */
function dragLogic(event, items, ui) {
    var canCopy = true,
        canMove = true,
        folder = this.find($(event.target).attr('data-id')),
        isSelf = false,
        dragGhost = $('.tb-drag-ghost');
    items.forEach(function (item) {
        if (!isSelf) {
            isSelf = item.id === folder.id;
        }
        canCopy = canCopy && item.data.permissions.copyable;
        canMove = canMove && item.data.permissions.movable;
    });
    if (canAcceptDrop(items, folder) && (canMove || canCopy)) {
        if (canMove && canCopy) {
            if (altKey) {
                copyMode = 'copy';
            } else {
                copyMode = 'move';
            }
        }
        if (canMove && !canCopy) {
            copyMode = 'move';
        }
        if (canCopy && !canMove) {
            copyMode = 'copy';
        }
    } else {
        copyMode = 'forbidden';
    }
    if (isSelf) {
        copyMode = 'forbidden';
    }
    // Set the cursor to match the appropriate copy mode
    // Remember that Treebeard is using tb-drag-ghost instead of ui.helper

    switch (copyMode) {
    case 'forbidden':
        dragGhost.css('cursor', 'not-allowed');
        break;
    case 'copy':
        dragGhost.css('cursor', 'copy');
        break;
    case 'move':
        dragGhost.css('cursor', 'move');
        break;
    default:
        dragGhost.css('cursor', 'default');
    }
    return copyMode;
}

/**
 * Checks if the folder can accept the items dropped on it
 * @param {Array} items List of items being dragged at the time. Each item is a _item object
 * @param {Object} folder Folder information as _item object, the drop target
 * @returns {boolean} canDrop Whether drop can happen
 */
function canAcceptDrop(items, folder, theCopyMode) {
    if (typeof theCopyMode === 'undefined') {
        theCopyMode = copyMode;
    }
    var representativeItem,
        itemParentNodeId,
        hasComponents,
        hasFolders,
        copyable,
        movable,
        canDrop;
    if (folder.data.isSmartFolder || !folder.data.isFolder) {
        return false;
    }
    // if the folder is contained by the item, return false
    representativeItem = items[0];
    if (representativeItem.isAncestor(folder) || representativeItem.id === folder.id) {
        return false;
    }
    // If trying to drop on the folder it came from originally, return false
    itemParentNodeId = representativeItem.parent().data.node_id;
    if (itemParentNodeId === folder.data.node_id) {
        return false;
    }
    hasComponents = false;
    hasFolders = false;
    copyable = true;
    movable = true;
    canDrop = true;
    items.forEach(function (item) {
        hasComponents = hasComponents || item.data.isComponent;
        hasFolders = hasFolders || item.data.isFolder;
        copyable = copyable && item.data.permissions.copyable;
        movable = movable && item.data.permissions.movable;
    });
    if (hasComponents) {
        canDrop = canDrop && folder.data.permissions.acceptsComponents;
    }
    if (hasFolders) {
        canDrop = canDrop && folder.data.permissions.acceptsFolders;
    }
    if (theCopyMode === 'move') {
        canDrop = canDrop && folder.data.permissions.acceptsMoves && movable;
    }
    if (theCopyMode === 'copy') {
        canDrop = canDrop && folder.data.permissions.acceptsCopies && copyable;
    }
    return canDrop;
}

/**
 * Where the drop actions happen
 * @param event jQuery UI drop event
 * @param {Array} items List of items being dragged at the time. Each item is a _item object
 * @param {Object} folder Folder information as _item object
 */
function dropLogic(event, items, folder) {
    var tb = this,
        theFolderNodeID,
        getChildrenURL,
        folderChildren,
        sampleItem,
        itemParent,
        itemParentNodeID,
        getAction;
    if (typeof folder !== 'undefined' && !folder.data.isSmartFolder && folder !== null && folder.data.isFolder) {
        theFolderNodeID = folder.data.node_id;
        getChildrenURL = folder.data.apiURL + 'get_folder_pointers/';
        sampleItem = items[0];
        itemParent = sampleItem.parent();
        itemParentNodeID = itemParent.data.node_id;
        if (itemParentNodeID !== theFolderNodeID) { // This shouldn't happen, but if it does, it's bad
            getAction = $.getJSON(getChildrenURL, function (data) {
                folderChildren = data;
                var itemsToMove = [],
                    itemsNotToMove = [],
                    postInfo;
                items.forEach(function (item) {
                    if ($.inArray(item.data.node_id, folderChildren) === -1) { // pointer not in folder to be moved to
                        itemsToMove.push(item.data.node_id);
                    } else if (copyMode === 'move') { // Pointer is already in the folder and it's a move
                                // We  need to make sure not to delete the folder if the item is moved to the same folder.
                                // When we add the ability to reorganize within a folder, this will have to change.
                        itemsNotToMove.push(item.data.node_id);
                    }
                });
                postInfo = {
                    'copy': {
                        'url': '/api/v1/project/' + theFolderNodeID + '/pointer/',
                        'json': {
                            nodeIds: itemsToMove
                        }
                    },
                    'move': {
                        'url': '/api/v1/pointers/move/',
                        'json': {
                            pointerIds: itemsToMove,
                            toNodeId: theFolderNodeID,
                            fromNodeId: itemParentNodeID
                        }
                    }
                };
                if (copyMode === 'copy' || copyMode === 'move') {
                    deleteMultiplePointersFromFolder.call(tb, itemsNotToMove, itemParent);
                    if (itemsToMove.length > 0) {
                        var url = postInfo[copyMode].url,
                            postData = JSON.stringify(postInfo[copyMode].json),
                            outerFolder = whichIsContainer.call(tb, itemParent, folder),
                            postAction = $.ajax({
                                type: 'POST',
                                url: url,
                                data: postData,
                                contentType: 'application/json',
                                dataType: 'json'
                            });
                        postAction.always(function (result) {
                            if (copyMode === 'move') {
                                if (!outerFolder) {
                                    tb.updateFolder(null, itemParent);
                                    tb.updateFolder(null, folder);
                                } else {
                                    // if item is closed folder save expand state to be open
                                    if(!folder.data.expand){
                                        saveExpandState(folder.data, function(){
                                            tb.updateFolder(null, outerFolder);
                                        });
                                    } else {
                                        tb.updateFolder(null, outerFolder);
                                    }
                                }
                            } else {
                                tb.updateFolder(null, folder);
                            }
                        });
                        postAction.fail(function (jqxhr, textStatus, errorThrown) {
                            $osf.growl('Error:', textStatus + '. ' + errorThrown);
                        });
                    }
                }
            });
            getAction.fail(function (jqxhr, textStatus, errorThrown) {
                $osf.growl('Error:', textStatus + '. ' + errorThrown);
            });
        } else {
            Raven.captureMessage('Project dashboard: Parent node (' + itemParentNodeID + ') == Folder Node (' + theFolderNodeID + ')');
        }
    } else {
        if (typeof folder === 'undefined') {
            Raven.captureMessage('onDrop folder is undefined.');
        }
    }
    $('.project-organizer-dand').css('cursor', 'default');
}

/**
 * Checks if one of the items being moved contains the other. To check for adding parents to children
 * @param {Object} itemOne Treebeard _item object, has the _item API
 * @param {Object} itemTwo Treebeard _item object, has the _item API
 * @returns {null|Object} Returns object if one is containing the other. Null if neither or both
 */
function whichIsContainer(itemOne, itemTwo) {
    var isOneAncestor = itemOne.isAncestor(itemTwo),
        isTwoAncestor = itemTwo.isAncestor(itemOne);
    if (isOneAncestor && isTwoAncestor) {
        return null;
    }
    if (isOneAncestor) {
        return itemOne;
    }
    if (isTwoAncestor) {
        return itemTwo;
    }
    return null;
}

function _cleanupMithril() {
    // Clean up Mithril related redraw issues
    $('.tb-toggle-icon').each(function(){
        var children = $(this).children('i');
        if (children.length > 1) {
            children.last().remove();
        }
    });
}

function _addFolderEvent() {
    var tb = this;
    var val = $.trim($('#addNewFolder').val());
    if (tb.multiselected().length !== 1 || val.length < 1) {
        tb.toolbarMode(Fangorn.Components.toolbarModes.DEFAULT);
        return;
    }
    var item = tb.multiselected()[0];
    var theItem = item.data;
    var url = '/api/v1/folder/';
    var postData = {
            node_id: theItem.node_id,
            title: val
        };
    theItem.expand = false;
    saveExpandState(theItem, function () {
        var putAction = $osf.putJSON(url, postData);
        putAction.done(function () {
            tb.updateFolder(null, item);
            triggerClickOnItem.call(tb, item);
        }).fail($osf.handleJSONError);

    });
    tb.toolbarMode(Fangorn.Components.toolbarModes.DEFAULT);
}

function _renameEvent() {
    var tb = this;
    var val = $.trim($('#renameInput').val());
    if (tb.multiselected().length !== 1 || val.length < 1) {
        tb.toolbarMode(Fangorn.Components.toolbarModes.DEFAULT);
        return;
    }
    var item = tb.multiselected()[0];
    var theItem = item.data;
    var url = theItem.apiURL + 'edit/';
    var postAction;
    var postData = {
            name: 'title',
            value: val
        };
    postAction = $osf.postJSON(url, postData);
    postAction.done(function () {
        tb.updateFolder(null, tb.find(1));
        // Also update every
    }).fail($osf.handleJSONError);
    tb.toolbarMode(Fangorn.Components.toolbarModes.DEFAULT);
}

function applyTypeahead() {
    var tb = this;
    var item = tb.multiselected()[0];
    var theItem = item.data;
    projectOrganizer.myProjects.initialize();
    projectOrganizer.publicProjects.initialize();
    // injecting error into search results from https://github.com/twitter/typeahead.js/issues/747
    var mySourceWithEmptySelectable = function (q, cb) {
        var emptyMyProjects = [{ error: 'There are no matching projects to which you contribute.' }];
        projectOrganizer.myProjects.get(q, injectEmptySelectable);
        function injectEmptySelectable(suggestions) {
            if (suggestions.length === 0) {
                cb(emptyMyProjects);
            } else {
                cb(suggestions);
            }
        }
    };
    var publicSourceWithEmptySelectable = function (q, cb) {
        var emptyPublicProjects = { error: 'There are no matching public projects.' };
        projectOrganizer.publicProjects.get(q, injectEmptySelectable);
        function injectEmptySelectable(suggestions) {
            if (suggestions.length === 0) {
                cb([emptyPublicProjects]);
            } else {
                cb(suggestions);
            }
        }
    };

    if (!theItem.isSmartFolder) {
        $('#addprojectInput').typeahead('destroy');
        $('#addprojectInput').typeahead({
            highlight: true
        }, {
            name: 'my-projects',
            displayKey: function (data) {
                return data.name;
            },
            source: mySourceWithEmptySelectable,
            templates: {
                header: function () {
                    return '<h3 class="category">My Projects</h3>';
                },
                suggestion: function (data) {
                    if (typeof data.name !== 'undefined') {
                        return '<p>' + data.name + '</p>';
                    }
                    return '<p>' + data.error + '</p>';
                }
            }
        }, {
            name: 'public-projects',
            displayKey: function (data) {
                return data.name;
            },
            source: publicSourceWithEmptySelectable,
            templates: {
                header: function () {
                    return '<h3 class="category">Public Projects</h3>';
                },
                suggestion: function (data) {
                    if (typeof data.name !== 'undefined') {
                        return '<p>' + data.name + '</p>';
                    }
                    return '<p>' + data.error + '</p>';
                }
            }
        });
        $('#addprojectInput').bind('keyup', function (event) {
            var key = event.keyCode || event.which,
                buttonEnabled = $('#add-link-button').hasClass('tb-disabled');

            if (key === 13) {
                if (buttonEnabled) {
                    $('#add-link-button').click(); //submits if the control is active
                }
            } else {
                $('#add-link-warning').removeClass('p-sm').text('');
                $('#add-link-button').addClass('tb-disabled');
                linkName = '';
                linkID = '';
            }
        });
        $('#addprojectInput').bind('typeahead:selected', function (obj, datum, name) {
            var getChildrenURL = theItem.apiURL + 'get_folder_pointers/',
                children;
            $.getJSON(getChildrenURL, function (data) {
                children = data;
                if (children.indexOf(datum.node_id) === -1) {
                    $('#add-link-button').removeClass('tb-disabled');
                    linkName = datum.name;
                    linkID = datum.node_id;
                } else {
                    $('#add-link-warning').addClass('p-sm').text('This project is already in the folder');
                }
            }).fail($osf.handleJSONError);
        });
    }

}

function addProjectEvent() {
    var tb = this;
    var item = tb.multiselected()[0];
    var theItem = item.data;
    var url = '/api/v1/pointer/',
        postData = JSON.stringify({
            pointerID: linkID,
            toNodeID: theItem.node_id
        });
    theItem.expand = false;
    saveExpandState(theItem, function () {
        var postAction = $.ajax({
            type: 'POST',
            url: url,
            data: postData,
            contentType: 'application/json',
            dataType: 'json'
        });
        postAction.done(function () {
            tb.updateFolder(null, item);
        });
    });
    triggerClickOnItem.call(tb, item);
    tb.toolbarMode(Fangorn.Components.toolbarModes.DEFAULT);
    tb.select('.tb-header-row .twitter-typeahead').remove();
}

function showLegend() {
    var tb = this;
    var keys = Object.keys(projectOrganizerCategories);
    var data = keys.map(function (key) {
        return {
            icon: iconmap.componentIcons[key] || iconmap.projectIcons[key],
            label: nodeCategories[key] || projectOrganizerCategories[key]
        };
    });
    var repr = function (item) {
        return [
            m('span[style="width:18px"]', {
                className: item.icon
            }),
            '  ',
            item.label
        ];
    };
    var opts = {
        footer: m('span', ['*lighter color denotes a registration (e.g. ',
            m('span', {
                className: iconmap.componentIcons.data + ' po-icon'
            }),
            ' becomes  ',
            m('span', {
                className: iconmap.componentIcons.data + ' po-icon-registered'
            }),
            ' )'
            ])
    };
    var closeBtn = m('button', {
        class:'btn btn-default',
        type:'button',
        onclick : function(event) { tb.modal.dismiss(); } }, 'Close');

    tb.modal.update(legendView(data, repr, opts), closeBtn, m('h3.modal-title', 'Legend'));
    tb.modal.show();
}

var POItemButtons = {
    view : function (ctrl, args, children) {
        var tb = args.treebeard;
        var item = args.item;
        var buttons = [];
        if (!item.data.urls) {
            return m('div');
        }
        var url = item.data.urls.fetch;
        var theItem = item.data;
        var theParentNode = item.parent();
        var theParentNodeID = theParentNode.data.node_id;
        $('.fangorn-toolbar-icon').tooltip('destroy');
        if (!item.data.isSmartFolder) {
            if (url !== null) {
                buttons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            _gotoEvent.call(tb, event, item);
                        },
                        icon: 'fa fa-external-link',
                        className: 'text-primary'
                    }, 'Open')
                );
            }
        }
        if (!item.data.isSmartFolder && (item.data.isDashboard || item.data.isFolder)) {
            buttons.push(
                m.component(Fangorn.Components.button, {
                    onclick: function (event) {
                        tb.toolbarMode(Fangorn.Components.toolbarModes.ADDFOLDER);
                    },
                    icon: 'fa fa-cubes',
                    className: 'text-primary'
                }, 'Add Collection'),
                m.component(Fangorn.Components.button, {
                    onclick: function (event) {
                        tb.toolbarMode(Fangorn.Components.toolbarModes.ADDPROJECT);
                    },
                    icon: 'fa fa-cube',
                    className: 'text-primary'
                }, 'Add Existing Project')
            );
        }
        if (!item.data.isFolder && item.data.parentIsFolder && !item.parent().data.isSmartFolder) {
            buttons.push(
                m.component(Fangorn.Components.button, {
                    onclick: function (event) {
                        url = '/api/v1/folder/' + theParentNodeID + '/pointer/' + theItem.node_id;
                        var deleteAction = $.ajax({
                            type: 'DELETE',
                            url: url,
                            contentType: 'application/json',
                            dataType: 'json'
                        });
                        deleteAction.done(function () {
                            tb.updateFolder(null, theParentNode);
                            tb.clearMultiselect();
                        });
                        deleteAction.fail(function (xhr, status, error) {
                            Raven.captureMessage('Remove from collection in PO failed.', {
                                url: url,
                                textStatus: status,
                                error: error
                            });
                        });
                    },
                    icon: 'fa fa-minus',
                    className: 'text-primary'
                }, 'Remove from Collection')
            );
        }
        if (!item.data.isDashboard && !item.data.isRegistration && item.data.permissions && item.data.permissions.edit) {
            buttons.push(
                m.component(Fangorn.Components.button, {
                    onclick: function (event) {
                        tb.toolbarMode(Fangorn.Components.toolbarModes.RENAME);
                    },
                    icon: 'fa fa-font',
                    className: 'text-primary'
                }, 'Rename')
            );
        }
        if (item.data.isFolder && !item.data.isDashboard && !item.data.isSmartFolder) {
            buttons.push(
                m.component(Fangorn.Components.button, {
                    onclick: function (event) {
                        _deleteFolder.call(tb, item, theItem);
                    },
                    icon: 'fa fa-trash',
                    className: 'text-danger'
                }, 'Delete')
            );
        }
        return m('span', buttons);
    }
};

var _dismissToolbar = function () {
    var tb = this;
    if (tb.toolbarMode() === Fangorn.Components.toolbarModes.SEARCH){
        tb.resetFilter();
    }
    tb.toolbarMode(Fangorn.Components.toolbarModes.DEFAULT);
    tb.filterText('');
    tb.select('.tb-header-row .twitter-typeahead').remove();
    m.redraw();
};

var POToolbar = {
    controller: function (args) {
        var self = this;
        self.tb = args.treebeard;
        self.tb.toolbarMode = m.prop(Fangorn.Components.toolbarModes.DEFAULT);
        self.tb.inputValue = m.prop('');
        self.items = args.treebeard.multiselected;
        self.mode = self.tb.toolbarMode;
        self.helpText = m.prop('');
        self.dismissToolbar = _dismissToolbar.bind(self.tb);
    },
    view: function (ctrl) {
        var templates = {};
        var generalButtons = [];
        var rowButtons = [];
        var dismissIcon = m.component(Fangorn.Components.button, {
            onclick: ctrl.dismissToolbar,
            icon : 'fa fa-times'
        }, '');
        templates[Fangorn.Components.toolbarModes.SEARCH] =  [
            m('.col-xs-10', [
                ctrl.tb.options.filterTemplate.call(ctrl.tb)
            ]),
            m('.col-xs-2.tb-buttons-col',
                m('.fangorn-toolbar.pull-right',
                    [
                        m.component(Fangorn.Components.button, {
                            onclick: ctrl.dismissToolbar,
                            icon : 'fa fa-times'
                        }, 'Close')
                    ]
                    )
                )
        ];
        templates[Fangorn.Components.toolbarModes.ADDFOLDER] = [
            m('.col-xs-9',
                m.component(Fangorn.Components.input, {
                    onkeypress: function (event) {
                        if (ctrl.tb.pressedKey === ENTER_KEY) {
                            _addFolderEvent.call(ctrl.tb);
                        }
                    },
                    id : 'addNewFolder',
                    helpTextId : 'addFolderHelp',
                    placeholder : 'New collection name',
                }, ctrl.helpText())
                ),
            m('.col-xs-3.tb-buttons-col',
                m('.fangorn-toolbar.pull-right',
                    [
                        m.component(Fangorn.Components.button, {
                            onclick: function () {
                                _addFolderEvent.call(ctrl.tb);
                            },
                            icon : 'fa fa-plus',
                            className : 'text-info'
                        }, 'Add'),
                        dismissIcon
                    ]
                    )
                )
        ];
        templates[Fangorn.Components.toolbarModes.RENAME] = [
            m('.col-xs-9',
                m.component(Fangorn.Components.input, {
                    onkeypress: function (event) {
                        ctrl.tb.inputValue($(event.target).val());
                        if (ctrl.tb.pressedKey === ENTER_KEY) {
                            _renameEvent.call(ctrl.tb);
                        }
                    },
                    id : 'renameInput',
                    helpTextId : 'renameHelpText',
                    placeholder : null,
                    value : ctrl.tb.inputValue()
                }, ctrl.helpText())
                ),
            m('.col-xs-3.tb-buttons-col',
                m('.fangorn-toolbar.pull-right',
                    [
                        m.component(Fangorn.Components.button, {
                            onclick: function () {
                                _renameEvent.call(ctrl.tb);
                            },
                            icon : 'fa fa-pencil',
                            className : 'text-info'
                        }, 'Rename'),
                        dismissIcon
                    ]
                    )
                )
        ];
        templates[Fangorn.Components.toolbarModes.ADDPROJECT] = [
            m('.col-xs-9', [
                m('input#addprojectInput.tb-header-input', {
                    config : function () {
                        applyTypeahead.call(ctrl.tb);
                    },
                    onkeypress : function (event) {
                        if (ctrl.tb.pressedKey === ENTER_KEY) {
                            addProjectEvent.call(ctrl.tb);
                        }
                    },
                    type : 'text',
                    placeholder : 'Name of the project to find'
                }),
                m('#add-link-warning.text-warning')
            ]
                ),
            m('.col-xs-3.tb-buttons-col',
                m('.fangorn-toolbar.pull-right',
                    [
                        m.component(Fangorn.Components.button, {
                            onclick: function () {
                                addProjectEvent.call(ctrl.tb);
                            },
                            icon : 'fa fa-plus',
                            className : 'text-info'
                        }, 'Add'),
                        dismissIcon
                    ]
                    )
                )
        ];
        generalButtons.push(
            m.component(Fangorn.Components.button, {
                onclick: function (event) {
                    ctrl.mode(Fangorn.Components.toolbarModes.SEARCH);
                },
                icon: 'fa fa-search',
                className : 'text-primary'
            }, 'Search'),
            m.component(Fangorn.Components.button, {
                onclick: function (event) {
                    showLegend.call(ctrl.tb);
                },
                icon: 'fa fa-info',
                className : 'text-info'
            }, '')
        );
        if(ctrl.items().length > 1){
            var someItemsAreFolders = false;
            var pointerIds = [];
            var theParentNode = ctrl.items()[0].parent();
            ctrl.items().forEach(function (item) {
                var thisItem = item.data;
                someItemsAreFolders = (
                    someItemsAreFolders ||
                    thisItem.isFolder ||
                    thisItem.isSmartFolder ||
                    thisItem.parentIsSmartFolder ||
                    !thisItem.permissions.movable
                );
                pointerIds.push(thisItem.node_id);
            });
            if(!someItemsAreFolders){
                generalButtons.push(
                    m.component(Fangorn.Components.button, {
                        onclick: function (event) {
                            deleteMultiplePointersFromFolder.call(ctrl.tb, pointerIds, theParentNode);
                        },
                        icon: 'fa fa-minus',
                        className : 'text-primary'
                    }, 'Remove All from Collection')
                );
            }
        }
        if (ctrl.items().length === 1) {
            rowButtons = m.component(POItemButtons, {treebeard : ctrl.tb, item : ctrl.items()[0]});
        }
        templates[Fangorn.Components.toolbarModes.DEFAULT] = m('.col-xs-12',m('.pull-right', [rowButtons, generalButtons]));
        return m('.row.tb-header-row', [
            m('#headerRow', { config : function () {
                $('#headerRow input').focus();
            }}, [
                templates[ctrl.mode()]
            ])
        ]);
    }
};


function _deleteFolder(item) {
    var tb = this;
    var theItem = item.data;
    function runDeleteFolder() {
        var url = '/api/v1/folder/' + theItem.node_id;
        var deleteAction = $.ajax({
                type: 'DELETE',
                url: url,
                contentType: 'application/json',
                dataType: 'json'
            });
        deleteAction.done(function () {
            tb.updateFolder(null, item.parent());
            tb.modal.dismiss();
            tb.select('.tb-row').first().trigger('click');
        });
    }
    var mithrilContent = m('div', [
            m('p', 'Are you sure you want to delete this Collection? This will also delete any Collections ' +
                'inside this one. You will not delete any projects in this Collection.')
        ]);
    var mithrilButtons = m('div', [
            m('span.btn.btn-default', { onclick : function() { tb.modal.dismiss(); } }, 'Cancel'),
            m('span.btn.btn-danger', { onclick : function() { runDeleteFolder(); }  }, 'Delete')
        ]);
    tb.modal.update(mithrilContent, mithrilButtons,  m('h3.break-word.modal-title', 'Delete "' + theItem.name + '"?'));
}

/**
 * OSF-specific Treebeard options common to all addons.
 * For documentation visit: https://github.com/caneruguz/treebeard/wiki
 */
var tbOptions = {
    rowHeight : 35,         // user can override or get from .tb-row height
    showTotal : 15,         // Actually this is calculated with div height, not needed. NEEDS CHECKING
    paginate : false,       // Whether the applet starts with pagination or not.
    paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
    uploads : false,         // Turns dropzone on/off.
    columnTitles : _poColumnTitles,
    resolveRows : _poResolveRows,
    showFilter : true,     // Gives the option to filter by showing the filter box.
    title : false,          // Title of the grid, boolean, string OR function that returns a string.
    allowMove : true,       // Turn moving on or off.
    moveClass : 'po-draggable',
    hoverClass : 'fangorn-hover',
    hoverClassMultiselect : 'fangorn-selected',
    togglecheck : _poToggleCheck,
    sortButtonSelector : {
        up : 'i.fa.fa-chevron-up',
        down : 'i.fa.fa-chevron-down'
    },
    sortDepth : 1,
    dragOptions : {},
    dropOptions : {},
    dragEvents : {
        start : _poDragStart
    },
    dropEvents : {
        drop : _poDrop,
        over : _poOver
    },
    onload : function () {
        var tb = this,
            rowDiv = tb.select('.tb-row');
        _poLoadOpenChildren.call(tb);
        rowDiv.first().trigger('click');

        $('.gridWrapper').on('mouseout', function () {
            tb.select('.tb-row').removeClass('po-hover');
        });
    },
    createcheck : function (item, parent) {
        return true;
    },
    deletecheck : function (item) {
        return true;
    },
    ontogglefolder : function (item, event) {
        if (event) {
            saveExpandState(item.data);
        }
        if (!item.open) {
            item.load = false;
        }
        $('[data-toggle="tooltip"]').tooltip();
    },
    onscrollcomplete : function () {
        $('[data-toggle="tooltip"]').tooltip();
        _cleanupMithril();
    },
    onmultiselect : _poMultiselect,
    resolveIcon : Fangorn.Utils.resolveIconView,
    resolveToggle : _poResolveToggle,
    resolveLazyloadUrl : _poResolveLazyLoad,
    lazyLoadOnLoad : expandStateLoad,
    resolveRefreshIcon : function () {
        return m('i.fa.fa-refresh.fa-spin');
    },
    toolbarComponent : POToolbar,
    naturalScrollLimit : 0,
    removeIcon : function(){
        return m.trust('&times;');
    },
};

/**
 * Initialize Project organizer in the fashion of Fangorn. Prepeares an option object within ProjectOrganizer
 * @param options Treebeard type options to be extended with Treebeard default options.
 * @constructor
 */
function ProjectOrganizer(options) {
    this.options = $.extend({}, tbOptions, options);
    this.grid = null; // Set by _initGrid
    this.init();
}
/**
 * Project organizer prototype object with init functions set to Treebeard.
 * @type {{constructor: ProjectOrganizer, init: Function, _initGrid: Function}}
 */
ProjectOrganizer.prototype = {
    constructor: ProjectOrganizer,
    init: function () {
        this._initGrid();
    },
    _initGrid: function () {
        this.grid = new Treebeard(this.options);
        return this.grid;
    }
};

module.exports = {
    ProjectOrganizer: ProjectOrganizer,
    _whichIsContainer: whichIsContainer,
    _canAcceptDrop: canAcceptDrop
};


/***/ },

/***/ 184:
/***/ function(module, exports, __webpack_require__) {

// style-loader: Adds some css to the DOM by adding a <style> tag

// load the styles
var content = __webpack_require__(185);
if(typeof content === 'string') content = [[module.id, content, '']];
// add the styles to the DOM
var update = __webpack_require__(19)(content, {});
// Hot Module Replacement
if(false) {
	// When the styles change, update the <style> tags
	module.hot.accept("!!/Users/laurenbarker/GitHub/osf.io/node_modules/css-loader/index.js!/Users/laurenbarker/GitHub/osf.io/website/static/css/projectorganizer.css", function() {
		var newContent = require("!!/Users/laurenbarker/GitHub/osf.io/node_modules/css-loader/index.js!/Users/laurenbarker/GitHub/osf.io/website/static/css/projectorganizer.css");
		if(typeof newContent === 'string') newContent = [[module.id, newContent, '']];
		update(newContent);
	});
	// When the module is disposed, remove the <style> tags
	module.hot.dispose(function() { update(); });
}

/***/ },

/***/ 185:
/***/ function(module, exports, __webpack_require__) {

exports = module.exports = __webpack_require__(16)();
exports.push([module.id, ".po-hover-multiselect {\n    background : lightgoldenrodyellow;\n}\n\n/* @override http://localhost:5000/static/css/projectorganizer.css */\n\nspan.project-smart-folder.smart-folder{\n    font-style: italic;\n}\n\n/* Project organizer icons */\nspan.project-organizer-icon-folder {\n    display: inline-block;\n    width: 16px;\n    height: 16px;\n    vertical-align: middle;\n    background-image: url('/static/img/hgrid/folder.png');\n    background-repeat: no-repeat;\n}\n\nspan.project-organizer-icon-smart-folder {\n    display: inline-block;\n    width: 16px;\n    height: 16px;\n    vertical-align: middle;\n    background-image: url('/static/img/hgrid/smart-folder.png');\n    background-repeat: no-repeat;\n}\n\nspan.project-organizer-icon-project {\n    display: inline-block;\n    width: 16px;\n    height: 16px;\n    vertical-align: middle;\n    background-image: url('/static/img/hgrid/project.png');\n    background-repeat: no-repeat;\n}\n\nspan.project-organizer-icon-project:hover {\n    display: inline-block;\n    width: 16px;\n    height: 16px;\n    vertical-align: middle;\n    background-image: url('/static/img/hgrid/project-hover.png');\n    background-repeat: no-repeat;\n}\n\nspan.project-organizer-icon-component {\n    display: inline-block;\n    width: 16px;\n    height: 16px;\n    vertical-align: middle;\n    background-image: url('/static/img/hgrid/component.png');\n    background-repeat: no-repeat;\n}\n\nspan.project-organizer-icon-component:hover {\n    display: inline-block;\n    width: 16px;\n    height: 16px;\n    vertical-align: middle;\n    background-image: url('/static/img/hgrid/component-hover.png');\n    background-repeat: no-repeat;\n}\n\nspan.project-organizer-icon-pointer {\n    display: inline-block;\n    width: 16px;\n    height: 16px;\n    vertical-align: middle;\n    background-image: url('/static/img/hgrid/pointer.png');\n    background-repeat: no-repeat;\n}\n\nspan.project-organizer-icon-reg-pointer {\n    display: inline-block;\n    width: 16px;\n    height: 16px;\n    vertical-align: middle;\n    background-image: url('/static/img/hgrid/reg-pointer.png');\n    background-repeat: no-repeat;\n}\n\n\nspan.project-organizer-icon-reg-pointer:hover {\n    background-image: url('/static/img/hgrid/pointer-hover.png');\n    background-repeat: no-repeat;\n}\n\nspan.project-organizer-icon-pointer:hover {\n    display: inline-block;\n    width: 16px;\n    height: 16px;\n    vertical-align: middle;\n    background-image: url('/static/img/hgrid/pointer-hover.png');\n    background-repeat: no-repeat;\n}\n\nspan.project-organizer-icon-reg-project {\n    display: inline-block;\n    width: 16px;\n    height: 16px;\n    vertical-align: middle;\n    background-image: url('/static/img/hgrid/reg-project.png');\n    background-repeat: no-repeat;\n}\n\nspan.project-organizer-icon-reg-project:hover {\n    display: inline-block;\n    width: 16px;\n    height: 16px;\n    vertical-align: middle;\n    background-image: url('/static/img/hgrid/reg-project-hover.png');\n    background-repeat: no-repeat;\n}\n\nspan.project-organizer-icon-reg-component {\n    display: inline-block;\n    width: 16px;\n    height: 16px;\n    vertical-align: middle;\n    background-image: url('/static/img/hgrid/reg-component.png');\n    background-repeat: no-repeat;\n}\n\nspan.project-organizer-icon-reg-component:hover {\n    display: inline-block;\n    width: 16px;\n    height: 16px;\n    vertical-align: middle;\n    background-image: url('/static/img/hgrid/reg-component-hover.png');\n    background-repeat: no-repeat;\n}\n\nbutton.project-organizer-icon-info {\n    width: 20px;\n    height: 20px;\n    background-image: url('/static/img/hgrid/info.png');\n    background-repeat: no-repeat;\n}\n\nbutton.project-organizer-icon-visit {\n    width: 20px;\n    height: 20px;\n    background-image: url('/static/img/hgrid/visit.png');\n    background-repeat: no-repeat;\n}\n\nbutton.hg-btn {\n    background-color: transparent;\n    border: 0px;\n}\n\n\n/* Preventing folders that are HGrid leaves from showing underlines when hovered over */\n\n.project-folder:hover {\n    text-decoration: none !important;\n}\n\nspan.project-folder {\n    text-decoration: none;\n}\n\n.hg-item-name:hover {\n    text-decoration: none !important;\n    cursor: default;\n}\n\n/* Controls above the HGrid */\n\ndiv.project-grid-menu {\n    text-align: right;\n    margin-top: -20px;\n}\n\ndiv.project-grid-menu span.pg-expand-all {\n    color: #468cc8;\n    text-decoration: underline;\n    cursor: pointer;\n    margin-right: 10px;\n}\n\ndiv.project-grid-menu span.pg-collapse-all {\n    color: #468cc8;\n    text-decoration: underline;\n    cursor: pointer;\n    margin-right: 7px;\n}\n\n.page-header .btn {\n    margin-right: 5px;\n}\n\n/* Project details box  */\nspan.project-details {\n    visibility: hidden;\n}\n\n\nspan.add-link-warning {\n    color: #808080;\n}\n\ndiv.add-folder-container {\n    display: none;\n\n}\n\nspan.rename-container{\n    display: none;\n}\n\ndiv.project-details span.title {\n    display: inline;\n    overflow-x: hidden;\n    font-size: 15px;\n    overflow-x: hidden;\n}\n\n\n.project-action-icons img {\n    margin-right: 4px;\n    cursor:pointer;cursor:hand\n}\n\ndiv.project-details {\n    display: inline-block;\n    width: 100%;\n    background-color: #EEE;\n    padding: 7px;\n    margin-bottom: 10px;\n}\n\ndiv.contributors {\n    overflow-x: hidden;\n}\n\n.organize-project-controls {\n    z-index: 11;\n}\n\ndiv.organize-project-controls {\n    display: block;\n    position: relative;\n    bottom: 0;\n    width: 100%;\n    text-align: right;\n}\n\n.organize-project-controls .organizeBtn.btn.btn-default {\n    display: block;\n    margin-right: 10px;\n    float: left;\n    margin-bottom: 10px;\n}\n\n/* Typeahead autocomplete box */\n\n\n\n.organize-project-controls span.twitter-typeahead {\n    width: 100%;\n}\n\n/* Typeahead scaffolding */\n/* ----------- */\n\n.tt-dropdown-menu,\n.gist {\n    text-align: left;\n    overflow-x: hidden;\n}\n\n/* Typeahead base styles */\n/* ----------- */\n\n.typeahead,\n.tt-query {\n    width: 100%;\n    height: 30px;\n    font-size: 16px;\n    border: 1px solid rgb(204, 204, 204);\n    -webkit-border-radius: 4px;\n    -moz-border-radius: 4px;\n    border-radius: 4px;\n    outline: none;\n}\ninput.typeahead.tt-input {\nheight: 32px ;\n}\n\n.typeahead {\n    background-color: #fff;\n}\n\n.tt-query {\n    -webkit-box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.075);\n    -moz-box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.075);\n    box-shadow: inset 0 1px 1px rgba(0, 0, 0, 0.075);\n}\n/* rgb of glow 106 176 232\n*/\n.tt-input, .typeahead {\n    padding: 4px 10px;\n}\n\n.tt-hint {\n    color: #999;\n    padding: 0px 12px 3px 8px\n}\nh3.category {\n    font-size: 18px;\n    margin-top: 4px;\n    margin-left: 5px;\n}\n.tt-dropdown-menu {\n    width: 422px;\n    padding: 8px 0;\n    background-color: #fff;\n    border: 1px solid #ccc;\n    border: 1px solid rgba(0, 0, 0, 0.2);\n    -webkit-border-radius: 5px;\n    -moz-border-radius: 5px;\n    border-radius: 5px;\n    -webkit-box-shadow: 0 5px 10px rgba(0, 0, 0, .2);\n    -moz-box-shadow: 0 5px 10px rgba(0, 0, 0, .2);\n    box-shadow: 0 5px 10px rgba(0, 0, 0, .2);\n    margin-top: 6px;\n}\n\n.tt-suggestion {\n    padding: 3px 5px;\n    font-size: 12px;\n    line-height: 14px;\n}\n\n.tt-suggestion.tt-cursor {\n    color: #fff;\n    background-color: #0097cf;\n\n}\n\n/*.tt-suggestion p {\n    margin: 0;\n}*/\n\n.gist {\n    font-size: 14px;\n}\n.tb-row {\n    font-size: 13px;\n    line-height: 30px;\n}\n\n.po-hover {\n    background : #E0EBF3;\n}\n\n.tb-td {\n    height: inherit;\n    padding-top: 4px;\n}\n\n/* Project Toolbar New Additions and Changes */\n\n.po-placeholder {\n    line-height: 30px;\n}\n\n#project-grid {\n    margin-bottom: 5px;\n}\n\n.organizer-legend {\n    font-size: 13px;\n    padding-left: 4px;\n}\n\n.organizer-legend img {\n    vertical-align: bottom;\n    margin-right: 4px;\n}\n.tb-h-success {\n    background: #B8ECC0;\n}\n.po-icon-registered {\n    color: #D4D4D4;\n}\n.po-icon {\n    color: #5E5E5E;\n}\n.fangorn-selected .po-icon-registered {\n    color: #CCCCCC;\n}\n.fangorn-selected .po-icon {\n    color: #FFFFFF;\n}\n.po-modal {\n    width: auto;\n}\n.smaller {\n    font-size: 75%;\n}\n\n.registration-archiving {\n    cursor: default;\n}", ""]);

/***/ },

/***/ 188:
/***/ function(module, exports, __webpack_require__) {

/* WEBPACK VAR INJECTION */(function(setImmediate) {/*!
 * typeahead.js 0.10.5
 * https://github.com/twitter/typeahead.js
 * Copyright 2013-2014 Twitter, Inc. and other contributors; Licensed MIT
 */

(function($) {
    var _ = function() {
        "use strict";
        return {
            isMsie: function() {
                return /(msie|trident)/i.test(navigator.userAgent) ? navigator.userAgent.match(/(msie |rv:)(\d+(.\d+)?)/i)[2] : false;
            },
            isBlankString: function(str) {
                return !str || /^\s*$/.test(str);
            },
            escapeRegExChars: function(str) {
                return str.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&");
            },
            isString: function(obj) {
                return typeof obj === "string";
            },
            isNumber: function(obj) {
                return typeof obj === "number";
            },
            isArray: $.isArray,
            isFunction: $.isFunction,
            isObject: $.isPlainObject,
            isUndefined: function(obj) {
                return typeof obj === "undefined";
            },
            toStr: function toStr(s) {
                return _.isUndefined(s) || s === null ? "" : s + "";
            },
            bind: $.proxy,
            each: function(collection, cb) {
                $.each(collection, reverseArgs);
                function reverseArgs(index, value) {
                    return cb(value, index);
                }
            },
            map: $.map,
            filter: $.grep,
            every: function(obj, test) {
                var result = true;
                if (!obj) {
                    return result;
                }
                $.each(obj, function(key, val) {
                    if (!(result = test.call(null, val, key, obj))) {
                        return false;
                    }
                });
                return !!result;
            },
            some: function(obj, test) {
                var result = false;
                if (!obj) {
                    return result;
                }
                $.each(obj, function(key, val) {
                    if (result = test.call(null, val, key, obj)) {
                        return false;
                    }
                });
                return !!result;
            },
            mixin: $.extend,
            getUniqueId: function() {
                var counter = 0;
                return function() {
                    return counter++;
                };
            }(),
            templatify: function templatify(obj) {
                return $.isFunction(obj) ? obj : template;
                function template() {
                    return String(obj);
                }
            },
            defer: function(fn) {
                setTimeout(fn, 0);
            },
            debounce: function(func, wait, immediate) {
                var timeout, result;
                return function() {
                    var context = this, args = arguments, later, callNow;
                    later = function() {
                        timeout = null;
                        if (!immediate) {
                            result = func.apply(context, args);
                        }
                    };
                    callNow = immediate && !timeout;
                    clearTimeout(timeout);
                    timeout = setTimeout(later, wait);
                    if (callNow) {
                        result = func.apply(context, args);
                    }
                    return result;
                };
            },
            throttle: function(func, wait) {
                var context, args, timeout, result, previous, later;
                previous = 0;
                later = function() {
                    previous = new Date();
                    timeout = null;
                    result = func.apply(context, args);
                };
                return function() {
                    var now = new Date(), remaining = wait - (now - previous);
                    context = this;
                    args = arguments;
                    if (remaining <= 0) {
                        clearTimeout(timeout);
                        timeout = null;
                        previous = now;
                        result = func.apply(context, args);
                    } else if (!timeout) {
                        timeout = setTimeout(later, remaining);
                    }
                    return result;
                };
            },
            noop: function() {}
        };
    }();
    var VERSION = "0.10.5";
    var tokenizers = function() {
        "use strict";
        return {
            nonword: nonword,
            whitespace: whitespace,
            obj: {
                nonword: getObjTokenizer(nonword),
                whitespace: getObjTokenizer(whitespace)
            }
        };
        function whitespace(str) {
            str = _.toStr(str);
            return str ? str.split(/\s+/) : [];
        }
        function nonword(str) {
            str = _.toStr(str);
            return str ? str.split(/\W+/) : [];
        }
        function getObjTokenizer(tokenizer) {
            return function setKey() {
                var args = [].slice.call(arguments, 0);
                return function tokenize(o) {
                    var tokens = [];
                    _.each(args, function(k) {
                        tokens = tokens.concat(tokenizer(_.toStr(o[k])));
                    });
                    return tokens;
                };
            };
        }
    }();
    var LruCache = function() {
        "use strict";
        function LruCache(maxSize) {
            this.maxSize = _.isNumber(maxSize) ? maxSize : 100;
            this.reset();
            if (this.maxSize <= 0) {
                this.set = this.get = $.noop;
            }
        }
        _.mixin(LruCache.prototype, {
            set: function set(key, val) {
                var tailItem = this.list.tail, node;
                if (this.size >= this.maxSize) {
                    this.list.remove(tailItem);
                    delete this.hash[tailItem.key];
                }
                if (node = this.hash[key]) {
                    node.val = val;
                    this.list.moveToFront(node);
                } else {
                    node = new Node(key, val);
                    this.list.add(node);
                    this.hash[key] = node;
                    this.size++;
                }
            },
            get: function get(key) {
                var node = this.hash[key];
                if (node) {
                    this.list.moveToFront(node);
                    return node.val;
                }
            },
            reset: function reset() {
                this.size = 0;
                this.hash = {};
                this.list = new List();
            }
        });
        function List() {
            this.head = this.tail = null;
        }
        _.mixin(List.prototype, {
            add: function add(node) {
                if (this.head) {
                    node.next = this.head;
                    this.head.prev = node;
                }
                this.head = node;
                this.tail = this.tail || node;
            },
            remove: function remove(node) {
                node.prev ? node.prev.next = node.next : this.head = node.next;
                node.next ? node.next.prev = node.prev : this.tail = node.prev;
            },
            moveToFront: function(node) {
                this.remove(node);
                this.add(node);
            }
        });
        function Node(key, val) {
            this.key = key;
            this.val = val;
            this.prev = this.next = null;
        }
        return LruCache;
    }();
    var PersistentStorage = function() {
        "use strict";
        var ls, methods;
        try {
            ls = window.localStorage;
            ls.setItem("~~~", "!");
            ls.removeItem("~~~");
        } catch (err) {
            ls = null;
        }
        function PersistentStorage(namespace) {
            this.prefix = [ "__", namespace, "__" ].join("");
            this.ttlKey = "__ttl__";
            this.keyMatcher = new RegExp("^" + _.escapeRegExChars(this.prefix));
        }
        if (ls && window.JSON) {
            methods = {
                _prefix: function(key) {
                    return this.prefix + key;
                },
                _ttlKey: function(key) {
                    return this._prefix(key) + this.ttlKey;
                },
                get: function(key) {
                    if (this.isExpired(key)) {
                        this.remove(key);
                    }
                    return decode(ls.getItem(this._prefix(key)));
                },
                set: function(key, val, ttl) {
                    if (_.isNumber(ttl)) {
                        ls.setItem(this._ttlKey(key), encode(now() + ttl));
                    } else {
                        ls.removeItem(this._ttlKey(key));
                    }
                    return ls.setItem(this._prefix(key), encode(val));
                },
                remove: function(key) {
                    ls.removeItem(this._ttlKey(key));
                    ls.removeItem(this._prefix(key));
                    return this;
                },
                clear: function() {
                    var i, key, keys = [], len = ls.length;
                    for (i = 0; i < len; i++) {
                        if ((key = ls.key(i)).match(this.keyMatcher)) {
                            keys.push(key.replace(this.keyMatcher, ""));
                        }
                    }
                    for (i = keys.length; i--; ) {
                        this.remove(keys[i]);
                    }
                    return this;
                },
                isExpired: function(key) {
                    var ttl = decode(ls.getItem(this._ttlKey(key)));
                    return _.isNumber(ttl) && now() > ttl ? true : false;
                }
            };
        } else {
            methods = {
                get: _.noop,
                set: _.noop,
                remove: _.noop,
                clear: _.noop,
                isExpired: _.noop
            };
        }
        _.mixin(PersistentStorage.prototype, methods);
        return PersistentStorage;
        function now() {
            return new Date().getTime();
        }
        function encode(val) {
            return JSON.stringify(_.isUndefined(val) ? null : val);
        }
        function decode(val) {
            return JSON.parse(val);
        }
    }();
    var Transport = function() {
        "use strict";
        var pendingRequestsCount = 0, pendingRequests = {}, maxPendingRequests = 6, sharedCache = new LruCache(10);
        function Transport(o) {
            o = o || {};
            this.cancelled = false;
            this.lastUrl = null;
            this._send = o.transport ? callbackToDeferred(o.transport) : $.ajax;
            this._get = o.rateLimiter ? o.rateLimiter(this._get) : this._get;
            this._cache = o.cache === false ? new LruCache(0) : sharedCache;
        }
        Transport.setMaxPendingRequests = function setMaxPendingRequests(num) {
            maxPendingRequests = num;
        };
        Transport.resetCache = function resetCache() {
            sharedCache.reset();
        };
        _.mixin(Transport.prototype, {
            _get: function(url, o, cb) {
                var that = this, jqXhr;
                if (this.cancelled || url !== this.lastUrl) {
                    return;
                }
                if (jqXhr = pendingRequests[url]) {
                    jqXhr.done(done).fail(fail);
                } else if (pendingRequestsCount < maxPendingRequests) {
                    pendingRequestsCount++;
                    pendingRequests[url] = this._send(url, o).done(done).fail(fail).always(always);
                } else {
                    this.onDeckRequestArgs = [].slice.call(arguments, 0);
                }
                function done(resp) {
                    cb && cb(null, resp);
                    that._cache.set(url, resp);
                }
                function fail() {
                    cb && cb(true);
                }
                function always() {
                    pendingRequestsCount--;
                    delete pendingRequests[url];
                    if (that.onDeckRequestArgs) {
                        that._get.apply(that, that.onDeckRequestArgs);
                        that.onDeckRequestArgs = null;
                    }
                }
            },
            get: function(url, o, cb) {
                var resp;
                if (_.isFunction(o)) {
                    cb = o;
                    o = {};
                }
                this.cancelled = false;
                this.lastUrl = url;
                if (resp = this._cache.get(url)) {
                    _.defer(function() {
                        cb && cb(null, resp);
                    });
                } else {
                    this._get(url, o, cb);
                }
                return !!resp;
            },
            cancel: function() {
                this.cancelled = true;
            }
        });
        return Transport;
        function callbackToDeferred(fn) {
            return function customSendWrapper(url, o) {
                var deferred = $.Deferred();
                fn(url, o, onSuccess, onError);
                return deferred;
                function onSuccess(resp) {
                    _.defer(function() {
                        deferred.resolve(resp);
                    });
                }
                function onError(err) {
                    _.defer(function() {
                        deferred.reject(err);
                    });
                }
            };
        }
    }();
    var SearchIndex = function() {
        "use strict";
        function SearchIndex(o) {
            o = o || {};
            if (!o.datumTokenizer || !o.queryTokenizer) {
                $.error("datumTokenizer and queryTokenizer are both required");
            }
            this.datumTokenizer = o.datumTokenizer;
            this.queryTokenizer = o.queryTokenizer;
            this.reset();
        }
        _.mixin(SearchIndex.prototype, {
            bootstrap: function bootstrap(o) {
                this.datums = o.datums;
                this.trie = o.trie;
            },
            add: function(data) {
                var that = this;
                data = _.isArray(data) ? data : [ data ];
                _.each(data, function(datum) {
                    var id, tokens;
                    id = that.datums.push(datum) - 1;
                    tokens = normalizeTokens(that.datumTokenizer(datum));
                    _.each(tokens, function(token) {
                        var node, chars, ch;
                        node = that.trie;
                        chars = token.split("");
                        while (ch = chars.shift()) {
                            node = node.children[ch] || (node.children[ch] = newNode());
                            node.ids.push(id);
                        }
                    });
                });
            },
            get: function get(query) {
                var that = this, tokens, matches;
                tokens = normalizeTokens(this.queryTokenizer(query));
                _.each(tokens, function(token) {
                    var node, chars, ch, ids;
                    if (matches && matches.length === 0) {
                        return false;
                    }
                    node = that.trie;
                    chars = token.split("");
                    while (node && (ch = chars.shift())) {
                        node = node.children[ch];
                    }
                    if (node && chars.length === 0) {
                        ids = node.ids.slice(0);
                        matches = matches ? getIntersection(matches, ids) : ids;
                    } else {
                        matches = [];
                        return false;
                    }
                });
                return matches ? _.map(unique(matches), function(id) {
                    return that.datums[id];
                }) : [];
            },
            reset: function reset() {
                this.datums = [];
                this.trie = newNode();
            },
            serialize: function serialize() {
                return {
                    datums: this.datums,
                    trie: this.trie
                };
            }
        });
        return SearchIndex;
        function normalizeTokens(tokens) {
            tokens = _.filter(tokens, function(token) {
                return !!token;
            });
            tokens = _.map(tokens, function(token) {
                return token.toLowerCase();
            });
            return tokens;
        }
        function newNode() {
            return {
                ids: [],
                children: {}
            };
        }
        function unique(array) {
            var seen = {}, uniques = [];
            for (var i = 0, len = array.length; i < len; i++) {
                if (!seen[array[i]]) {
                    seen[array[i]] = true;
                    uniques.push(array[i]);
                }
            }
            return uniques;
        }
        function getIntersection(arrayA, arrayB) {
            var ai = 0, bi = 0, intersection = [];
            arrayA = arrayA.sort(compare);
            arrayB = arrayB.sort(compare);
            var lenArrayA = arrayA.length, lenArrayB = arrayB.length;
            while (ai < lenArrayA && bi < lenArrayB) {
                if (arrayA[ai] < arrayB[bi]) {
                    ai++;
                } else if (arrayA[ai] > arrayB[bi]) {
                    bi++;
                } else {
                    intersection.push(arrayA[ai]);
                    ai++;
                    bi++;
                }
            }
            return intersection;
            function compare(a, b) {
                return a - b;
            }
        }
    }();
    var oParser = function() {
        "use strict";
        return {
            local: getLocal,
            prefetch: getPrefetch,
            remote: getRemote
        };
        function getLocal(o) {
            return o.local || null;
        }
        function getPrefetch(o) {
            var prefetch, defaults;
            defaults = {
                url: null,
                thumbprint: "",
                ttl: 24 * 60 * 60 * 1e3,
                filter: null,
                ajax: {}
            };
            if (prefetch = o.prefetch || null) {
                prefetch = _.isString(prefetch) ? {
                    url: prefetch
                } : prefetch;
                prefetch = _.mixin(defaults, prefetch);
                prefetch.thumbprint = VERSION + prefetch.thumbprint;
                prefetch.ajax.type = prefetch.ajax.type || "GET";
                prefetch.ajax.dataType = prefetch.ajax.dataType || "json";
                !prefetch.url && $.error("prefetch requires url to be set");
            }
            return prefetch;
        }
        function getRemote(o) {
            var remote, defaults;
            defaults = {
                url: null,
                cache: true,
                wildcard: "%QUERY",
                replace: null,
                rateLimitBy: "debounce",
                rateLimitWait: 300,
                send: null,
                filter: null,
                ajax: {}
            };
            if (remote = o.remote || null) {
                remote = _.isString(remote) ? {
                    url: remote
                } : remote;
                remote = _.mixin(defaults, remote);
                remote.rateLimiter = /^throttle$/i.test(remote.rateLimitBy) ? byThrottle(remote.rateLimitWait) : byDebounce(remote.rateLimitWait);
                remote.ajax.type = remote.ajax.type || "GET";
                remote.ajax.dataType = remote.ajax.dataType || "json";
                delete remote.rateLimitBy;
                delete remote.rateLimitWait;
                !remote.url && $.error("remote requires url to be set");
            }
            return remote;
            function byDebounce(wait) {
                return function(fn) {
                    return _.debounce(fn, wait);
                };
            }
            function byThrottle(wait) {
                return function(fn) {
                    return _.throttle(fn, wait);
                };
            }
        }
    }();
    (function(root) {
        "use strict";
        var old, keys;
        old = root.Bloodhound;
        keys = {
            data: "data",
            protocol: "protocol",
            thumbprint: "thumbprint"
        };
        root.Bloodhound = Bloodhound;
        function Bloodhound(o) {
            if (!o || !o.local && !o.prefetch && !o.remote) {
                $.error("one of local, prefetch, or remote is required");
            }
            this.limit = o.limit || 5;
            this.sorter = getSorter(o.sorter);
            this.dupDetector = o.dupDetector || ignoreDuplicates;
            this.local = oParser.local(o);
            this.prefetch = oParser.prefetch(o);
            this.remote = oParser.remote(o);
            this.cacheKey = this.prefetch ? this.prefetch.cacheKey || this.prefetch.url : null;
            this.index = new SearchIndex({
                datumTokenizer: o.datumTokenizer,
                queryTokenizer: o.queryTokenizer
            });
            this.storage = this.cacheKey ? new PersistentStorage(this.cacheKey) : null;
        }
        Bloodhound.noConflict = function noConflict() {
            root.Bloodhound = old;
            return Bloodhound;
        };
        Bloodhound.tokenizers = tokenizers;
        _.mixin(Bloodhound.prototype, {
            _loadPrefetch: function loadPrefetch(o) {
                var that = this, serialized, deferred;
                if (serialized = this._readFromStorage(o.thumbprint)) {
                    this.index.bootstrap(serialized);
                    deferred = $.Deferred().resolve();
                } else {
                    deferred = $.ajax(o.url, o.ajax).done(handlePrefetchResponse);
                }
                return deferred;
                function handlePrefetchResponse(resp) {
                    that.clear();
                    that.add(o.filter ? o.filter(resp) : resp);
                    that._saveToStorage(that.index.serialize(), o.thumbprint, o.ttl);
                }
            },
            _getFromRemote: function getFromRemote(query, cb) {
                var that = this, url, uriEncodedQuery;
                if (!this.transport) {
                    return;
                }
                query = query || "";
                uriEncodedQuery = encodeURIComponent(query);
                url = this.remote.replace ? this.remote.replace(this.remote.url, query) : this.remote.url.replace(this.remote.wildcard, uriEncodedQuery);
                return this.transport.get(url, this.remote.ajax, handleRemoteResponse);
                function handleRemoteResponse(err, resp) {
                    err ? cb([]) : cb(that.remote.filter ? that.remote.filter(resp) : resp);
                }
            },
            _cancelLastRemoteRequest: function cancelLastRemoteRequest() {
                this.transport && this.transport.cancel();
            },
            _saveToStorage: function saveToStorage(data, thumbprint, ttl) {
                if (this.storage) {
                    this.storage.set(keys.data, data, ttl);
                    this.storage.set(keys.protocol, location.protocol, ttl);
                    this.storage.set(keys.thumbprint, thumbprint, ttl);
                }
            },
            _readFromStorage: function readFromStorage(thumbprint) {
                var stored = {}, isExpired;
                if (this.storage) {
                    stored.data = this.storage.get(keys.data);
                    stored.protocol = this.storage.get(keys.protocol);
                    stored.thumbprint = this.storage.get(keys.thumbprint);
                }
                isExpired = stored.thumbprint !== thumbprint || stored.protocol !== location.protocol;
                return stored.data && !isExpired ? stored.data : null;
            },
            _initialize: function initialize() {
                var that = this, local = this.local, deferred;
                deferred = this.prefetch ? this._loadPrefetch(this.prefetch) : $.Deferred().resolve();
                local && deferred.done(addLocalToIndex);
                this.transport = this.remote ? new Transport(this.remote) : null;
                return this.initPromise = deferred.promise();
                function addLocalToIndex() {
                    that.add(_.isFunction(local) ? local() : local);
                }
            },
            initialize: function initialize(force) {
                return !this.initPromise || force ? this._initialize() : this.initPromise;
            },
            add: function add(data) {
                this.index.add(data);
            },
            get: function get(query, cb) {
                var that = this, matches = [], cacheHit = false;
                matches = this.index.get(query);
                matches = this.sorter(matches).slice(0, this.limit);
                matches.length < this.limit ? cacheHit = this._getFromRemote(query, returnRemoteMatches) : this._cancelLastRemoteRequest();
                if (!cacheHit) {
                    (matches.length > 0 || !this.transport) && cb && cb(matches);
                }
                function returnRemoteMatches(remoteMatches) {
                    var matchesWithBackfill = matches.slice(0);
                    _.each(remoteMatches, function(remoteMatch) {
                        var isDuplicate;
                        isDuplicate = _.some(matchesWithBackfill, function(match) {
                            return that.dupDetector(remoteMatch, match);
                        });
                        !isDuplicate && matchesWithBackfill.push(remoteMatch);
                        return matchesWithBackfill.length < that.limit;
                    });
                    cb && cb(that.sorter(matchesWithBackfill));
                }
            },
            clear: function clear() {
                this.index.reset();
            },
            clearPrefetchCache: function clearPrefetchCache() {
                this.storage && this.storage.clear();
            },
            clearRemoteCache: function clearRemoteCache() {
                this.transport && Transport.resetCache();
            },
            ttAdapter: function ttAdapter() {
                return _.bind(this.get, this);
            }
        });
        return Bloodhound;
        function getSorter(sortFn) {
            return _.isFunction(sortFn) ? sort : noSort;
            function sort(array) {
                return array.sort(sortFn);
            }
            function noSort(array) {
                return array;
            }
        }
        function ignoreDuplicates() {
            return false;
        }
    })(this);
    var html = function() {
        return {
            wrapper: '<span class="twitter-typeahead"></span>',
            dropdown: '<span class="tt-dropdown-menu"></span>',
            dataset: '<div class="tt-dataset-%CLASS%"></div>',
            suggestions: '<span class="tt-suggestions"></span>',
            suggestion: '<div class="tt-suggestion"></div>'
        };
    }();
    var css = function() {
        "use strict";
        var css = {
            wrapper: {
                position: "relative",
                display: "inline-block"
            },
            hint: {
                position: "absolute",
                top: "0",
                left: "0",
                borderColor: "transparent",
                boxShadow: "none",
                opacity: "1"
            },
            input: {
                position: "relative",
                verticalAlign: "top",
                backgroundColor: "transparent"
            },
            inputWithNoHint: {
                position: "relative",
                verticalAlign: "top"
            },
            dropdown: {
                position: "absolute",
                top: "100%",
                left: "0",
                zIndex: "100",
                display: "none"
            },
            suggestions: {
                display: "block"
            },
            suggestion: {
                whiteSpace: "nowrap",
                cursor: "pointer"
            },
            suggestionChild: {
                whiteSpace: "normal"
            },
            ltr: {
                left: "0",
                right: "auto"
            },
            rtl: {
                left: "auto",
                right: " 0"
            }
        };
        if (_.isMsie()) {
            _.mixin(css.input, {
                backgroundImage: "url(data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7)"
            });
        }
        if (_.isMsie() && _.isMsie() <= 7) {
            _.mixin(css.input, {
                marginTop: "-1px"
            });
        }
        return css;
    }();
    var EventBus = function() {
        "use strict";
        var namespace = "typeahead:";
        function EventBus(o) {
            if (!o || !o.el) {
                $.error("EventBus initialized without el");
            }
            this.$el = $(o.el);
        }
        _.mixin(EventBus.prototype, {
            trigger: function(type) {
                var args = [].slice.call(arguments, 1);
                this.$el.trigger(namespace + type, args);
            }
        });
        return EventBus;
    }();
    var EventEmitter = function() {
        "use strict";
        var splitter = /\s+/, nextTick = getNextTick();
        return {
            onSync: onSync,
            onAsync: onAsync,
            off: off,
            trigger: trigger
        };
        function on(method, types, cb, context) {
            var type;
            if (!cb) {
                return this;
            }
            types = types.split(splitter);
            cb = context ? bindContext(cb, context) : cb;
            this._callbacks = this._callbacks || {};
            while (type = types.shift()) {
                this._callbacks[type] = this._callbacks[type] || {
                    sync: [],
                    async: []
                };
                this._callbacks[type][method].push(cb);
            }
            return this;
        }
        function onAsync(types, cb, context) {
            return on.call(this, "async", types, cb, context);
        }
        function onSync(types, cb, context) {
            return on.call(this, "sync", types, cb, context);
        }
        function off(types) {
            var type;
            if (!this._callbacks) {
                return this;
            }
            types = types.split(splitter);
            while (type = types.shift()) {
                delete this._callbacks[type];
            }
            return this;
        }
        function trigger(types) {
            var type, callbacks, args, syncFlush, asyncFlush;
            if (!this._callbacks) {
                return this;
            }
            types = types.split(splitter);
            args = [].slice.call(arguments, 1);
            while ((type = types.shift()) && (callbacks = this._callbacks[type])) {
                syncFlush = getFlush(callbacks.sync, this, [ type ].concat(args));
                asyncFlush = getFlush(callbacks.async, this, [ type ].concat(args));
                syncFlush() && nextTick(asyncFlush);
            }
            return this;
        }
        function getFlush(callbacks, context, args) {
            return flush;
            function flush() {
                var cancelled;
                for (var i = 0, len = callbacks.length; !cancelled && i < len; i += 1) {
                    cancelled = callbacks[i].apply(context, args) === false;
                }
                return !cancelled;
            }
        }
        function getNextTick() {
            var nextTickFn;
            if (window.setImmediate) {
                nextTickFn = function nextTickSetImmediate(fn) {
                    setImmediate(function() {
                        fn();
                    });
                };
            } else {
                nextTickFn = function nextTickSetTimeout(fn) {
                    setTimeout(function() {
                        fn();
                    }, 0);
                };
            }
            return nextTickFn;
        }
        function bindContext(fn, context) {
            return fn.bind ? fn.bind(context) : function() {
                fn.apply(context, [].slice.call(arguments, 0));
            };
        }
    }();
    var highlight = function(doc) {
        "use strict";
        var defaults = {
            node: null,
            pattern: null,
            tagName: "strong",
            className: null,
            wordsOnly: false,
            caseSensitive: false
        };
        return function hightlight(o) {
            var regex;
            o = _.mixin({}, defaults, o);
            if (!o.node || !o.pattern) {
                return;
            }
            o.pattern = _.isArray(o.pattern) ? o.pattern : [ o.pattern ];
            regex = getRegex(o.pattern, o.caseSensitive, o.wordsOnly);
            traverse(o.node, hightlightTextNode);
            function hightlightTextNode(textNode) {
                var match, patternNode, wrapperNode;
                if (match = regex.exec(textNode.data)) {
                    wrapperNode = doc.createElement(o.tagName);
                    o.className && (wrapperNode.className = o.className);
                    patternNode = textNode.splitText(match.index);
                    patternNode.splitText(match[0].length);
                    wrapperNode.appendChild(patternNode.cloneNode(true));
                    textNode.parentNode.replaceChild(wrapperNode, patternNode);
                }
                return !!match;
            }
            function traverse(el, hightlightTextNode) {
                var childNode, TEXT_NODE_TYPE = 3;
                for (var i = 0; i < el.childNodes.length; i++) {
                    childNode = el.childNodes[i];
                    if (childNode.nodeType === TEXT_NODE_TYPE) {
                        i += hightlightTextNode(childNode) ? 1 : 0;
                    } else {
                        traverse(childNode, hightlightTextNode);
                    }
                }
            }
        };
        function getRegex(patterns, caseSensitive, wordsOnly) {
            var escapedPatterns = [], regexStr;
            for (var i = 0, len = patterns.length; i < len; i++) {
                escapedPatterns.push(_.escapeRegExChars(patterns[i]));
            }
            regexStr = wordsOnly ? "\\b(" + escapedPatterns.join("|") + ")\\b" : "(" + escapedPatterns.join("|") + ")";
            return caseSensitive ? new RegExp(regexStr) : new RegExp(regexStr, "i");
        }
    }(window.document);
    var Input = function() {
        "use strict";
        var specialKeyCodeMap;
        specialKeyCodeMap = {
            9: "tab",
            27: "esc",
            37: "left",
            39: "right",
            13: "enter",
            38: "up",
            40: "down"
        };
        function Input(o) {
            var that = this, onBlur, onFocus, onKeydown, onInput;
            o = o || {};
            if (!o.input) {
                $.error("input is missing");
            }
            onBlur = _.bind(this._onBlur, this);
            onFocus = _.bind(this._onFocus, this);
            onKeydown = _.bind(this._onKeydown, this);
            onInput = _.bind(this._onInput, this);
            this.$hint = $(o.hint);
            this.$input = $(o.input).on("blur.tt", onBlur).on("focus.tt", onFocus).on("keydown.tt", onKeydown);
            if (this.$hint.length === 0) {
                this.setHint = this.getHint = this.clearHint = this.clearHintIfInvalid = _.noop;
            }
            if (!_.isMsie()) {
                this.$input.on("input.tt", onInput);
            } else {
                this.$input.on("keydown.tt keypress.tt cut.tt paste.tt", function($e) {
                    if (specialKeyCodeMap[$e.which || $e.keyCode]) {
                        return;
                    }
                    _.defer(_.bind(that._onInput, that, $e));
                });
            }
            this.query = this.$input.val();
            this.$overflowHelper = buildOverflowHelper(this.$input);
        }
        Input.normalizeQuery = function(str) {
            return (str || "").replace(/^\s*/g, "").replace(/\s{2,}/g, " ");
        };
        _.mixin(Input.prototype, EventEmitter, {
            _onBlur: function onBlur() {
                this.resetInputValue();
                this.trigger("blurred");
            },
            _onFocus: function onFocus() {
                this.trigger("focused");
            },
            _onKeydown: function onKeydown($e) {
                var keyName = specialKeyCodeMap[$e.which || $e.keyCode];
                this._managePreventDefault(keyName, $e);
                if (keyName && this._shouldTrigger(keyName, $e)) {
                    this.trigger(keyName + "Keyed", $e);
                }
            },
            _onInput: function onInput() {
                this._checkInputValue();
            },
            _managePreventDefault: function managePreventDefault(keyName, $e) {
                var preventDefault, hintValue, inputValue;
                switch (keyName) {
                  case "tab":
                    hintValue = this.getHint();
                    inputValue = this.getInputValue();
                    preventDefault = hintValue && hintValue !== inputValue && !withModifier($e);
                    break;

                  case "up":
                  case "down":
                    preventDefault = !withModifier($e);
                    break;

                  default:
                    preventDefault = false;
                }
                preventDefault && $e.preventDefault();
            },
            _shouldTrigger: function shouldTrigger(keyName, $e) {
                var trigger;
                switch (keyName) {
                  case "tab":
                    trigger = !withModifier($e);
                    break;

                  default:
                    trigger = true;
                }
                return trigger;
            },
            _checkInputValue: function checkInputValue() {
                var inputValue, areEquivalent, hasDifferentWhitespace;
                inputValue = this.getInputValue();
                areEquivalent = areQueriesEquivalent(inputValue, this.query);
                hasDifferentWhitespace = areEquivalent ? this.query.length !== inputValue.length : false;
                this.query = inputValue;
                if (!areEquivalent) {
                    this.trigger("queryChanged", this.query);
                } else if (hasDifferentWhitespace) {
                    this.trigger("whitespaceChanged", this.query);
                }
            },
            focus: function focus() {
                this.$input.focus();
            },
            blur: function blur() {
                this.$input.blur();
            },
            getQuery: function getQuery() {
                return this.query;
            },
            setQuery: function setQuery(query) {
                this.query = query;
            },
            getInputValue: function getInputValue() {
                return this.$input.val();
            },
            setInputValue: function setInputValue(value, silent) {
                this.$input.val(value);
                silent ? this.clearHint() : this._checkInputValue();
            },
            resetInputValue: function resetInputValue() {
                this.setInputValue(this.query, true);
            },
            getHint: function getHint() {
                return this.$hint.val();
            },
            setHint: function setHint(value) {
                this.$hint.val(value);
            },
            clearHint: function clearHint() {
                this.setHint("");
            },
            clearHintIfInvalid: function clearHintIfInvalid() {
                var val, hint, valIsPrefixOfHint, isValid;
                val = this.getInputValue();
                hint = this.getHint();
                valIsPrefixOfHint = val !== hint && hint.indexOf(val) === 0;
                isValid = val !== "" && valIsPrefixOfHint && !this.hasOverflow();
                !isValid && this.clearHint();
            },
            getLanguageDirection: function getLanguageDirection() {
                return (this.$input.css("direction") || "ltr").toLowerCase();
            },
            hasOverflow: function hasOverflow() {
                var constraint = this.$input.width() - 2;
                this.$overflowHelper.text(this.getInputValue());
                return this.$overflowHelper.width() >= constraint;
            },
            isCursorAtEnd: function() {
                var valueLength, selectionStart, range;
                valueLength = this.$input.val().length;
                selectionStart = this.$input[0].selectionStart;
                if (_.isNumber(selectionStart)) {
                    return selectionStart === valueLength;
                } else if (document.selection) {
                    range = document.selection.createRange();
                    range.moveStart("character", -valueLength);
                    return valueLength === range.text.length;
                }
                return true;
            },
            destroy: function destroy() {
                this.$hint.off(".tt");
                this.$input.off(".tt");
                this.$hint = this.$input = this.$overflowHelper = null;
            }
        });
        return Input;
        function buildOverflowHelper($input) {
            return $('<pre aria-hidden="true"></pre>').css({
                position: "absolute",
                visibility: "hidden",
                whiteSpace: "pre",
                fontFamily: $input.css("font-family"),
                fontSize: $input.css("font-size"),
                fontStyle: $input.css("font-style"),
                fontVariant: $input.css("font-variant"),
                fontWeight: $input.css("font-weight"),
                wordSpacing: $input.css("word-spacing"),
                letterSpacing: $input.css("letter-spacing"),
                textIndent: $input.css("text-indent"),
                textRendering: $input.css("text-rendering"),
                textTransform: $input.css("text-transform")
            }).insertAfter($input);
        }
        function areQueriesEquivalent(a, b) {
            return Input.normalizeQuery(a) === Input.normalizeQuery(b);
        }
        function withModifier($e) {
            return $e.altKey || $e.ctrlKey || $e.metaKey || $e.shiftKey;
        }
    }();
    var Dataset = function() {
        "use strict";
        var datasetKey = "ttDataset", valueKey = "ttValue", datumKey = "ttDatum";
        function Dataset(o) {
            o = o || {};
            o.templates = o.templates || {};
            if (!o.source) {
                $.error("missing source");
            }
            if (o.name && !isValidName(o.name)) {
                $.error("invalid dataset name: " + o.name);
            }
            this.query = null;
            this.highlight = !!o.highlight;
            this.name = o.name || _.getUniqueId();
            this.source = o.source;
            this.displayFn = getDisplayFn(o.display || o.displayKey);
            this.templates = getTemplates(o.templates, this.displayFn);
            this.$el = $(html.dataset.replace("%CLASS%", this.name));
        }
        Dataset.extractDatasetName = function extractDatasetName(el) {
            return $(el).data(datasetKey);
        };
        Dataset.extractValue = function extractDatum(el) {
            return $(el).data(valueKey);
        };
        Dataset.extractDatum = function extractDatum(el) {
            return $(el).data(datumKey);
        };
        _.mixin(Dataset.prototype, EventEmitter, {
            _render: function render(query, suggestions) {
                if (!this.$el) {
                    return;
                }
                var that = this, hasSuggestions;
                this.$el.empty();
                hasSuggestions = suggestions && suggestions.length;
                if (!hasSuggestions && this.templates.empty) {
                    this.$el.html(getEmptyHtml()).prepend(that.templates.header ? getHeaderHtml() : null).append(that.templates.footer ? getFooterHtml() : null);
                } else if (hasSuggestions) {
                    this.$el.html(getSuggestionsHtml()).prepend(that.templates.header ? getHeaderHtml() : null).append(that.templates.footer ? getFooterHtml() : null);
                }
                this.trigger("rendered");
                function getEmptyHtml() {
                    return that.templates.empty({
                        query: query,
                        isEmpty: true
                    });
                }
                function getSuggestionsHtml() {
                    var $suggestions, nodes;
                    $suggestions = $(html.suggestions).css(css.suggestions);
                    nodes = _.map(suggestions, getSuggestionNode);
                    $suggestions.append.apply($suggestions, nodes);
                    that.highlight && highlight({
                        className: "tt-highlight",
                        node: $suggestions[0],
                        pattern: query
                    });
                    return $suggestions;
                    function getSuggestionNode(suggestion) {
                        var $el;
                        $el = $(html.suggestion).append(that.templates.suggestion(suggestion)).data(datasetKey, that.name).data(valueKey, that.displayFn(suggestion)).data(datumKey, suggestion);
                        $el.children().each(function() {
                            $(this).css(css.suggestionChild);
                        });
                        return $el;
                    }
                }
                function getHeaderHtml() {
                    return that.templates.header({
                        query: query,
                        isEmpty: !hasSuggestions
                    });
                }
                function getFooterHtml() {
                    return that.templates.footer({
                        query: query,
                        isEmpty: !hasSuggestions
                    });
                }
            },
            getRoot: function getRoot() {
                return this.$el;
            },
            update: function update(query) {
                var that = this;
                this.query = query;
                this.canceled = false;
                this.source(query, render);
                function render(suggestions) {
                    if (!that.canceled && query === that.query) {
                        that._render(query, suggestions);
                    }
                }
            },
            cancel: function cancel() {
                this.canceled = true;
            },
            clear: function clear() {
                this.cancel();
                this.$el.empty();
                this.trigger("rendered");
            },
            isEmpty: function isEmpty() {
                return this.$el.is(":empty");
            },
            destroy: function destroy() {
                this.$el = null;
            }
        });
        return Dataset;
        function getDisplayFn(display) {
            display = display || "value";
            return _.isFunction(display) ? display : displayFn;
            function displayFn(obj) {
                return obj[display];
            }
        }
        function getTemplates(templates, displayFn) {
            return {
                empty: templates.empty && _.templatify(templates.empty),
                header: templates.header && _.templatify(templates.header),
                footer: templates.footer && _.templatify(templates.footer),
                suggestion: templates.suggestion || suggestionTemplate
            };
            function suggestionTemplate(context) {
                return "<p>" + displayFn(context) + "</p>";
            }
        }
        function isValidName(str) {
            return /^[_a-zA-Z0-9-]+$/.test(str);
        }
    }();
    var Dropdown = function() {
        "use strict";
        function Dropdown(o) {
            var that = this, onSuggestionClick, onSuggestionMouseEnter, onSuggestionMouseLeave;
            o = o || {};
            if (!o.menu) {
                $.error("menu is required");
            }
            this.isOpen = false;
            this.isEmpty = true;
            this.datasets = _.map(o.datasets, initializeDataset);
            onSuggestionClick = _.bind(this._onSuggestionClick, this);
            onSuggestionMouseEnter = _.bind(this._onSuggestionMouseEnter, this);
            onSuggestionMouseLeave = _.bind(this._onSuggestionMouseLeave, this);
            this.$menu = $(o.menu).on("click.tt", ".tt-suggestion", onSuggestionClick).on("mouseenter.tt", ".tt-suggestion", onSuggestionMouseEnter).on("mouseleave.tt", ".tt-suggestion", onSuggestionMouseLeave);
            _.each(this.datasets, function(dataset) {
                that.$menu.append(dataset.getRoot());
                dataset.onSync("rendered", that._onRendered, that);
            });
        }
        _.mixin(Dropdown.prototype, EventEmitter, {
            _onSuggestionClick: function onSuggestionClick($e) {
                this.trigger("suggestionClicked", $($e.currentTarget));
            },
            _onSuggestionMouseEnter: function onSuggestionMouseEnter($e) {
                this._removeCursor();
                this._setCursor($($e.currentTarget), true);
            },
            _onSuggestionMouseLeave: function onSuggestionMouseLeave() {
                this._removeCursor();
            },
            _onRendered: function onRendered() {
                this.isEmpty = _.every(this.datasets, isDatasetEmpty);
                this.isEmpty ? this._hide() : this.isOpen && this._show();
                this.trigger("datasetRendered");
                function isDatasetEmpty(dataset) {
                    return dataset.isEmpty();
                }
            },
            _hide: function() {
                this.$menu.hide();
            },
            _show: function() {
                this.$menu.css("display", "block");
            },
            _getSuggestions: function getSuggestions() {
                return this.$menu.find(".tt-suggestion");
            },
            _getCursor: function getCursor() {
                return this.$menu.find(".tt-cursor").first();
            },
            _setCursor: function setCursor($el, silent) {
                $el.first().addClass("tt-cursor");
                !silent && this.trigger("cursorMoved");
            },
            _removeCursor: function removeCursor() {
                this._getCursor().removeClass("tt-cursor");
            },
            _moveCursor: function moveCursor(increment) {
                var $suggestions, $oldCursor, newCursorIndex, $newCursor;
                if (!this.isOpen) {
                    return;
                }
                $oldCursor = this._getCursor();
                $suggestions = this._getSuggestions();
                this._removeCursor();
                newCursorIndex = $suggestions.index($oldCursor) + increment;
                newCursorIndex = (newCursorIndex + 1) % ($suggestions.length + 1) - 1;
                if (newCursorIndex === -1) {
                    this.trigger("cursorRemoved");
                    return;
                } else if (newCursorIndex < -1) {
                    newCursorIndex = $suggestions.length - 1;
                }
                this._setCursor($newCursor = $suggestions.eq(newCursorIndex));
                this._ensureVisible($newCursor);
            },
            _ensureVisible: function ensureVisible($el) {
                var elTop, elBottom, menuScrollTop, menuHeight;
                elTop = $el.position().top;
                elBottom = elTop + $el.outerHeight(true);
                menuScrollTop = this.$menu.scrollTop();
                menuHeight = this.$menu.height() + parseInt(this.$menu.css("paddingTop"), 10) + parseInt(this.$menu.css("paddingBottom"), 10);
                if (elTop < 0) {
                    this.$menu.scrollTop(menuScrollTop + elTop);
                } else if (menuHeight < elBottom) {
                    this.$menu.scrollTop(menuScrollTop + (elBottom - menuHeight));
                }
            },
            close: function close() {
                if (this.isOpen) {
                    this.isOpen = false;
                    this._removeCursor();
                    this._hide();
                    this.trigger("closed");
                }
            },
            open: function open() {
                if (!this.isOpen) {
                    this.isOpen = true;
                    !this.isEmpty && this._show();
                    this.trigger("opened");
                }
            },
            setLanguageDirection: function setLanguageDirection(dir) {
                this.$menu.css(dir === "ltr" ? css.ltr : css.rtl);
            },
            moveCursorUp: function moveCursorUp() {
                this._moveCursor(-1);
            },
            moveCursorDown: function moveCursorDown() {
                this._moveCursor(+1);
            },
            getDatumForSuggestion: function getDatumForSuggestion($el) {
                var datum = null;
                if ($el.length) {
                    datum = {
                        raw: Dataset.extractDatum($el),
                        value: Dataset.extractValue($el),
                        datasetName: Dataset.extractDatasetName($el)
                    };
                }
                return datum;
            },
            getDatumForCursor: function getDatumForCursor() {
                return this.getDatumForSuggestion(this._getCursor().first());
            },
            getDatumForTopSuggestion: function getDatumForTopSuggestion() {
                return this.getDatumForSuggestion(this._getSuggestions().first());
            },
            update: function update(query) {
                _.each(this.datasets, updateDataset);
                function updateDataset(dataset) {
                    dataset.update(query);
                }
            },
            empty: function empty() {
                _.each(this.datasets, clearDataset);
                this.isEmpty = true;
                function clearDataset(dataset) {
                    dataset.clear();
                }
            },
            isVisible: function isVisible() {
                return this.isOpen && !this.isEmpty;
            },
            destroy: function destroy() {
                this.$menu.off(".tt");
                this.$menu = null;
                _.each(this.datasets, destroyDataset);
                function destroyDataset(dataset) {
                    dataset.destroy();
                }
            }
        });
        return Dropdown;
        function initializeDataset(oDataset) {
            return new Dataset(oDataset);
        }
    }();
    var Typeahead = function() {
        "use strict";
        var attrsKey = "ttAttrs";
        function Typeahead(o) {
            var $menu, $input, $hint;
            o = o || {};
            if (!o.input) {
                $.error("missing input");
            }
            this.isActivated = false;
            this.autoselect = !!o.autoselect;
            this.minLength = _.isNumber(o.minLength) ? o.minLength : 1;
            this.$node = buildDom(o.input, o.withHint);
            $menu = this.$node.find(".tt-dropdown-menu");
            $input = this.$node.find(".tt-input");
            $hint = this.$node.find(".tt-hint");
            $input.on("blur.tt", function($e) {
                var active, isActive, hasActive;
                active = document.activeElement;
                isActive = $menu.is(active);
                hasActive = $menu.has(active).length > 0;
                if (_.isMsie() && (isActive || hasActive)) {
                    $e.preventDefault();
                    $e.stopImmediatePropagation();
                    _.defer(function() {
                        $input.focus();
                    });
                }
            });
            $menu.on("mousedown.tt", function($e) {
                $e.preventDefault();
            });
            this.eventBus = o.eventBus || new EventBus({
                el: $input
            });
            this.dropdown = new Dropdown({
                menu: $menu,
                datasets: o.datasets
            }).onSync("suggestionClicked", this._onSuggestionClicked, this).onSync("cursorMoved", this._onCursorMoved, this).onSync("cursorRemoved", this._onCursorRemoved, this).onSync("opened", this._onOpened, this).onSync("closed", this._onClosed, this).onAsync("datasetRendered", this._onDatasetRendered, this);
            this.input = new Input({
                input: $input,
                hint: $hint
            }).onSync("focused", this._onFocused, this).onSync("blurred", this._onBlurred, this).onSync("enterKeyed", this._onEnterKeyed, this).onSync("tabKeyed", this._onTabKeyed, this).onSync("escKeyed", this._onEscKeyed, this).onSync("upKeyed", this._onUpKeyed, this).onSync("downKeyed", this._onDownKeyed, this).onSync("leftKeyed", this._onLeftKeyed, this).onSync("rightKeyed", this._onRightKeyed, this).onSync("queryChanged", this._onQueryChanged, this).onSync("whitespaceChanged", this._onWhitespaceChanged, this);
            this._setLanguageDirection();
        }
        _.mixin(Typeahead.prototype, {
            _onSuggestionClicked: function onSuggestionClicked(type, $el) {
                var datum;
                if (datum = this.dropdown.getDatumForSuggestion($el)) {
                    this._select(datum);
                }
            },
            _onCursorMoved: function onCursorMoved() {
                var datum = this.dropdown.getDatumForCursor();
                this.input.setInputValue(datum.value, true);
                this.eventBus.trigger("cursorchanged", datum.raw, datum.datasetName);
            },
            _onCursorRemoved: function onCursorRemoved() {
                this.input.resetInputValue();
                this._updateHint();
            },
            _onDatasetRendered: function onDatasetRendered() {
                this._updateHint();
            },
            _onOpened: function onOpened() {
                this._updateHint();
                this.eventBus.trigger("opened");
            },
            _onClosed: function onClosed() {
                this.input.clearHint();
                this.eventBus.trigger("closed");
            },
            _onFocused: function onFocused() {
                this.isActivated = true;
                this.dropdown.open();
            },
            _onBlurred: function onBlurred() {
                this.isActivated = false;
                this.dropdown.empty();
                this.dropdown.close();
            },
            _onEnterKeyed: function onEnterKeyed(type, $e) {
                var cursorDatum, topSuggestionDatum;
                cursorDatum = this.dropdown.getDatumForCursor();
                topSuggestionDatum = this.dropdown.getDatumForTopSuggestion();
                if (cursorDatum) {
                    this._select(cursorDatum);
                    $e.preventDefault();
                } else if (this.autoselect && topSuggestionDatum) {
                    this._select(topSuggestionDatum);
                    $e.preventDefault();
                }
            },
            _onTabKeyed: function onTabKeyed(type, $e) {
                var datum;
                if (datum = this.dropdown.getDatumForCursor()) {
                    this._select(datum);
                    $e.preventDefault();
                } else {
                    this._autocomplete(true);
                }
            },
            _onEscKeyed: function onEscKeyed() {
                this.dropdown.close();
                this.input.resetInputValue();
            },
            _onUpKeyed: function onUpKeyed() {
                var query = this.input.getQuery();
                this.dropdown.isEmpty && query.length >= this.minLength ? this.dropdown.update(query) : this.dropdown.moveCursorUp();
                this.dropdown.open();
            },
            _onDownKeyed: function onDownKeyed() {
                var query = this.input.getQuery();
                this.dropdown.isEmpty && query.length >= this.minLength ? this.dropdown.update(query) : this.dropdown.moveCursorDown();
                this.dropdown.open();
            },
            _onLeftKeyed: function onLeftKeyed() {
                this.dir === "rtl" && this._autocomplete();
            },
            _onRightKeyed: function onRightKeyed() {
                this.dir === "ltr" && this._autocomplete();
            },
            _onQueryChanged: function onQueryChanged(e, query) {
                this.input.clearHintIfInvalid();
                query.length >= this.minLength ? this.dropdown.update(query) : this.dropdown.empty();
                this.dropdown.open();
                this._setLanguageDirection();
            },
            _onWhitespaceChanged: function onWhitespaceChanged() {
                this._updateHint();
                this.dropdown.open();
            },
            _setLanguageDirection: function setLanguageDirection() {
                var dir;
                if (this.dir !== (dir = this.input.getLanguageDirection())) {
                    this.dir = dir;
                    this.$node.css("direction", dir);
                    this.dropdown.setLanguageDirection(dir);
                }
            },
            _updateHint: function updateHint() {
                var datum, val, query, escapedQuery, frontMatchRegEx, match;
                datum = this.dropdown.getDatumForTopSuggestion();
                if (datum && this.dropdown.isVisible() && !this.input.hasOverflow()) {
                    val = this.input.getInputValue();
                    query = Input.normalizeQuery(val);
                    escapedQuery = _.escapeRegExChars(query);
                    frontMatchRegEx = new RegExp("^(?:" + escapedQuery + ")(.+$)", "i");
                    match = frontMatchRegEx.exec(datum.value);
                    match ? this.input.setHint(val + match[1]) : this.input.clearHint();
                } else {
                    this.input.clearHint();
                }
            },
            _autocomplete: function autocomplete(laxCursor) {
                var hint, query, isCursorAtEnd, datum;
                hint = this.input.getHint();
                query = this.input.getQuery();
                isCursorAtEnd = laxCursor || this.input.isCursorAtEnd();
                if (hint && query !== hint && isCursorAtEnd) {
                    datum = this.dropdown.getDatumForTopSuggestion();
                    datum && this.input.setInputValue(datum.value);
                    this.eventBus.trigger("autocompleted", datum.raw, datum.datasetName);
                }
            },
            _select: function select(datum) {
                this.input.setQuery(datum.value);
                this.input.setInputValue(datum.value, true);
                this._setLanguageDirection();
                this.eventBus.trigger("selected", datum.raw, datum.datasetName);
                this.dropdown.close();
                _.defer(_.bind(this.dropdown.empty, this.dropdown));
            },
            open: function open() {
                this.dropdown.open();
            },
            close: function close() {
                this.dropdown.close();
            },
            setVal: function setVal(val) {
                val = _.toStr(val);
                if (this.isActivated) {
                    this.input.setInputValue(val);
                } else {
                    this.input.setQuery(val);
                    this.input.setInputValue(val, true);
                }
                this._setLanguageDirection();
            },
            getVal: function getVal() {
                return this.input.getQuery();
            },
            destroy: function destroy() {
                this.input.destroy();
                this.dropdown.destroy();
                destroyDomStructure(this.$node);
                this.$node = null;
            }
        });
        return Typeahead;
        function buildDom(input, withHint) {
            var $input, $wrapper, $dropdown, $hint;
            $input = $(input);
            $wrapper = $(html.wrapper).css(css.wrapper);
            $dropdown = $(html.dropdown).css(css.dropdown);
            $hint = $input.clone().css(css.hint).css(getBackgroundStyles($input));
            $hint.val("").removeData().addClass("tt-hint").removeAttr("id name placeholder required").prop("readonly", true).attr({
                autocomplete: "off",
                spellcheck: "false",
                tabindex: -1
            });
            $input.data(attrsKey, {
                dir: $input.attr("dir"),
                autocomplete: $input.attr("autocomplete"),
                spellcheck: $input.attr("spellcheck"),
                style: $input.attr("style")
            });
            $input.addClass("tt-input").attr({
                autocomplete: "off",
                spellcheck: false
            }).css(withHint ? css.input : css.inputWithNoHint);
            try {
                !$input.attr("dir") && $input.attr("dir", "auto");
            } catch (e) {}
            return $input.wrap($wrapper).parent().prepend(withHint ? $hint : null).append($dropdown);
        }
        function getBackgroundStyles($el) {
            return {
                backgroundAttachment: $el.css("background-attachment"),
                backgroundClip: $el.css("background-clip"),
                backgroundColor: $el.css("background-color"),
                backgroundImage: $el.css("background-image"),
                backgroundOrigin: $el.css("background-origin"),
                backgroundPosition: $el.css("background-position"),
                backgroundRepeat: $el.css("background-repeat"),
                backgroundSize: $el.css("background-size")
            };
        }
        function destroyDomStructure($node) {
            var $input = $node.find(".tt-input");
            _.each($input.data(attrsKey), function(val, key) {
                _.isUndefined(val) ? $input.removeAttr(key) : $input.attr(key, val);
            });
            $input.detach().removeData(attrsKey).removeClass("tt-input").insertAfter($node);
            $node.remove();
        }
    }();
    (function() {
        "use strict";
        var old, typeaheadKey, methods;
        old = $.fn.typeahead;
        typeaheadKey = "ttTypeahead";
        methods = {
            initialize: function initialize(o, datasets) {
                datasets = _.isArray(datasets) ? datasets : [].slice.call(arguments, 1);
                o = o || {};
                return this.each(attach);
                function attach() {
                    var $input = $(this), eventBus, typeahead;
                    _.each(datasets, function(d) {
                        d.highlight = !!o.highlight;
                    });
                    typeahead = new Typeahead({
                        input: $input,
                        eventBus: eventBus = new EventBus({
                            el: $input
                        }),
                        withHint: _.isUndefined(o.hint) ? true : !!o.hint,
                        minLength: o.minLength,
                        autoselect: o.autoselect,
                        datasets: datasets
                    });
                    $input.data(typeaheadKey, typeahead);
                }
            },
            open: function open() {
                return this.each(openTypeahead);
                function openTypeahead() {
                    var $input = $(this), typeahead;
                    if (typeahead = $input.data(typeaheadKey)) {
                        typeahead.open();
                    }
                }
            },
            close: function close() {
                return this.each(closeTypeahead);
                function closeTypeahead() {
                    var $input = $(this), typeahead;
                    if (typeahead = $input.data(typeaheadKey)) {
                        typeahead.close();
                    }
                }
            },
            val: function val(newVal) {
                return !arguments.length ? getVal(this.first()) : this.each(setVal);
                function setVal() {
                    var $input = $(this), typeahead;
                    if (typeahead = $input.data(typeaheadKey)) {
                        typeahead.setVal(newVal);
                    }
                }
                function getVal($input) {
                    var typeahead, query;
                    if (typeahead = $input.data(typeaheadKey)) {
                        query = typeahead.getVal();
                    }
                    return query;
                }
            },
            destroy: function destroy() {
                return this.each(unattach);
                function unattach() {
                    var $input = $(this), typeahead;
                    if (typeahead = $input.data(typeaheadKey)) {
                        typeahead.destroy();
                        $input.removeData(typeaheadKey);
                    }
                }
            }
        };
        $.fn.typeahead = function(method) {
            var tts;
            if (methods[method] && method !== "initialize") {
                tts = this.filter(function() {
                    return !!$(this).data(typeaheadKey);
                });
                return methods[method].apply(tts, [].slice.call(arguments, 1));
            } else {
                return methods.initialize.apply(this, arguments);
            }
        };
        $.fn.typeahead.noConflict = function noConflict() {
            $.fn.typeahead = old;
            return this;
        };
    })();
})(window.jQuery);

/*** EXPORTS FROM exports-loader ***/
module.exports = Bloodhound
/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(173).setImmediate))

/***/ },

/***/ 189:
/***/ function(module, exports, __webpack_require__) {

__webpack_require__(190);
var m = __webpack_require__(158);

module.exports = {
    view: function(data, repr, opts) {
        if(data[0].label){
            data.sort(function(a, b) {
                return a.label.localeCompare(b.label);
            });
        }
        return [
            m('div', {
                className: 'legend-grid'
            }, data.map(function(item) {
                return m('span', {
                    className: 'legend-grid-item'
                }, repr(item));
            })),
            m('span', {className: 'pull-left'}, opts.footer || '')
        ];
    }
};


/***/ },

/***/ 190:
/***/ function(module, exports, __webpack_require__) {

// style-loader: Adds some css to the DOM by adding a <style> tag

// load the styles
var content = __webpack_require__(191);
if(typeof content === 'string') content = [[module.id, content, '']];
// add the styles to the DOM
var update = __webpack_require__(19)(content, {});
// Hot Module Replacement
if(false) {
	// When the styles change, update the <style> tags
	module.hot.accept("!!/Users/laurenbarker/GitHub/osf.io/node_modules/css-loader/index.js!/Users/laurenbarker/GitHub/osf.io/website/static/css/legend.css", function() {
		var newContent = require("!!/Users/laurenbarker/GitHub/osf.io/node_modules/css-loader/index.js!/Users/laurenbarker/GitHub/osf.io/website/static/css/legend.css");
		if(typeof newContent === 'string') newContent = [[module.id, newContent, '']];
		update(newContent);
	});
	// When the module is disposed, remove the <style> tags
	module.hot.dispose(function() { update(); });
}

/***/ },

/***/ 191:
/***/ function(module, exports, __webpack_require__) {

exports = module.exports = __webpack_require__(16)();
exports.push([module.id, ".legend-grid {\n    -webkit-column-count: 2; /* Chrome, Safari, Opera */\n    -moz-column-count: 2; /* Firefox */\n    column-count: 2;\n    margin-bottom: 5px;\n}\n\n.legend-grid-item {\n    width: 100%;\n    padding-left: 5px;\n    padding-right: 3px;\n    margin-bottom: 8px;\n    line-break: strict;\n    display: inline-block;\n}\n\n", ""]);

/***/ }

});
//# sourceMappingURL=dashboard-page.js.map