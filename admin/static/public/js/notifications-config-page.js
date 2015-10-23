webpackJsonp([29],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

var $ = __webpack_require__(38);

// initialize view model for configuring mailchimp subscriptions
var NotificationsConfig =  __webpack_require__(375);
new NotificationsConfig('#selectLists', window.contextVars.mailingList);

//initialize treebeard for notification subscriptions
var ProjectNotifications = __webpack_require__(376);
var $notificationsMsg = $('#configureNotificationsMessage');

$.ajax({
    url: '/api/v1/subscriptions',
    type: 'GET',
    dataType: 'json'
}).done( function(response) {
    new ProjectNotifications(response);
}).fail( function() {
    $notificationsMsg.addClass('text-danger');
    $notificationsMsg.text('Could not retrieve notification settings.');
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

/***/ 375:
/***/ function(module, exports, __webpack_require__) {

'use strict';

var ko = __webpack_require__(48);
__webpack_require__(152);
var $ = __webpack_require__(38);
var $osf = __webpack_require__(47);
ko.punches.enableAll();

var ViewModel = function(list) {
    var self = this;
    self.list = list;
    self.subscribed = ko.observable();
    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-success');

    self.getListInfo = function() {
        $.ajax({
            url: '/api/v1/settings/notifications',
            type: 'GET',
            dataType: 'json',
            success: function(response) {
                var isSubscribed = response.mailing_lists ? response.mailing_lists[self.list] : false;
                self.subscribed(isSubscribed);
            },
            error: function() {
                var message = 'Could not retrieve settings information.';
                self.changeMessage(message, 'text-danger', 5000);
            }});
    };

    self.getListInfo();

    /** Change the flashed status message */
    self.changeMessage = function(text, css, timeout) {
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(function() {
                self.message('');
                self.messageClass('text-info');
            }, timeout);
        }
    };

    self.submit = function () {
        var payload = {};
        payload[self.list] = self.subscribed();
        var request = $osf.postJSON('/api/v1/settings/notifications/', payload);
        request.done(function () {
            self.changeMessage('Settings updated.', 'text-success', 5000);
        });
        request.fail(function (xhr) {
            if (xhr.responseJSON.error_type !== 'not_subscribed') {
                var message = 'Could not update email preferences at this time. If this issue persists, ' +
                    'please report it to <a href="mailto:support@osf.io">support@osf.io</a>.';
                self.changeMessage(message, 'text-danger', 5000);
            }
        });
    };
};

// API
function NotificationsViewModel(selector, list) {
    var self = this;
    self.viewModel = new ViewModel(list);
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = NotificationsViewModel;


/***/ },

/***/ 376:
/***/ function(module, exports, __webpack_require__) {

'use strict';

var $ = __webpack_require__(38);
var m = __webpack_require__(158);
var Treebeard = __webpack_require__(159);
var $osf = __webpack_require__(47);
var projectSettingsTreebeardBase = __webpack_require__(377);

function expandOnLoad() {
    var tb = this;  // jshint ignore: line
    for (var i = 0; i < tb.treeData.children.length; i++) {
        var parent = tb.treeData.children[i];
        tb.updateFolder(null, parent);
        expandChildren(tb, parent.children);
    }
}

function expandChildren(tb, children) {
    var openParent = false;
    for (var i = 0; i < children.length; i++) {
        var child = children[i];
        var parent = children[i].parent();
        if (child.data.kind === 'event' && child.data.event.notificationType !== 'adopt_parent') {
            openParent = true;
        }
        if (child.children.length > 0) {
            expandChildren(tb, child.children);
        }
    }
    if (openParent) {
        openAncestors(tb, children[0]);
    }
}

function openAncestors (tb, item) {
    var parent = item.parent();
    if(parent && parent.id > 0) {
        tb.updateFolder(null, parent);
        openAncestors(tb, parent);
    }
}

function subscribe(item, notification_type) {
    var id = item.parent().data.node.id;
    var event = item.data.event.title;
    var payload = {
        'id': id,
        'event': event,
        'notification_type': notification_type
    };
    $osf.postJSON(
        '/api/v1/subscriptions/',
        payload
    ).done(function(){
        //'notfiy-success' is to override default class 'success' in treebeard
        item.notify.update('Settings updated', 'notify-success', 1, 2000);
        item.data.event.notificationType = notification_type;
    }).fail(function() {
        item.notify.update('Could not update settings', 'notify-danger', 1, 2000);
    });
}

function displayParentNotificationType(item){
    var notificationTypeDescriptions = {
        'email_transactional': 'Instantly',
        'email_digest': 'Daily',
        'adopt_parent': 'Adopt setting from parent project',
        'none': 'Never'
    };

    if (item.data.event.parent_notification_type) {
        if (item.parent().parent().parent() === undefined) {
            return '(' + notificationTypeDescriptions[item.data.event.parent_notification_type] + ')';
        }
    }
    return '';
}


function ProjectNotifications(data) {

    //  Treebeard version
    var tbOptions = $.extend({}, projectSettingsTreebeardBase.defaults, {
        divID: 'grid',
        filesData: data,
        naturalScrollLimit : 0,
        resolveRows: function notificationResolveRows(item){
            var columns = [];
            var iconcss = '';
            // check if should not get icon
            if(item.children.length < 1 ){
                iconcss = 'tb-no-icon';
            }
            if (item.data.kind === 'heading') {
                if (item.data.children.length === 0) {
                    columns.push({
                        data : 'project',  // Data field name
                        folderIcons : false,
                        filter : true,
                        sortInclude : false,
                        custom : function() {
                            return m('div[style="padding-left:5px"]',
                                        [m ('p', [
                                                m('b', item.data.node.title + ': '),
                                                m('span[class="text-warning"]', ' No configured projects.')]
                                        )]
                            );
                        }
                    });
                } else {
                    columns.push({
                        data : 'project',  // Data field name
                        folderIcons : false,
                        filter : true,
                        sortInclude : false,
                        custom : function() {
                            return m('div[style="padding-left:5px"]',
                                    [m('p',
                                        [m('b', item.data.node.title + ':')]
                                )]
                            );
                        }
                    });
                }
            }
            else if (item.data.kind === 'folder' || item.data.kind === 'node') {
                columns.push({
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    sortInclude : false,
                    custom : function() {
                        if (item.data.node.url !== '') {
                            return m('a', { href : item.data.node.url, target : '_blank' }, item.data.node.title);
                        } else {
                            return m('span', item.data.node.title);
                        }

                    }
                });
            }
            else if (item.parent().data.kind === 'folder' || item.parent().data.kind === 'heading' && item.data.kind === 'event') {
                columns.push(
                {
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    css : iconcss,
                    sortInclude : false,
                    custom : function(item, col) {
                        return item.data.event.description;
                    }
                },
                {
                    data : 'notificationType',  // Data field name
                    folderIcons : false,
                    filter : false,
                    custom : function(item, col) {
                        return m('div[style="padding-right:10px"]',
                            [m('select.form-control', {
                                onchange: function(ev) {
                                    subscribe(item, ev.target.value);
                                }},
                                [
                                    m('option', {value: 'none', selected : item.data.event.notificationType === 'none' ? 'selected': ''}, 'Never'),
                                    m('option', {value: 'email_transactional', selected : item.data.event.notificationType === 'email_transactional' ? 'selected': ''}, 'Instantly'),
                                    m('option', {value: 'email_digest', selected : item.data.event.notificationType === 'email_digest' ? 'selected': ''}, 'Daily')
                            ])
                        ]);
                    }
                });
            }
            else {
                columns.push(
                {
                    data : 'project',  // Data field name
                    folderIcons : true,
                    filter : true,
                    css : iconcss,
                    sortInclude : false,
                    custom : function() {
                        return item.data.event.description;

                    }
                },
                {
                    data : 'notificationType',  // Data field name
                    folderIcons : false,
                    filter : false,
                    custom : function() {
                        return  m('div[style="padding-right:10px"]',
                            [m('select.form-control', {
                                onchange: function(ev) {
                                    subscribe(item, ev.target.value);
                                }},
                                [
                                    m('option', {value: 'adopt_parent',
                                                 selected: item.data.event.notificationType === 'adopt_parent' ? 'selected' : ''},
                                                 'Adopt setting from parent project ' + displayParentNotificationType(item)),
                                    m('option', {value: 'none', selected : item.data.event.notificationType === 'none' ? 'selected': ''}, 'Never'),
                                    m('option', {value: 'email_transactional',  selected : item.data.event.notificationType === 'email_transactional' ? 'selected': ''}, 'Instantly'),
                                    m('option', {value: 'email_digest', selected : item.data.event.notificationType === 'email_digest' ? 'selected': ''}, 'Daily')
                            ])
                        ]);
                    }
                });
            }

            return columns;
        }
    });
    var grid = new Treebeard(tbOptions);
    expandOnLoad.call(grid.tbController);
}

module.exports = ProjectNotifications;


/***/ },

/***/ 377:
/***/ function(module, exports, __webpack_require__) {

/**
 * Treebeard base for project settings
 * Currently used for wiki and notification settings
 */

'use strict';

var $ = __webpack_require__(38);
var m = __webpack_require__(158);
var Treebeard = __webpack_require__(159);
var Fangorn = __webpack_require__(186);


function resolveToggle(item) {
    var toggleMinus = m('i.fa.fa-minus', ' '),
        togglePlus = m('i.fa.fa-plus', ' ');

    if (item.children.length > 0) {
        if (item.open) {
            return toggleMinus;
        }
        return togglePlus;
    }
    item.open = true;
    return '';
}

module.exports = {
    defaults: {
        rowHeight : 33,         // user can override or get from .tb-row height
        resolveToggle: resolveToggle,
        paginate : false,       // Whether the applet starts with pagination or not.
        paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
        uploads : false,         // Turns dropzone on/off.
        resolveIcon : Fangorn.Utils.resolveIconView,
        hideColumnTitles: true,
        columnTitles : function columnTitles(item, col) {
            return [
                {
                    title: 'Project',
                    width: '60%',
                    sortType : 'text',
                    sort : false
                },
                {
                    title: 'Editing Toggle',
                    width : '40%',
                    sort : false

                }
            ];
        },
        ontogglefolder : function (item){
            var containerHeight = this.select('#tb-tbody').height();
            this.options.showTotal = Math.floor(containerHeight / this.options.rowHeight) + 1;
            this.redraw();
        },
        sortButtonSelector : {
            up : 'i.fa.fa-chevron-up',
            down : 'i.fa.fa-chevron-down'
        },
        showFilter : false,     // Gives the option to filter by showing the filter box.
        allowMove : false,       // Turn moving on or off.
        hoverClass : '',
        resolveRefreshIcon : function() {
          return m('i.fa.fa-refresh.fa-spin');
        }
    }
};

/***/ }

});
//# sourceMappingURL=notifications-config-page.js.map