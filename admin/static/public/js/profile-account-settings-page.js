webpackJsonp([30],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

'use strict';

var $ = __webpack_require__(38);
var $osf = __webpack_require__(47);
var accountSettings = __webpack_require__(378);

$(function() {
    var viewModel = new accountSettings.UserProfileViewModel();
    $osf.applyBindings(viewModel, '#connectedEmails');
    viewModel.init();

    $osf.applyBindings(
        new accountSettings.DeactivateAccountViewModel(),
        '#deactivateAccount'
    );

    $osf.applyBindings(
        new accountSettings.ExportAccountViewModel(),
        '#exportAccount'
    );
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

/***/ 378:
/***/ function(module, exports, __webpack_require__) {

'use strict';

var $ = __webpack_require__(38);
var $osf = __webpack_require__(47);
var bootbox = __webpack_require__(138);
var ko = __webpack_require__(48);
var oop = __webpack_require__(146);
var Raven = __webpack_require__(52);
var ChangeMessageMixin = __webpack_require__(379);

__webpack_require__(152);
ko.punches.enableAll();


var UserEmail = oop.defclass({
    constructor: function(params) {
        params = params || {};
        this.address = ko.observable(params.address);
        this.isConfirmed = ko.observable(params.isConfirmed || false);
        this.isPrimary = ko.observable(params.isPrimary || false);
    }
});


var UserProfile = oop.defclass({
    constructor: function () {

        this.id = ko.observable();
        this.emails = ko.observableArray();

        this.primaryEmail = ko.pureComputed(function () {
            var emails = this.emails();
            for (var i = 0; i < this.emails().length; i++) {
                if(emails[i].isPrimary()) {
                    return emails[i];
                }
            }
            return new UserEmail();
        }.bind(this));

        this.alternateEmails = ko.pureComputed(function () {
            var emails = this.emails();
            var retval = [];
            for (var i = 0; i < this.emails().length; i++) {
                if (emails[i].isConfirmed() && !emails[i].isPrimary()) {
                    retval.push(emails[i]);
                }
            }
            return retval;
        }.bind(this));

        this.unconfirmedEmails = ko.pureComputed(function () {
            var emails = this.emails();
            var retval = [];
            for (var i = 0; i < this.emails().length; i++) {
                if(!emails[i].isConfirmed()) {
                    retval.push(emails[i]);
                }
            }
            return retval;
        }.bind(this));

    }
});


var UserProfileClient = oop.defclass({
    constructor: function () {},
    urls: {
        fetch: '/api/v1/profile/',
        update: '/api/v1/profile/',
        resend: '/api/v1/resend/'
    },
    fetch: function () {
        var ret = $.Deferred();

        var request = $.get(this.urls.fetch);
        request.done(function(data) {
            ret.resolve(this.unserialize(data));
        }.bind(this));
        request.fail(function(xhr, status, error) {
            $osf.growl('Error', 'Could not fetch user profile.', 'danger');
            Raven.captureMessage('Error fetching user profile', {
                url: this.urls.fetch,
                status: status,
                error: error
            });
            ret.reject(xhr, status, error);
        }.bind(this));

        return ret.promise();
    },
    update: function (profile, email) {
        var url = this.urls.update;
        if(email) {
            url = this.urls.resend;
        }
        var ret = $.Deferred();
        var request = $osf.putJSON(
            url,
            this.serialize(profile, email)
        ).done(function (data) {
            ret.resolve(this.unserialize(data, profile));
        }.bind(this)).fail(function(xhr, status, error) {
            if (xhr.status === 400) {
                $osf.growl('Error', xhr.responseJSON.message_long);

            } else {
                $osf.growl('Error', 'User profile not updated. Please refresh the page and try ' +
                'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                'if the problem persists.', 'danger');
            }

            Raven.captureMessage('Error fetching user profile', {
                url: this.urls.update,
                status: status,
                error: error
            });
            ret.reject(xhr, status, error);
        }.bind(this));

        return ret;
    },
    serialize: function (profile, email) {
        if(email){
            return {
                id: profile.id(),
                email: {
                    address: email.address(),
                    primary: email.isPrimary(),
                    confirmed: email.isConfirmed()
                }
            };
        }
        return {
            id: profile.id(),
            emails: ko.utils.arrayMap(profile.emails(), function(email) {
                return {
                    address: email.address(),
                    primary: email.isPrimary(),
                    confirmed: email.isConfirmed()
                };
            })

        };
    },
    unserialize: function (data, profile) {
        if (typeof(profile) === 'undefined') {
            profile = new UserProfile();
        }

        profile.id(data.profile.id);
        profile.emails(
            ko.utils.arrayMap(data.profile.emails, function (emailData){
                var email = new UserEmail({
                    address: emailData.address,
                    isPrimary: emailData.primary,
                    isConfirmed: emailData.confirmed
                });
                return email;
            })
        );

        return profile;
    }
});


var UserProfileViewModel = oop.extend(ChangeMessageMixin, {
    constructor: function() {
        this.super.constructor.call(this);
        this.client = new UserProfileClient();
        this.profile = ko.observable(new UserProfile());
        this.emailInput = ko.observable('');

    },
    init: function () {
        this.client.fetch().done(
            function(profile) { this.profile(profile); }.bind(this)
        );
    },
    addEmail: function () {
        this.changeMessage('', 'text-info');
        var newEmail = this.emailInput().toLowerCase().trim();
        if(newEmail){

            var email = new UserEmail({
                address: newEmail
            });

            // ensure email isn't already in the list
            for (var i=0; i<this.profile().emails().length; i++) {
                if (this.profile().emails()[i].address() === email.address()) {
                    this.changeMessage('Duplicate Email', 'text-warning');
                    this.emailInput('');
                    return;
                }
            }

            this.profile().emails.push(email);

            this.client.update(this.profile()).done(function (profile) {
                this.profile(profile);

                var emails = profile.emails();
                for (var i=0; i<emails.length; i++) {
                    if (emails[i].address() === email.address()) {
                        this.emailInput('');
                        var addrText = $osf.htmlEscape(email.address());
                        $osf.growl('<em>' + addrText  + '</em> added to your account.','You will receive a confirmation email at <em>' + addrText  + '</em>. Please check your email and confirm.', 'success');
                        return;
                    }
                }
            }.bind(this)).fail(function(){
                this.profile().emails.remove(email);
            }.bind(this));
        } else {
            this.changeMessage('Email cannot be empty.', 'text-danger');
        }
    },
    resendConfirmation: function(email){
        var self = this;
        self.changeMessage('', 'text-info');
        var addrText = $osf.htmlEscape(email.address());
        bootbox.confirm({
            title: 'Resend Email Confirmation?',
            message: 'Are you sure that you want to resend email confirmation to ' + '<em>' + addrText + '</em>?',
            callback: function (confirmed) {
                if (confirmed) {
                    self.client.update(self.profile(), email).done(function () {
                        $osf.growl(
                            'Email confirmation resent to <em>' + addrText + '</em>',
                            'You will receive a new confirmation email at <em>' + addrText  + '</em>. Please check your email and confirm.',
                            'success');
                    });
                }
            },
            buttons:{
                confirm:{
                    label:'Resend'
                }
            }
        });
    },
    removeEmail: function (email) {
        var self = this;
        self.changeMessage('', 'text-info');
        if (self.profile().emails().indexOf(email) !== -1) {
            var addrText = $osf.htmlEscape(email.address());
            bootbox.confirm({
                title: 'Remove Email?',
                message: 'Are you sure that you want to remove ' + '<em>' + addrText + '</em>' + ' from your email list?',
                callback: function (confirmed) {
                    if (confirmed) {
                        self.profile().emails.remove(email);
                        self.client.update(self.profile()).done(function () {
                            $osf.growl('Email Removed', '<em>' + addrText + '</em>', 'success');
                        });
                    }
                },
                buttons:{
                    confirm:{
                        label:'Remove',
                        className:'btn-danger'
                    }
                }
            });
        } else {
            $osf.growl('Error', 'Please refresh the page and try again.', 'danger');
        }
    },
    makeEmailPrimary: function (email) {
        this.changeMessage('', 'text-info');
        if (this.profile().emails().indexOf(email) !== -1) {
            this.profile().primaryEmail().isPrimary(false);
            email.isPrimary(true);
            this.client.update(this.profile()).done(function () {
                var addrText = $osf.htmlEscape(email.address());
                $osf.growl('Made Primary', '<em>' + addrText + '<em>', 'success');
            });
        } else {
            $osf.growl('Error', 'Please refresh the page and try again.', 'danger');
        }
    }
});


var DeactivateAccountViewModel = oop.defclass({
    constructor: function () {
        this.success = ko.observable(false);
    },
    urls: {
        'update': '/api/v1/profile/deactivate/'
    },
    _requestDeactivation: function() {
        var request = $osf.postJSON(this.urls.update, {});
        request.done(function() {
            $osf.growl('Success', 'An OSF administrator will contact you shortly to confirm your deactivation request.', 'success');
            this.success(true);
        }.bind(this));
        request.fail(function(xhr, status, error) {
            $osf.growl('Error',
                'Deactivation request failed. Please contact <a href="mailto: support@cos.io">support@cos.io</a> if the problem persists.',
                'danger'
            );
            Raven.captureMessage('Error requesting account deactivation', {
                url: this.urls.update,
                status: status,
                error: error
            });
        }.bind(this));
        return request;
    },
    submit: function () {
        var self = this;
        bootbox.confirm({
            title: 'Request account deactivation?',
            message: 'Are you sure you want to request account deactivation? An OSF administrator will review your request. If accepted, you ' +
                     'will <strong>NOT</strong> be able to reactivate your account.',
            callback: function(confirmed) {
                if (confirmed) {
                    return self._requestDeactivation();
                }
            },
            buttons:{
                confirm:{
                    label:'Request',
                    className:'btn-danger'
                }
            }
        });
    }
});


var ExportAccountViewModel = oop.defclass({
    constructor: function () {
        this.success = ko.observable(false);
    },
    urls: {
        'update': '/api/v1/profile/export/'
    },
    _requestExport: function() {
        var request = $osf.postJSON(this.urls.update, {});
        request.done(function() {
            $osf.growl('Success', 'An OSF administrator will contact you shortly to confirm your export request.', 'success');
            this.success(true);
        }.bind(this));
        request.fail(function(xhr, status, error) {
            $osf.growl('Error',
                'Export request failed. Please contact <a href="mailto: support@cos.io">support@cos.io</a> if the problem persists.',
                'danger'
            );
            Raven.captureMessage('Error requesting account export', {
                url: this.urls.update,
                status: status,
                error: error
            });
        }.bind(this));
        return request;
    },
    submit: function () {
        var self = this;
        bootbox.confirm({
            title: 'Request account export?',
            message: 'Are you sure you want to request account export?',
            callback: function(confirmed) {
                if (confirmed) {
                    return self._requestExport();
                }
            },
            buttons:{
                confirm:{
                    label:'Request'
                }
            }
        });
    }
});

module.exports = {
    UserProfileViewModel: UserProfileViewModel,
    DeactivateAccountViewModel: DeactivateAccountViewModel,
    ExportAccountViewModel: ExportAccountViewModel
};


/***/ },

/***/ 379:
/***/ function(module, exports, __webpack_require__) {

/**
 * ViewModel mixin for displaying form input help messages.
 * Adds message and messageClass observables that can be changed with the
 * changeMessage method.
 */
'use strict';
var ko = __webpack_require__(48);
var oop = __webpack_require__(146);
/** Change the flashed status message */

var ChangeMessageMixin = oop.defclass({
    constructor: function() {
        this.message = ko.observable('');
        this.messageClass = ko.observable('text-info');
    },
    changeMessage: function(text, css, timeout) {
        var self = this;
        if (typeof text === 'function') {
            text = text();
        }
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            window.setTimeout(function () {
                self.message('');
                self.messageClass('text-info');
            }, timeout);
        }
    },
    resetMessage: function() {
        this.message('');
        this.messageClass('text-info');        
    }
});

module.exports = ChangeMessageMixin;


/***/ }

});
//# sourceMappingURL=profile-account-settings-page.js.map