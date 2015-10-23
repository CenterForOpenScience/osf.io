webpackJsonp([42],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

'use strict';

var $ = __webpack_require__(38);
var AddonHelper = __webpack_require__(359);
var S3NodeConfig = __webpack_require__(415).S3NodeConfig;

var ctx = window.contextVars;  // mako context variables

var s3Settings = {
    url: ctx.node.urls.api + 's3/settings/',
};

new S3NodeConfig('#s3Scope', s3Settings);


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

/***/ 359:
/***/ function(module, exports, __webpack_require__) {

// TODO: Deprecate me
var $ = __webpack_require__(38);
var $osf = __webpack_require__(47);

var AddonHelper = (function() {

    /**
     * Convert an HTML form to a JS object.
     *
     * @param {jQuery} form
     * @return {Object} The parsed data
     */
    function formToObj(form) {
        var rv = {};
        $.each($(form).serializeArray(), function(_, value) {
            rv[value.name] = value.value;
        });
        return rv;
    }

    /**
     * Submit add-on settings.
     */
    function onSubmitSettings() {
        var $this = $(this);
        var addon = $this.attr('data-addon');
        var owner = $this.find('span[data-owner]').attr('data-owner');
        var msgElm = $this.find('.addon-settings-message');

        var url = owner === 'user' ? '/api/v1/settings/' + addon + '/' : nodeApiUrl + addon + '/settings/';

        $osf.postJSON(
            url,
            formToObj($this)
        ).done(function() {
            msgElm.text('Settings updated')
                .removeClass('text-danger').addClass('text-success')
                .fadeOut(100).fadeIn();
        }).fail(function(response) {
            var message = '';
            response = JSON.parse(response.responseText);
            if (response && response.message) {
                message = response.message;
            } else {
                message = 'Settings not updated.';
            }
            msgElm.text(message)
                .removeClass('text-success').addClass('text-danger')
                .fadeOut(100).fadeIn();
        });

        return false;

    }

    // Expose public methods
    exports = {
        formToObj: formToObj,
        onSubmitSettings: onSubmitSettings,
    };

    if (true) {
        module.exports = exports; 
    } 
    return exports;
})();


/***/ },

/***/ 415:
/***/ function(module, exports, __webpack_require__) {

'use strict';
var ko = __webpack_require__(48);
__webpack_require__(152);
var $ = __webpack_require__(38);
var bootbox = __webpack_require__(138);
var Raven = __webpack_require__(52);

var $osf = __webpack_require__(47);

var s3Settings = __webpack_require__(416);

ko.punches.enableAll();

var defaultSettings = {
    url: '',
    encryptUploads: s3Settings.encryptUploads,
    bucketLocations: s3Settings.bucketLocations
};

var ViewModel = function(selector, settings) {
    var self = this;

    self.url = settings.url;
    self.selector = selector;
    self.settings = $.extend({}, defaultSettings, settings);

    self.nodeHasAuth = ko.observable(false);
    self.userHasAuth = ko.observable(false);
    self.userIsOwner = ko.observable(false);
    self.ownerName = ko.observable('');
    self.validCredentials = ko.observable(true);

    self.urls = ko.observable({});
    self.loadedSettings = ko.observable(false);
    self.bucketList = ko.observableArray([]);
    self.loadedBucketList = ko.observable(false);
    self.currentBucket = ko.observable('');
    self.selectedBucket = ko.observable('');
    self.encryptUploads = ko.observable(self.settings.encryptUploads);

    self.accessKey = ko.observable('');
    self.secretKey = ko.observable('');

    self.loading = ko.observable(false);
    self.creating = ko.observable(false);
    self.creatingCredentials = ko.observable(false);

    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    self.showSelect = ko.observable(false);

    self.showSettings = ko.pureComputed(function() {
        return self.nodeHasAuth() && self.validCredentials();
    });
    self.disableSettings = ko.pureComputed(function() {
        return !(self.userHasAuth() && self.userIsOwner());
    });
    self.showNewBucket = ko.pureComputed(function() {
        return self.userHasAuth() && self.userIsOwner();
    });
    self.showImport = ko.pureComputed(function() {
        return self.userHasAuth() && !self.nodeHasAuth();
    });
    self.showCreateCredentials = ko.pureComputed(function() {
        return self.loadedSettings() && (!self.nodeHasAuth() && !self.userHasAuth());
    });
    self.canChange = ko.pureComputed(function() {
        return self.userIsOwner() && self.nodeHasAuth();
    });
    self.allowSelectBucket = ko.pureComputed(function() {
        return (self.bucketList().length > 0 || self.loadedBucketList()) && (!self.loading());
    });

    self.saveButtonText = ko.pureComputed (function(){
        return self.loading()? 'Saving': 'Save';
    });
};

ViewModel.prototype.toggleSelect = function() {
    var self = this;
    self.showSelect(!self.showSelect());
    return self.updateBucketList();
};

ViewModel.prototype.updateBucketList = function(){
    var self = this;
    return self.fetchBucketList()
        .done(function(buckets){
            self.bucketList(buckets);
            self.selectedBucket(self.currentBucket());
        });
};

var isValidBucketName = function(bucketName, allowPeriods) {
    var isValidBucket;

    if (allowPeriods === true) {
        isValidBucket = /^(?!.*(\.\.|-\.))[^.][a-z0-9\d.-]{2,61}[^.]$/;
    } else {isValidBucket = /^(?!.*(\.\.|-\.))[^.][a-z0-9\d-]{2,61}[^.]$/;}

    return isValidBucket.test(bucketName);
};

ViewModel.prototype.selectBucket = function() {
    var self = this;

    self.loading(true);

    var ret = $.Deferred();
    if (!isValidBucketName(self.selectedBucket(), false)) {
        self.loading(false);
        bootbox.alert({
            title: 'Invalid bucket name',
            message: 'Sorry, the S3 addon only supports bucket names without periods.'
        });
        ret.reject();
    } else {
        $osf.postJSON(
                self.urls().set_bucket, {
                    's3_bucket': self.selectedBucket(),
                    'encrypt_uploads': self.encryptUploads()
                }
            )
            .done(function (response) {
                self.updateFromData(response);
                self.changeMessage('Successfully linked S3 bucket "' + self.currentBucket() + '". Go to the <a href="' +
                    self.urls().files + '">Files page</a> to view your content.', 'text-success');
                self.loading(false);
                ret.resolve(response);
            })
            .fail(function (xhr, status, error) {
                self.loading(false);
                var message = 'Could not change S3 bucket at this time. ' +
                    'Please refresh the page. If the problem persists, email ' +
                    '<a href="mailto:support@osf.io">support@osf.io</a>.';
                self.changeMessage(message, 'text-danger');
                Raven.captureMessage('Could not set S3 bucket', {
                    url: self.urls().setBucket,
                    textStatus: status,
                    error: error
                });
                ret.reject();
            });
    }
    return ret.promise();
};

ViewModel.prototype._deauthorizeNodeConfirm = function() {
    var self = this;
    return $.ajax({
        type: 'DELETE',
        url: self.urls().deauthorize,
        contentType: 'application/json',
        dataType: 'json'
    }).done(function(response) {
        self.updateFromData(response);
        self.changeMessage('Disconnected S3.', 'text-warning', 3000);
    }).fail(function(xhr, status, error) {
        var message = 'Could not disconnect S3 at ' +
            'this time. Please refresh the page. If the problem persists, email ' +
            '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-danger');
        Raven.captureMessage('Could not remove S3 authorization.', {
            url: self.urls().deauthorize,
            textStatus: status,
            error: error
        });
    });
};

ViewModel.prototype.deauthorizeNode = function() {
    var self = this;
    bootbox.confirm({
        title: 'Disconnect S3 Account?',
        message: 'Are you sure you want to remove this S3 account?',
        callback: function(confirm) {
            if (confirm) {
                self._deauthorizeNodeConfirm();
            }
        },
        buttons:{
            confirm:{
                label: 'Disconnect',
                className: 'btn-danger'
            }
        }
    });
};

ViewModel.prototype._importAuthConfirm = function() {
    var self = this;
    return $osf.postJSON(
        self.urls().import_auth, {}
    ).done(function(response) {
        self.changeMessage('Successfully imported S3 credentials.', 'text-success');
        self.updateFromData(response);
    }).fail(function(xhr, status, error) {
        var message = 'Could not import S3 credentials at ' +
            'this time. Please refresh the page. If the problem persists, email ' +
            '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-danger');
        Raven.captureMessage('Could not import S3 credentials', {
            url: self.urls().importAuth,
            textStatus: status,
            error: error
        });
    });

};

