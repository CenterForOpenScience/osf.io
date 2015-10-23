webpackJsonp([6],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

var DataverseNodeConfig = __webpack_require__(193);

var url = window.contextVars.node.urls.api + 'dataverse/settings/';
new DataverseNodeConfig('#dataverseScope', url);


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

/***/ 193:
/***/ function(module, exports, __webpack_require__) {

/* WEBPACK VAR INJECTION */(function($) {/**
 * Module that controls the Dataverse node settings. Includes Knockout view-model
 * for syncing data.
 */

var ko = __webpack_require__(48);
var bootbox = __webpack_require__(138);
__webpack_require__(152);
var Raven = __webpack_require__(52);

var $osf = __webpack_require__(47);

var $modal = $('#dataverseInputCredentials');

ko.punches.enableAll();

function ViewModel(url) {
    var self = this;
    const otherString = 'Other (Please Specify)';

    self.addonName = 'Dataverse';
    self.url = url;
    self.urls = ko.observable();
    self.apiToken = ko.observable();

    self.ownerName = ko.observable();
    self.nodeHasAuth = ko.observable(false);
    self.userHasAuth = ko.observable(false);
    self.userIsOwner = ko.observable(false);
    self.validCredentials = ko.observable(false);
    self.loadedSettings = ko.observable(false);
    self.loadedDatasets = ko.observable(false);
    self.submitting = ko.observable(false);

    self.dataverses = ko.observableArray([]);
    self.datasets = ko.observableArray([]);

    self.savedDatasetDoi = ko.observable();
    self.savedDatasetTitle = ko.observable();
    self.savedDataverseAlias = ko.observable();
    self.savedDataverseTitle = ko.observable();
    self.datasetWasFound = ko.observable(false);

    self.accounts = ko.observable([]);
    self.hosts = ko.observableArray([]);
    self.selectedHost = ko.observable();    // Host specified in select element
    self.customHost = ko.observable();      // Host specified in input element
    self.savedHost = ko.observable();       // Configured host

    // Designated host, specified from select or input element
    self.host = ko.pureComputed(function() {
        return self.useCustomHost() ? self.customHost() : self.selectedHost();
    });
    // Hosts visible in select element. Includes presets and "Other" option
    self.visibleHosts = ko.pureComputed(function() {
        return self.hosts().concat([otherString]);
    });
    // Whether to use select element or input element for host designation
    self.useCustomHost = ko.pureComputed(function() {
        return self.selectedHost() === otherString;
    });
    self.showApiTokenInput = ko.pureComputed(function() {
        return Boolean(self.selectedHost());
    });
    self.tokenUrl = ko.pureComputed(function() {
       return self.host() ? 'https://' + self.host() + '/account/apitoken' : null;
    });
    self.savedHostUrl = ko.pureComputed(function() {
        return 'https://' + self.savedHost();
    });

    self.messages = {
        userSettingsError: ko.pureComputed(function() {
            return 'Could not retrieve settings. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        }),
        confirmDeauth: ko.pureComputed(function() {
            return 'Are you sure you want to remove this ' + self.addonName + ' account?';
        }),
        confirmAuth: ko.pureComputed(function() {
            return 'Are you sure you want to authorize this project with your ' + self.addonName + ' access token?';
        }),
        deauthorizeSuccess: ko.pureComputed(function() {
            return 'Disconnected ' + self.addonName + '.';
        }),
        deauthorizeFail: ko.pureComputed(function() {
            return 'Could not disconnect because of an error. Please try again later.';
        }),
        authInvalid: ko.pureComputed(function() {
            return 'The API token provided for ' + self.host() + ' is invalid.';
        }),
        authError: ko.pureComputed(function() {
            return 'Sorry, but there was a problem connecting to that instance of Dataverse. It ' +
                'is likely that the instance hasn\'t been upgraded to Dataverse 4.0. If you ' +
                'have any questions or believe this to be an error, please contact ' +
                'support@osf.io.';
        }),
        tokenImportSuccess: ko.pureComputed(function() {
            return 'Successfully imported access token from profile.';
        }),
        tokenImportError: ko.pureComputed(function() {
            return 'Error occurred while importing access token.';
        }),
        updateAccountsError: ko.pureComputed(function() {
            return 'Could not retrieve ' + self.addonName + ' account list at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
        }),
        datasetDeaccessioned: ko.pureComputed(function() {
            return 'This dataset has already been deaccessioned on Dataverse ' +
                'and cannot be connected to the OSF.';
        }),
        forbiddenCharacters: ko.pureComputed(function() {
            return 'This dataset cannot be connected due to forbidden characters ' +
                'in one or more of the dataset\'s file names. This issue has been forwarded to our ' +
                'development team.';
        }),
        setInfoSuccess: ko.pureComputed(function() {
            var filesUrl = window.contextVars.node.urls.web + 'files/';
            return 'Successfully linked dataset \'' + self.savedDatasetTitle() + '\'. Go to the <a href="' +
                filesUrl + '">Files page</a> to view your content.';
        }),
        setDatasetError: ko.pureComputed(function() {
            return 'Could not connect to this dataset. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        }),
        getDatasetsError: ko.pureComputed(function() {
            return 'Could not load datasets. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        })
    };

    self.savedDatasetUrl = ko.pureComputed(function() {
        return (self.urls()) ? self.urls().datasetPrefix + self.savedDatasetDoi() : null;
    });
    self.savedDataverseUrl = ko.pureComputed(function() {
        return (self.urls()) ? self.urls().dataversePrefix + self.savedDataverseAlias() : null;
    });

    self.selectedDataverseAlias = ko.observable();
    self.selectedDatasetDoi = ko.observable();
    self.selectedDataverseTitle = ko.pureComputed(function() {
        for (var i = 0; i < self.dataverses().length; i++) {
            var data = self.dataverses()[i];
            if (data.alias === self.selectedDataverseAlias()) {
                return data.title;
            }
        }
        return null;
    });
    self.selectedDatasetTitle = ko.pureComputed(function() {
        for (var i = 0; i < self.datasets().length; i++) {
            var data = self.datasets()[i];
            if (data.doi === self.selectedDatasetDoi()) {
                return data.title;
            }
        }
        return null;
    });
    self.dataverseHasDatasets = ko.pureComputed(function() {
        return self.datasets().length > 0;
    });

    self.showDatasetSelect = ko.pureComputed(function() {
        return self.loadedDatasets() && self.dataverseHasDatasets();
    });
    self.showNoDatasets = ko.pureComputed(function() {
        return self.loadedDatasets() && !self.dataverseHasDatasets();
    });
    self.showLinkedDataset = ko.pureComputed(function() {
        return self.savedDatasetDoi();
    });
    self.showLinkDataverse = ko.pureComputed(function() {
        return self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings();
    });
    self.credentialsChanged = ko.pureComputed(function() {
        return self.nodeHasAuth() && !self.validCredentials();
    });
    self.showInputCredentials = ko.pureComputed(function() {
        return (self.credentialsChanged() && self.userIsOwner()) ||
            (!self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings());
    });
    self.hasDataverses = ko.pureComputed(function() {
        return self.dataverses().length > 0;
    });
    self.showNotFound = ko.pureComputed(function() {
        return self.savedDatasetDoi() && self.loadedDatasets() && !self.datasetWasFound();
    });
    self.showSubmitDataset = ko.pureComputed(function() {
        return self.nodeHasAuth() && self.validCredentials() && self.userIsOwner();
    });
    self.enableSubmitDataset = ko.pureComputed(function() {
        return !self.submitting() && self.dataverseHasDatasets() &&
            self.savedDatasetDoi() !== self.selectedDatasetDoi();
    });

    self.showSettings = ko.pureComputed(function() {
        return self.nodeHasAuth() && self.validCredentials();
    });
    self.showImport = ko.pureComputed(function() {
        return self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings();
    });
    self.showTokenCreateButton = ko.pureComputed(function() {
        return !self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings();
    });

    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    // Update above observables with data from the server
    $.ajax({
        url: url,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        // Update view model
        self.updateFromData(response.result);
        self.loadedSettings(true);
    }).fail(function(xhr, textStatus, error) {
        self.changeMessage(self.messages.userSettingsError, 'text-danger');
        Raven.captureMessage('Could not GET dataverse settings', {
            url: url,
            textStatus: textStatus,
            error: error
        });
    });

    self.selectionChanged = function() {
        self.changeMessage('','');
    };
}

/**
 * Update the view model from data returned from the server.
 */
ViewModel.prototype.updateFromData = function(data) {
    var self = this;
    self.urls(data.urls);
    self.ownerName(data.ownerName);
    self.nodeHasAuth(data.nodeHasAuth);
    self.userHasAuth(data.userHasAuth);
    self.userIsOwner(data.userIsOwner);
    self.hosts(data.hosts);

    if (self.nodeHasAuth()) {
        self.savedHost(data.dataverseHost);
        self.dataverses(data.dataverses);
        self.savedDataverseAlias(data.savedDataverse.alias);
        self.savedDataverseTitle(data.savedDataverse.title);
        self.selectedDataverseAlias(data.savedDataverse.alias);
        self.savedDatasetDoi(data.savedDataset.doi);
        self.savedDatasetTitle(data.savedDataset.title);
        self.validCredentials(data.connected);
        if (self.userIsOwner()) {
            self.getDatasets(); // Sets datasets, selectedDatasetDoi
        }
    }
};

/** Reset all fields from Dataverse host selection modal */
ViewModel.prototype.clearModal = function() {
    var self = this;
    self.message('');
    self.messageClass('text-info');
    self.apiToken(null);
    self.selectedHost(null);
    self.customHost(null);
};

ViewModel.prototype.setInfo = function() {
    var self = this;
    self.submitting(true);
    return $osf.postJSON(
        self.urls().set,
        ko.toJS({
            dataverse: {
                alias: self.selectedDataverseAlias
            },
            dataset: {
                doi: self.selectedDatasetDoi
            }
        })
    ).done(function() {
        self.submitting(false);
        self.savedDataverseAlias(self.selectedDataverseAlias());
        self.savedDataverseTitle(self.selectedDataverseTitle());
        self.savedDatasetDoi(self.selectedDatasetDoi());
        self.savedDatasetTitle(self.selectedDatasetTitle());
        self.datasetWasFound(true);
        self.changeMessage(self.messages.setInfoSuccess, 'text-success');
    }).fail(function(xhr, textStatus, error) {
        self.submitting(false);
        var errorMessage = (xhr.status === 410) ? self.messages.datasetDeaccessioned :
            (xhr.status = 406) ? self.messages.forbiddenCharacters : self.messages.setDatasetError;
        self.changeMessage(errorMessage, 'text-danger');
        Raven.captureMessage('Could not authenticate with Dataverse', {
            url: self.urls().set,
            textStatus: textStatus,
            error: error
        });
    });
};

/**
 * Looks for dataset in list of datasets when first loaded.
 * This prevents an additional request to the server, but requires additional logic.
 */
ViewModel.prototype.findDataset = function() {
    var self = this;
    for (var i in self.datasets()) {
        if (self.datasets()[i].doi === self.savedDatasetDoi()) {
            self.datasetWasFound(true);
            return;
        }
    }
};

ViewModel.prototype.getDatasets = function() {
    var self = this;
    self.datasets([]);
    self.loadedDatasets(false);
    return $osf.postJSON(
        self.urls().getDatasets,
        ko.toJS({
            alias: self.selectedDataverseAlias
        })
    ).done(function(response) {
        // Don't update if another Dataverse has been selected
        if (response.alias === self.selectedDataverseAlias()) {
            self.datasets(response.datasets);
            self.loadedDatasets(true);
            self.selectedDatasetDoi(self.savedDatasetDoi());
            self.findDataset();
        }
    }).fail(function(xhr, status, error) {
        self.changeMessage(self.messages.getDatasetsError, 'text-danger');
        Raven.captureMessage('Could not GET datasets', {
            url: self.urls().getDatasets,
            textStatus: status,
            error: error
        });
    });
};

/** Send POST request to authorize Dataverse */
ViewModel.prototype.sendAuth = function() {
    var self = this;

    // Selection should not be empty
    if( !self.selectedHost() ){
        self.changeMessage("Please select a Dataverse repository.", 'text-danger');
        return;
    }
    var url = self.urls().create;
    return $osf.postJSON(
        url,
        ko.toJS({
            host: self.host,
            api_token: self.apiToken
        })
    ).done(function() {
        self.clearModal();
        $modal.modal('hide');
        self.userHasAuth(true);
        self.importAuth();
    }).fail(function(xhr, textStatus, error) {
        var errorMessage = (xhr.status === 401) ? self.messages.authInvalid : self.messages.authError;
        self.changeMessage(errorMessage, 'text-danger');
        Raven.captureMessage('Could not authenticate with Dataverse', {
            url: url,
            textStatus: textStatus,
            error: error
        });
    });
};

ViewModel.prototype.fetchAccounts = function() {
    var self = this;
    var ret = $.Deferred();
    var request = $.get(self.urls().accounts);
    request.then(function(data) {
        ret.resolve(data.accounts);
    });
    request.fail(function(xhr, textStatus, error) {
        self.changeMessage(self.messages.updateAccountsError(), 'text-danger');
        Raven.captureMessage('Could not GET ' + self.addonName + ' accounts for user', {
            url: self.url,
            textStatus: textStatus,
            error: error
        });
        ret.reject(xhr, textStatus, error);
    });
    return ret.promise();
};

ViewModel.prototype.updateAccounts = function() {
    var self = this;
    return self.fetchAccounts()
        .done(function(accounts) {
            self.accounts(
                $.map(accounts, function(account) {
                    return {
                        name: account.display_name,
                        id: account.id
                    };
                })
            );
        });
};

ViewModel.prototype.onImportSuccess = function(response) {
    var self = this;
    var msg = response.message || self.messages.tokenImportSuccess();
    // Update view model based on response
    self.changeMessage(msg, 'text-success', 3000);
    self.updateFromData(response.result);
};

ViewModel.prototype.onImportError = function(xhr, status, error) {
    var self = this;
    self.changeMessage(self.messages.tokenImportError(), 'text-danger');
    Raven.captureMessage('Failed to import ' + self.addonName + ' access token.', {
        xhr: xhr,
        status: status,
        error: error
    });
};

/**
 * Allows a user to create an access token from the nodeSettings page
 */
ViewModel.prototype.connectAccount = function() {
    var self = this;

    window.oauthComplete = function(res) {
        // Update view model based on response
        self.changeMessage(self.messages.connectAccountSuccess(), 'text-success', 3000);
        self.importAuth.call(self);
    };
    window.open(self.urls().auth);
};

ViewModel.prototype.connectExistingAccount = function(account_id) {
    var self = this;

    return $osf.putJSON(
        self.urls().importAuth, {
            external_account_id: account_id
        }
    ).then(self.onImportSuccess.bind(self), self.onImportError.bind(self));
};

/**
 *  Send PUT request to import access token from user profile.
 */
ViewModel.prototype.importAuth = function() {
    var self = this;
    self.updateAccounts()
        .then(function(){
            if (self.accounts().length > 1) {
                bootbox.prompt({
                    title: 'Choose ' + self.addonName + ' Access Token to Import',
                    inputType: 'select',
                    inputOptions: ko.utils.arrayMap(
                        self.accounts(),
                        function(item) {
                            return {
                                text: item.name,
                                value: item.id
                            };
                        }
                    ),
                    value: self.accounts()[0].id,
                    callback: function(accountId) {
                        if (accountId) {
                            self.connectExistingAccount.call(self, (accountId));
                        }
                    },
                    buttons:{
                        confirm:{
                            label: 'Import'
                        }
                    }
                });
            } else {
                bootbox.confirm({
                    title: 'Import ' + self.addonName + ' Access Token?',
                    message: self.messages.confirmAuth(),
                    callback: function(confirmed) {
                        if (confirmed) {
                            self.connectExistingAccount.call(self, (self.accounts()[0].id));
                        }
                    },
                    buttons:{
                        confirm:{
                            label:'Import'
                        }
                    }
                });
            }
        });
};

/**
 * Send DELETE request to deauthorize this node.
 */
ViewModel.prototype._deauthorizeConfirm = function() {
    var self = this;
    var request = $.ajax({
        url: self.urls().deauthorize,
        type: 'DELETE'
    });
    request.done(function() {
        // Update observables
        self.nodeHasAuth(false);
        self.clearModal();
        self.changeMessage(self.messages.deauthorizeSuccess(), 'text-warning', 3000);
    });
    request.fail(function(xhr, textStatus, error) {
        self.changeMessage(self.messages.deauthorizeFail(), 'text-danger');
        Raven.captureMessage('Could not deauthorize ' + self.addonName + ' account from node', {
            url: self.urls().deauthorize,
            textStatus: textStatus,
            error: error
        });
    });
    return request;
};

/** Pop up a confirmation to deauthorize addon from this node.
 *  Send DELETE request if confirmed.
 */
ViewModel.prototype.deauthorize = function() {
    var self = this;
    bootbox.confirm({
        title: 'Disconnect ' + self.addonName + ' Account?',
        message: self.messages.confirmDeauth(),
        callback: function(confirmed) {
            if (confirmed) {
                self._deauthorizeConfirm();
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

/** Change the flashed status message */
ViewModel.prototype.changeMessage = function(text, css, timeout) {
    var self = this;
    if (typeof text === 'function') {
        text = text();
    }
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

function DataverseNodeConfig(selector, url) {
    // Initialization code
    var self = this;
    self.selector = selector;
    self.url = url;
    // On success, instantiate and bind the ViewModel
    self.viewModel = new ViewModel(url);
    $osf.applyBindings(self.viewModel, '#dataverseScope');
}
module.exports = DataverseNodeConfig;

/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(38)))

/***/ }

});
//# sourceMappingURL=node-cfg.js.map