webpackJsonp([36],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

'use strict';
var $ = __webpack_require__(38);

var pointers = __webpack_require__(389);
var AccountClaimer = __webpack_require__(390);
var $osf = __webpack_require__(47);

// NodeActions is needed for rendering recent logs in nodelists (e.g. regsitrations and forks
// pages
__webpack_require__(383);

__webpack_require__(391);
var node = window.contextVars.node;


new pointers.PointerDisplay('#showLinks');

if (!window.contextVars.currentUser.isContributor) {
    new AccountClaimer('.contributor-unregistered');
}

if (node.isPublic && node.piwikSiteID) {
    $osf.trackPiwik(node.piwikHost, node.piwikSiteID);
}

// Used for clearing backward/forward cache issues
$(window).unload(function(){
    return 'Unload';
});
$(document).ready(function() {
    $.getJSON(node.urls.api, function(data) {    
        $('body').trigger('nodeLoad', data);
    });

    var self = this;
    var THRESHOLD_SCROLL_POSITION  = 50;
    var SMALL_SCREEN_SIZE = 767;
    var NON_NAV_TOP_MARGIN = 50;
    var NAV_MAX_TOP_MARGIN = 95;
    self.adjustPanelPosition = function() {
        var bodyWidth = $(document.body).width();
        var scrollTopPosition = $(window).scrollTop();
        if (bodyWidth <= SMALL_SCREEN_SIZE) {
            if (scrollTopPosition >= THRESHOLD_SCROLL_POSITION) {
                $('.cp-handle').css('margin-top', NON_NAV_TOP_MARGIN);
            }
            else {
                $('.cp-handle').css('margin-top', NAV_MAX_TOP_MARGIN - scrollTopPosition);
            }
        } else {
            $('.cp-handle').css('margin-top', NAV_MAX_TOP_MARGIN);
        }
    };
    var ADJUST_PANEL_DEBOUNCE = 10;
    var RESIZE_DEBOUNCE  = 50;

    self.adjustPanelPosition(); /* Init when refreshing the page*/
    $(window).scroll($osf.debounce(self.adjustPanelPosition, ADJUST_PANEL_DEBOUNCE));
    $(window).resize($osf.debounce(self.adjustPanelPosition, RESIZE_DEBOUNCE));
});


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

/***/ 383:
/***/ function(module, exports, __webpack_require__) {

/////////////////////
// Project JS      //
/////////////////////
'use strict';

var $ = __webpack_require__(38);
var bootbox = __webpack_require__(138);
var Raven = __webpack_require__(52);

var $osf = __webpack_require__(47);
var LogFeed = __webpack_require__(179);

var ctx = window.contextVars;
var NodeActions = {}; // Namespace for NodeActions

// TODO: move me to the NodeControl or separate module
NodeActions.beforeForkNode = function(url, done) {
    $.ajax({
        url: url,
        contentType: 'application/json'
    }).done(function(response) {
        bootbox.confirm({
            message: $osf.joinPrompts(response.prompts, ('<h4>Are you sure you want to fork this project?</h4>')),
            callback: function (result) {
                if (result) {
                    done && done();
                }
            },
            buttons:{
                confirm:{
                    label:'Fork'
                }
            }
        });
    }).fail(
        $osf.handleJSONError
    );
};

NodeActions.forkNode = function() {
    NodeActions.beforeForkNode(ctx.node.urls.api + 'fork/before/', function() {
        // Block page
        $osf.block();
        // Fork node
        $osf.postJSON(
            ctx.node.urls.api + 'fork/',
            {}
        ).done(function(response) {
            window.location = response;
        }).fail(function(response) {
            $osf.unblock();
            if (response.status === 403) {
                $osf.growl('Sorry:', 'you do not have permission to fork this project');
            } else {
                $osf.growl('Error:', 'Forking failed');
                Raven.captureMessage('Error occurred during forking');
            }
        });
    });
};

NodeActions.forkPointer = function(pointerId) {
    bootbox.confirm({
        title: 'Fork this project?',
        message: 'Are you sure you want to fork this project?',
        callback: function(result) {
            if(result) {
                // Block page
                $osf.block();

                // Fork pointer
                $osf.postJSON(
                    ctx.node.urls.api + 'pointer/fork/',
                    {pointerId: pointerId}
                ).done(function() {
                    window.location.reload();
                }).fail(function() {
                    $osf.unblock();
                    $osf.growl('Error','Could not fork link.');
                });
            }
        },
        buttons:{
            confirm:{
                label:'Fork'
            }
        }
    });
};

NodeActions.beforeTemplate = function(url, done) {
    $.ajax({
        url: url,
        contentType: 'application/json'
    }).success(function(response) {
        bootbox.confirm({
            message: $osf.joinPrompts(response.prompts,
                ('<h4>Are you sure you want to create a new project using this project as a template?</h4>' +
                '<p>Any add-ons configured for this project will not be authenticated in the new project.</p>')),
                //('Are you sure you want to create a new project using this project as a template? ' +
                //  'Any add-ons configured for this project will not be authenticated in the new project.')),
            callback: function (result) {
                if (result) {
                    done && done();
                }
            },
            buttons:{
                confirm:{
                    label:'Create'
                }
            }
        });
    });
};

NodeActions.addonFileRedirect = function(item) {
    window.location.href = item.params.urls.view;
    return false;
};

NodeActions.useAsTemplate = function() {
    NodeActions.beforeTemplate('/project/new/' + ctx.node.id + '/beforeTemplate/', function () {
        $osf.block();

        $osf.postJSON(
            '/api/v1/project/new/' + ctx.node.id + '/',
            {}
        ).done(function(response) {
            window.location = response.url;
        }).fail(function(response) {
            $osf.unblock();
            $osf.handleJSONError(response);
        });
    });
};


$(function() {

    $('#newComponent form').on('submit', function(e) {

        $('#add-component-submit')
            .attr('disabled', 'disabled')
            .text('Adding');

        if ($.trim($('#title').val()) === '') {

            $('#newComponent .modal-alert').text('This field is required.');

            $('#add-component-submit')
                .removeAttr('disabled', 'disabled')
                .text('Add');

            e.preventDefault();
        } else if ($(e.target).find('#title').val().length > 200) {
            $('#newComponent .modal-alert').text('The new component title cannot be more than 200 characters.'); //This alert never appears...

            $('#add-component-submit')
                .removeAttr('disabled', 'disabled')
                .text('Add');

            e.preventDefault();

        }
    });
});

NodeActions._openCloseNode = function(nodeId) {

    var icon = $('#icon-' + nodeId);
    var body = $('#body-' + nodeId);

    body.toggleClass('hide');

    if (body.hasClass('hide')) {
        icon.removeClass('fa fa-angle-up');
        icon.addClass('fa fa-angle-down');
    } else {
        icon.removeClass('fa fa-angle-down');
        icon.addClass('fa fa-angle-up');
    }
};


NodeActions.reorderChildren = function(idList, elm) {
    $osf.postJSON(
        ctx.node.urls.api + 'reorder_components/',
        {new_list: idList}
    ).fail(function(response) {
        $(elm).sortable('cancel');
        $osf.handleJSONError(response);
    });
};

NodeActions.removePointer = function(pointerId, pointerElm) {
    $.ajax({
        type: 'DELETE',
        url: ctx.node.urls.api + 'pointer/',
        data: JSON.stringify({
            pointerId: pointerId
        }),
        contentType: 'application/json',
        dataType: 'json'
    }).done(function() {
        pointerElm.remove();
    }).fail(
        $osf.handleJSONError
    );
};


/*
Display recent logs for for a node on the project view page.
*/
NodeActions.openCloseNode = function(nodeId) {
    var $logs = $('#logs-' + nodeId);
    if (!$logs.hasClass('active')) {
        if (!$logs.hasClass('served')) {
            $.getJSON(
                $logs.attr('data-uri'),
                {count: 3}
            ).done(function(response) {
                new LogFeed('#logs-' + nodeId, response.logs);
                $logs.addClass('served');
            });
        }
        $logs.addClass('active');
    } else {
        $logs.removeClass('active');
    }
    // Hide/show the html
    NodeActions._openCloseNode(nodeId);
};

// TODO: remove this
$(document).ready(function() {
    var permissionInfoHtml = '<dl>' +
        '<dt>Read</dt><dd>View project content and comment</dd>' +
        '<dt>Read + Write</dt><dd>Read privileges plus add and configure components; add and edit content</dd>' +
        '<dt>Administrator</dt><dd>Read and write privileges; manage contributors; delete and register project; public-private settings</dd>' +
        '</dl>';

    $('.permission-info').attr(
        'data-content', permissionInfoHtml
    ).popover({
        trigger: 'hover'
    });

    var bibliographicContribInfoHtml = 'Only bibliographic contributors will be displayed ' +
           'in the Contributors list and in project citations. Non-bibliographic contributors ' +
            'can read and modify the project as normal.';

    $('.visibility-info').attr(
        'data-content', bibliographicContribInfoHtml
    ).popover({
        trigger: 'hover'
    });

    ////////////////////
    // Event Handlers //
    ////////////////////

    $('.remove-pointer').on('click', function() {
        var $this = $(this);
        bootbox.confirm({
            title: 'Remove this link?',
            message: 'Are you sure you want to remove this link? This will not remove the ' +
                'project this link refers to.',
            callback: function(result) {
                if(result) {
                    var pointerId = $this.attr('data-id');
                    var pointerElm = $this.closest('.list-group-item');
                    NodeActions.removePointer(pointerId, pointerElm);
                }
            },
            buttons:{
                    confirm:{
                        label:'Remove',
                        className:'btn-danger'
                    }
            }
        });
    });

    $('#citation-more').on('click', function() {
        var panel = $('#citationStylePanel');
        panel.slideToggle(200, function() {
            if (panel.is(':visible')) {
                $('#citationStyleInput').select2('open');
            }
        });
        return false;
    });

    $('body').on('click', '.tagsinput .tag > span', function(e) {
        window.location = '/search/?q=(tags:' + $(e.target).text().toString().trim()+ ')';
    });


    // Portlet feature for the dashboard, to be implemented in later versions.
    // $( ".osf-dash-col" ).sortable({
    //   connectWith: ".osf-dash-col",
    //   handle: ".addon-widget-header",
    //   cancel: ".pull-right",
    //   placeholder: "osf-dash-portlet ui-corner-all"
    // });

    // Adds active class to current menu item
    $(function () {
        var path = window.location.pathname;
        $('.project-nav a').each(function () {
            var href = $(this).attr('href');
            if (path === href ||
               (path.indexOf('files') > -1 && href.indexOf('files') > -1) ||
               (path.indexOf('wiki') > -1 && href.indexOf('wiki') > -1)) {
                $(this).closest('li').addClass('active');
            }
        });
    });
});

window.NodeActions = NodeActions;
module.exports = NodeActions;


/***/ },

/***/ 389:
/***/ function(module, exports, __webpack_require__) {

/**
 * Controls the "Add Links" modal.
 */
'use strict';

var $ = __webpack_require__(38);
var ko = __webpack_require__(48);

var osfHelpers = __webpack_require__(47);
var Paginator = __webpack_require__(180);
var oop = __webpack_require__(146);

// Grab nodeID from global context (mako)
var nodeApiUrl = window.contextVars.node.urls.api;
var nodeId = window.contextVars.node.id;

var SEARCH_ALL_SUBMIT_TEXT = 'Search all projects';
var SEARCH_MY_PROJECTS_SUBMIT_TEXT = 'Search my projects';

var AddPointerViewModel = oop.extend(Paginator, {
    constructor: function(nodeTitle) {
        this.super.constructor.call(this);
        var self = this;
        this.nodeTitle = nodeTitle;
        this.submitEnabled = ko.observable(true);
        this.searchAllProjectsSubmitText = ko.observable(SEARCH_ALL_SUBMIT_TEXT);
        this.searchMyProjectsSubmitText = ko.observable(SEARCH_MY_PROJECTS_SUBMIT_TEXT);

        this.query = ko.observable();
        this.results = ko.observableArray();
        this.selection = ko.observableArray();
        this.errorMsg = ko.observable('');
        this.totalPages = ko.observable(0);
        this.includePublic = ko.observable(true);
        this.searchWarningMsg = ko.observable('');
        this.submitWarningMsg = ko.observable('');
        this.loadingResults = ko.observable(false);

        this.foundResults = ko.pureComputed(function() {
            return self.query() && self.results().length;
        });

        this.noResults = ko.pureComputed(function() {
            return self.query() && !self.results().length;
        });
    },
    searchAllProjects: function() {
        this.includePublic(true);
        this.pageToGet(0);
        this.searchAllProjectsSubmitText('Searching...');
        this.fetchResults();
    },
    searchMyProjects: function() {
        this.includePublic(false);
        this.pageToGet(0);
        this.searchMyProjectsSubmitText('Searching...');
        this.fetchResults();
    },
    fetchResults: function() {
        var self = this;
        self.errorMsg('');
        self.searchWarningMsg('');

        if (self.query()) {
            self.results([]); // clears page for spinner
            self.loadingResults(true); // enables spinner

            osfHelpers.postJSON(
                '/api/v1/search/node/', {
                    query: self.query(),
                    nodeId: nodeId,
                    includePublic: self.includePublic(),
                    page: self.pageToGet()
                }
            ).done(function(result) {
                if (!result.nodes.length) {
                    self.errorMsg('No results found.');
                }
                self.results(result.nodes);
                self.currentPage(result.page);
                self.numberOfPages(result.pages);
                self.addNewPaginators();
            }).fail(function(xhr) {
                    self.searchWarningMsg(xhr.responseJSON && xhr.responseJSON.message_long);
            }).always( function (){
                self.searchAllProjectsSubmitText(SEARCH_ALL_SUBMIT_TEXT);
                self.searchMyProjectsSubmitText(SEARCH_MY_PROJECTS_SUBMIT_TEXT);
                self.loadingResults(false);
            });
        } else {
            self.results([]);
            self.currentPage(0);
            self.totalPages(0);
            self.searchAllProjectsSubmitText(SEARCH_ALL_SUBMIT_TEXT);
            self.searchMyProjectsSubmitText(SEARCH_MY_PROJECTS_SUBMIT_TEXT);
        }
    },
    addTips: function(elements) {
        elements.forEach(function(element) {
            $(element).find('.contrib-button').tooltip();
        });
    },
    add: function(data) {
        this.selection.push(data);
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    },
    remove: function(data) {
        var self = this;
        self.selection.splice(
            self.selection.indexOf(data), 1
        );
        // Hack: Hide and refresh tooltips
        $('.tooltip').hide();
        $('.contrib-button').tooltip();
    },
    addAll: function() {
        var self = this;
        $.each(self.results(), function(idx, result) {
            if (self.selection().indexOf(result) === -1) {
                self.add(result);
            }
        });
    },
    removeAll: function() {
        var self = this;
        $.each(self.selection(), function(idx, selected) {
            self.remove(selected);
        });
    },
    selected: function(data) {
        var self = this;
        for (var idx = 0; idx < self.selection().length; idx++) {
            if (data.id === self.selection()[idx].id) {
                return true;
            }
        }
        return false;
    },
    submit: function() {
        var self = this;
        self.submitEnabled(false);
        self.submitWarningMsg('');

        var nodeIds = osfHelpers.mapByProperty(self.selection(), 'id');

        osfHelpers.postJSON(
            nodeApiUrl + 'pointer/', {
                nodeIds: nodeIds
            }
        ).done(function() {
            window.location.reload();
        }).fail(function(data) {
            self.submitEnabled(true);
            self.submitWarningMsg(data.responseJSON && data.responseJSON.message_long);
        });
    },
    clear: function() {
        this.query('');
        this.results([]);
        this.selection([]);
        this.searchWarningMsg('');
        this.submitWarningMsg('');
    },
    authorText: function(node) {
        var rv = node.firstAuthor;
        if (node.etal) {
            rv += ' et al.';
        }
        return rv;
    }
});

var LinksViewModel = function($elm) {

    var self = this;
    self.links = ko.observableArray([]);

    $elm.on('shown.bs.modal', function() {
        if (self.links().length === 0) {
            $.ajax({
                type: 'GET',
                url: nodeApiUrl + 'pointer/',
                dataType: 'json'
            }).done(function(response) {
                self.links(response.pointed);
            }).fail(function() {
                $elm.modal('hide');
                osfHelpers.growl('Error:', 'Could not get links');
            });
        }
    });

};

////////////////
// Public API //
////////////////

function PointerManager(selector, nodeName) {
    var self = this;
    self.selector = selector;
    self.$element = $(self.selector);
    self.nodeName = nodeName;
    self.viewModel = new AddPointerViewModel(nodeName);
    self.init();
}

PointerManager.prototype.init = function() {
    var self = this;
    ko.applyBindings(self.viewModel, self.$element[0]);
    self.$element.on('hidden.bs.modal', function() {
        self.viewModel.clear();
    });
};

function PointerDisplay(selector) {
    this.selector = selector;
    this.$element = $(selector);
    this.viewModel = new LinksViewModel(this.$element);
    ko.applyBindings(this.viewModel, this.$element[0]);
}

module.exports = {
    PointerManager: PointerManager,
    PointerDisplay: PointerDisplay
};


/***/ },

/***/ 390:
/***/ function(module, exports, __webpack_require__) {

/* WEBPACK VAR INJECTION */(function(global) {/**
* Module that enables account claiming on the project page. Makes unclaimed
* usernames show popovers when clicked, where they can input their email.
*
* Sends HTTP requests to the claim_user_post endpoint.
*/
'use strict';

var $ = __webpack_require__(38);
var bootbox = __webpack_require__(138);

var $osf = __webpack_require__(47);

var currentUserId = window.contextVars.currentUser.id;

function AccountClaimer (selector) {
    this.selector = selector;
    this.element = $(selector);  // Should select all span elements for
                                // unreg contributor names
    this.init();
}

function getClaimUrl() {
    var uid = $(this).data('pk');
    var pid = global.nodeId;
    var viewOnlyToken = $osf.urlParams().view_only;
    return '/api/v1/user/' + uid + '/' + pid +  '/claim/email/' + (viewOnlyToken ? '?view_only=' + viewOnlyToken : '');
}

function alertFinished(email) {
    $osf.growl('Email will arrive shortly', ['Please check <em>', email, '</em>'].join(''), 'success');
}

function onClickIfLoggedIn() {
    var pk = $(this).data('pk');
    if (pk !== currentUserId) {
        bootbox.confirm({
            title: 'Claim as ' + global.contextVars.currentUser.username + '?',
            message: 'If you claim this account, a contributor of this project ' +
                    'will be emailed to confirm your identity.',
            callback: function(confirmed) {
                if (confirmed) {
                    $osf.postJSON(
                        getClaimUrl(),
                        {
                            claimerId: currentUserId,
                            pk: pk
                        }
                    ).done(function(response) {
                        alertFinished(response.email);
                    }).fail(
                        $osf.handleJSONError
                    );
                }
            },
            buttons:{
                confirm:{
                    label:'Claim'
                }
            }
        });
    }
}

AccountClaimer.prototype = {
    constructor: AccountClaimer,
    init: function() {
        var self = this;
        self.element.tooltip({
            title: 'Is this you? Click to claim'
        });
        if (currentUserId.length) { // If user is logged in, ask for confirmation
            self.element.on('click', onClickIfLoggedIn);
        } else {
            self.element.editable({
                type: 'text',
                value: '',
                ajaxOptions: {
                    type: 'post',
                    contentType: 'application/json',
                    dataType: 'json'  // Expect JSON response
                },
                success: function(data) {
                    alertFinished(data.email);
                },
                error: $osf.handleJSONError,
                display: function(value, sourceData){
                    if (sourceData && sourceData.fullname) {
                        $(this).text(sourceData.fullname);
                    }
                },
                // Send JSON payload
                params: function(params) {
                    return JSON.stringify(params);
                },
                title: 'Claim Account',
                placement: 'bottom',
                placeholder: 'Enter email...',
                validate: function(value) {
                    var trimmed = $.trim(value);
                    if (!$osf.isEmail(trimmed)) {
                        return 'Not a valid email.';
                    }
                },
                url: getClaimUrl.call(this),
            });
        }
    }
};

module.exports = AccountClaimer;

/* WEBPACK VAR INJECTION */}.call(exports, (function() { return this; }())))

/***/ },

/***/ 391:
/***/ function(module, exports, __webpack_require__) {

/*
 * TODO, bring the register page up to date.
 *
 */
var $ = __webpack_require__(38);
var bootbox = __webpack_require__(138);

var $osf = __webpack_require__(47);

var preRegisterMessage =  function(title, parentTitle, parentUrl, category) {
    var titleText = $osf.htmlEscape(title);
    var parentTitleText = $osf.htmlEscape(parentTitle);
    if (parentUrl) {
        return 'You are about to register the ' + category + ' <b>' + titleText +
            '</b> including all components and data within it. This will <b>not</b> register' +
            ' its parent, <b>' + parentTitleText + '</b>.' +
            ' If you want to register the parent, please go <a href="' +
            parentUrl + '">here.</a> After clicking Register, you will next select a registration form.';
    } else {
        return 'You are about to register <b>' + titleText + '</b> ' +
            'including all components and data within it. ' +
            'Registration creates a permanent, time-stamped, uneditable version ' +
            'of the project. If you would prefer to register only one particular ' +
            'component, please navigate to that component and then initiate registration. ' +
            'After clicking Register, you will next select a registration form.';
    }
};

$(document).ready(function() {
    $('#registerNode').click(function(event) {
        var node = window.contextVars.node;
        var target = event.currentTarget.href;

        event.preventDefault();
        var title = node.title;
        var titleText = $osf.htmlEscape(title);
        var parentTitle = node.parentTitle;
        var parentRegisterUrl = node.parentRegisterUrl;
        var category = node.category;
        var bootboxTitle = 'Register ' + titleText;
        if (node.category !== 'project'){
            category = 'component';
        }

        bootbox.confirm({
            title: bootboxTitle,
            message: preRegisterMessage(title, parentTitle, parentRegisterUrl, category),
            callback: function (confirmed) {
                if(confirmed) {
                    window.location.href = target;
                }
            },
            buttons:{
                confirm:{
                    label:'Register'
                }
            }
        });
    });
});


/***/ }

});
//# sourceMappingURL=project-base-page.js.map