ViewModel.prototype.importAuth = function() {
    var self = this;
    bootbox.confirm({
        title: 'Import S3 credentials?',
        message: 'Are you sure you want to authorize this project with your S3 credentials?',
        callback: function(confirmed) {
            if (confirmed) {
                return self._importAuthConfirm();
            }
        },
        buttons:{
            confirm:{
                label:'Import'
            }
        }
    });
};

ViewModel.prototype.createCredentials = function() {
    var self = this;
    self.creatingCredentials(true);

    return $osf.postJSON(
        self.urls().create_auth, {
            secret_key: self.secretKey(),
            access_key: self.accessKey()
        }
    ).done(function(response) {
        self.creatingCredentials(false);
        self.changeMessage('Successfully added S3 credentials.', 'text-success');
        self.updateFromData(response);
    }).fail(function(xhr, status, error) {
        self.creatingCredentials(false);
        var message = '';
        var response = JSON.parse(xhr.responseText);
        if (response && response.message) {
            message = response.message;
        }
        self.changeMessage(message, 'text-danger');
        Raven.captureMessage('Could not add S3 credentials', {
            url: self.urls().importAuth,
            textStatus: status,
            error: error
        });
    });
};

ViewModel.prototype.createBucket = function(bucketName, bucketLocation) {
    var self = this;
    self.creating(true);
    bucketName = bucketName.toLowerCase();
    return $osf.postJSON(
        self.urls().create_bucket, {
            bucket_name: bucketName,
            bucket_location: bucketLocation
        }
    ).done(function(response) {
        self.creating(false);
        self.bucketList(response.buckets);
        self.loadedBucketList(true);
        self.selectedBucket(bucketName);
        self.showSelect(true);
        var msg = 'Successfully created bucket "' + bucketName + '". You can now select it from the drop down list.';
        var msgType = 'text-success';
        self.changeMessage(msg, msgType);
    }).fail(function(xhr) {
        var resp = JSON.parse(xhr.responseText);
        var message = resp.message;
        var title = resp.title || 'Problem creating bucket';
        self.creating(false);
        if (!message) {
            message = 'Looks like that name is taken. Try another name?';
        }
        bootbox.confirm({
            title: title,
            message: message,
            callback: function(result) {
                if (result) {
                    self.openCreateBucket();
                }
            },
            buttons:{
                confirm:{
                    label:'Try again'
                }
            }
        });
    });
};

