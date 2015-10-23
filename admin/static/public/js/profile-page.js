webpackJsonp([31],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

/**
 * Initialization code for the profile page. Currently, this just loads the necessary
 * modules and puts the profile module on the global context.
 *
*/

var profile = __webpack_require__(380); // Social, Job, Education classes
__webpack_require__(383); // Needed for nodelists to work
__webpack_require__(179); // Needed for nodelists to work

var ctx = window.contextVars;
// Instantiate all the profile modules
new profile.Social('#social', ctx.socialUrls, ['view']);
new profile.Jobs('#jobs', ctx.jobsUrls, ['view']);
new profile.Schools('#schools', ctx.schoolsUrls, ['view']);


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

/***/ 380:
/***/ function(module, exports, __webpack_require__) {

'use strict';

/*global require */
var $ = __webpack_require__(38);
var ko = __webpack_require__(48);
var bootbox = __webpack_require__(138);
__webpack_require__(143);
__webpack_require__(152);
ko.punches.enableAll();
__webpack_require__(381);

var $osf = __webpack_require__(47);
var koHelpers = __webpack_require__(142);
__webpack_require__(147);

var socialRules = {
    orcid: /orcid\.org\/([-\d]+)/i,
    researcherId: /researcherid\.com\/rid\/([-\w]+)/i,
    scholar: /scholar\.google\.com\/citations\?user=(\w+)/i,
    twitter: /twitter\.com\/(\w+)/i,
    linkedIn: /.*\/?(in\/.*|profile\/.*|pub\/.*)/i,
    impactStory: /impactstory\.org\/([\w\.-]+)/i,
    github: /github\.com\/(\w+)/i
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
    self.months = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
    self.endMonth = ko.observable();
    self.endYear = ko.observable().extend({
        required: {
            onlyIf: function() {
                return !!self.endMonth();
            },
            message: 'Please enter a year for the end date.'
        },
        year: true,
        pyDate: true
    });
    self.ongoing = ko.observable(false);
    self.displayDate = ko.observable(' ');
    self.endView = ko.computed(function() {
        return (self.ongoing() ? 'ongoing' : self.displayDate());
    }, self);
    self.startMonth = ko.observable();
    self.startYear = ko.observable().extend({
        required: {
            onlyIf: function() {
                if (!!self.endMonth() || !!self.endYear() || self.ongoing() === true) {
                    return true;
                }
            },
            message: 'Please enter a year for the start date.'
        },
        year: true,
        pyDate: true
    });

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
            return new Date(self.endYear(), '0', '1');
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

    // Start with blank profileWebsite for new users without a profile.
    self.profileWebsites = ko.observableArray(['']);

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

    self.trackedProperties = [
        self.profileWebsites,
        self.orcid,
        self.researcherId,
        self.twitter,
        self.scholar,
        self.linkedIn,
        self.impactStory,
        self.github
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
            {label: 'Google Scholar', text: self.scholar(), value: self.scholar.url()}
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
    }
    else {
        this.changeMessage(
            'Institution field is required.',
            'text-danger',
            5000
        );
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
        buttons:{
            confirm:{
                label:'Remove',
                className:'btn-danger'
            }
        }
    });
};

ListViewModel.prototype.unserialize = function(data) {
    var self = this;
    if(self.editAllowed) {
        self.editable(data.editable);
    } else {
        self.editable(false);
    }
    self.contents(ko.utils.arrayMap(data.contents || [], function (each) {
        return new self.ContentModel(self).unserialize(each);
    }));

    // Ensure at least one item is visible
    if (self.contents().length === 0) {
        self.addContent();
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

/*global module */
module.exports = {
    Names: Names,
    Social: Social,
    Jobs: Jobs,
    Schools: Schools,
    // Expose private viewmodels
    _NameViewModel: NameViewModel
};


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


/***/ }

});
//# sourceMappingURL=profile-page.js.map