ViewModel.prototype.openCreateBucket = function() {
    var self = this;

    var isValidBucket = /^(?!.*(\.\.|-\.))[^.][a-z0-9\d.-]{2,61}[^.]$/;

    // Generates html options for key-value pairs in BUCKET_LOCATION_MAP
    function generateBucketOptions(locations) {
        var options = '';
        for (var location in locations) {
            if (self.settings.bucketLocations.hasOwnProperty(location)) {
                options = options + ['<option value="', location, '">', locations[location], '</option>', '\n'].join('');
            }
        }
        return options;
    }

    bootbox.dialog({
        title: 'Create a new bucket',
        message:
                '<div class="row"> ' +
                    '<div class="col-md-12"> ' +
                        '<form class="form-horizontal"> ' +
                            '<div class="form-group"> ' +
                                '<label class="col-md-4 control-label" for="bucketName">Bucket Name</label> ' +
                                '<div class="col-md-8"> ' +
                                    '<input id="bucketName" name="bucketName" type="text" placeholder="Enter bucket name" class="form-control" autofocus> ' +
                                    '<div>' +
                                        '<span id="bucketModalErrorMessage" ></span>' +
                                    '</div>'+
                                '</div>' +
                            '</div>' +
                            '<div class="form-group"> ' +
                                '<label class="col-md-4 control-label" for="bucketLocation">Bucket Location</label> ' +
                                '<div class="col-md-8"> ' +
                                    '<select id="bucketLocation" name="bucketLocation" class="form-control"> ' +
                                        generateBucketOptions(self.settings.bucketLocations) +
                                    '</select>' +
                                '</div>' +
                            '</div>' +
                        '</form>' +
                    '</div>' +
                '</div>',
        buttons: {
            cancel: {
                label: 'Cancel',
                className: 'btn-default'
            },
            confirm: {
                label: 'Create',
                className: 'btn-success',
                callback: function () {
                    var bucketName = $('#bucketName').val();
                    var bucketLocation = $('#bucketLocation').val();

                    if (!bucketName) {
                        var errorMessage = $('#bucketModalErrorMessage');
                        errorMessage.text('Bucket name cannot be empty');
                        errorMessage[0].classList.add('text-danger');
                        return false;
                    } else if (isValidBucketName(bucketName, true)) {
                        bootbox.confirm({
                            title: 'Invalid bucket name',
                            message: 'Sorry, that\'s not a valid bucket name. Try another name?',
                            callback: function (result) {
                                if (result) {
                                    self.openCreateBucket();
                                }
                            },
                            buttons: {
                                confirm: {
                                    label: 'Try again'
                                }
                            }
                        });
                    } else {
                        self.createBucket(bucketName, bucketLocation);
                    }
                }
            }
        }
    });
};

ViewModel.prototype.fetchBucketList = function() {
    var self = this;

    var ret = $.Deferred();
    if(self.loadedBucketList()){
        ret.resolve(self.bucketList());
    }
    else{
         $.ajax({
            url: self.urls().bucket_list,
            type: 'GET',
            dataType: 'json'
        }).done(function(response) {
            self.loadedBucketList(true);
            ret.resolve(response.buckets);
        })
        .fail(function(xhr, status, error) {
            var message = 'Could not retrieve list of S3 buckets at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.changeMessage(message, 'text-danger');
            Raven.captureMessage('Could not GET s3 bucket list', {
                url: self.urls().bucketList,
                textStatus: status,
                error: error
            });
            ret.reject(xhr, status, error);
        });
    }
    return ret.promise();
};

ViewModel.prototype.updateFromData = function(data) {
    var self = this;
    var ret = $.Deferred();
    var applySettings = function(settings){
        self.nodeHasAuth(settings.node_has_auth);
        self.userHasAuth(settings.user_has_auth);
        self.userIsOwner(settings.user_is_owner);
        self.ownerName(settings.owner);
        self.validCredentials(settings.valid_credentials);
        self.currentBucket(settings.has_bucket ? settings.bucket : null);
        if (settings.urls) {
            self.urls(settings.urls);
        }
        if (self.nodeHasAuth() && !self.validCredentials()) {
            var message = '';
            if(self.userIsOwner()) {
                message = 'Could not retrieve S3 settings at ' +
                    'this time. The S3 credentials may no longer be valid.' +
                    ' Try deauthorizing and reauthorizing S3 on your <a href="' +
                    self.urls().settings + '">account settings page</a>.';
            }
            else {
                message = 'Could not retrieve S3 settings at ' +
                    'this time. The S3 addon credentials may no longer be valid.' +
                    ' Contact ' + self.ownerName() + ' to verify.';
            }
            self.changeMessage(message, 'text-danger');
        }
        ret.resolve(settings);
    };
    if (typeof data === 'undefined'){
        return self.fetchFromServer()
            .done(applySettings);
    }
    else {
        applySettings(data);
    }
    return ret.promise();
};

ViewModel.prototype.fetchFromServer = function() {
    var self = this;
    var ret = $.Deferred();
    $.ajax({
        url: self.url,
        type: 'GET',
        dataType: 'json',
        contentType: 'application/json'
    })
    .done(function(response) {
        var settings = response.result;
        self.loadedSettings(true);
        ret.resolve(settings);
    })
    .fail(function(xhr, status, error) {
        var message = 'Could not retrieve S3 settings at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-danger');
        Raven.captureMessage('Could not GET s3 settings', {
            url: self.url,
            textStatus: status,
            error: error
        });
        ret.reject(xhr, status, error);
    });
    return ret.promise();
};

/** Change the flashed message. */
ViewModel.prototype.changeMessage = function(text, css, timeout) {
    var self = this;
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

var S3Config = function(selector, settings) {
    var viewModel = new ViewModel(selector, settings);
    $osf.applyBindings(viewModel, selector);
    viewModel.updateFromData();
};

module.exports = {
    S3NodeConfig: S3Config,
    _S3NodeConfigViewModel: ViewModel,
    _isValidBucketName: isValidBucketName
};


/***/ },

/***/ 416:
/***/ function(module, exports) {

module.exports = {
	"bucketLocations": {
		"": "US Standard",
		"EU": "Europe Standard",
		"us-west-1": "California",
		"us-west-2": "Oregon",
		"ap-northeast-1": "Tokyo",
		"ap-southeast-1": "Singapore",
		"ap-southeast-2": "Sydney",
		"sa-east-1": "Sao Paulo"
	},
	"encryptUploads": true
}

/***/ }

});
//# sourceMappingURL=node-cfg.js.map