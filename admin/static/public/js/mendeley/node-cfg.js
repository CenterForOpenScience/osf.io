webpackJsonp([27],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

'use strict';

var CitationsNodeConfig = __webpack_require__(367).CitationsNodeConfig;

var url = window.contextVars.node.urls.api + 'mendeley/settings/';
new CitationsNodeConfig('Mendeley', '#mendeleyScope', url, '#mendeleyGrid');


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

/***/ 153:
/***/ function(module, exports, __webpack_require__) {

/* WEBPACK VAR INJECTION */(function(module) {/*!
 * ZeroClipboard
 * The ZeroClipboard library provides an easy way to copy text to the clipboard using an invisible Adobe Flash movie and a JavaScript interface.
 * Copyright (c) 2014 Jon Rohan, James M. Greene
 * Licensed MIT
 * http://zeroclipboard.org/
 * v2.1.6
 */
(function(window, undefined) {
  "use strict";
  /**
 * Store references to critically important global functions that may be
 * overridden on certain web pages.
 */
  var _window = window, _document = _window.document, _navigator = _window.navigator, _setTimeout = _window.setTimeout, _encodeURIComponent = _window.encodeURIComponent, _ActiveXObject = _window.ActiveXObject, _Error = _window.Error, _parseInt = _window.Number.parseInt || _window.parseInt, _parseFloat = _window.Number.parseFloat || _window.parseFloat, _isNaN = _window.Number.isNaN || _window.isNaN, _round = _window.Math.round, _now = _window.Date.now, _keys = _window.Object.keys, _defineProperty = _window.Object.defineProperty, _hasOwn = _window.Object.prototype.hasOwnProperty, _slice = _window.Array.prototype.slice, _unwrap = function() {
    var unwrapper = function(el) {
      return el;
    };
    if (typeof _window.wrap === "function" && typeof _window.unwrap === "function") {
      try {
        var div = _document.createElement("div");
        var unwrappedDiv = _window.unwrap(div);
        if (div.nodeType === 1 && unwrappedDiv && unwrappedDiv.nodeType === 1) {
          unwrapper = _window.unwrap;
        }
      } catch (e) {}
    }
    return unwrapper;
  }();
  /**
 * Convert an `arguments` object into an Array.
 *
 * @returns The arguments as an Array
 * @private
 */
  var _args = function(argumentsObj) {
    return _slice.call(argumentsObj, 0);
  };
  /**
 * Shallow-copy the owned, enumerable properties of one object over to another, similar to jQuery's `$.extend`.
 *
 * @returns The target object, augmented
 * @private
 */
  var _extend = function() {
    var i, len, arg, prop, src, copy, args = _args(arguments), target = args[0] || {};
    for (i = 1, len = args.length; i < len; i++) {
      if ((arg = args[i]) != null) {
        for (prop in arg) {
          if (_hasOwn.call(arg, prop)) {
            src = target[prop];
            copy = arg[prop];
            if (target !== copy && copy !== undefined) {
              target[prop] = copy;
            }
          }
        }
      }
    }
    return target;
  };
  /**
 * Return a deep copy of the source object or array.
 *
 * @returns Object or Array
 * @private
 */
  var _deepCopy = function(source) {
    var copy, i, len, prop;
    if (typeof source !== "object" || source == null) {
      copy = source;
    } else if (typeof source.length === "number") {
      copy = [];
      for (i = 0, len = source.length; i < len; i++) {
        if (_hasOwn.call(source, i)) {
          copy[i] = _deepCopy(source[i]);
        }
      }
    } else {
      copy = {};
      for (prop in source) {
        if (_hasOwn.call(source, prop)) {
          copy[prop] = _deepCopy(source[prop]);
        }
      }
    }
    return copy;
  };
  /**
 * Makes a shallow copy of `obj` (like `_extend`) but filters its properties based on a list of `keys` to keep.
 * The inverse of `_omit`, mostly. The big difference is that these properties do NOT need to be enumerable to
 * be kept.
 *
 * @returns A new filtered object.
 * @private
 */
  var _pick = function(obj, keys) {
    var newObj = {};
    for (var i = 0, len = keys.length; i < len; i++) {
      if (keys[i] in obj) {
        newObj[keys[i]] = obj[keys[i]];
      }
    }
    return newObj;
  };
  /**
 * Makes a shallow copy of `obj` (like `_extend`) but filters its properties based on a list of `keys` to omit.
 * The inverse of `_pick`.
 *
 * @returns A new filtered object.
 * @private
 */
  var _omit = function(obj, keys) {
    var newObj = {};
    for (var prop in obj) {
      if (keys.indexOf(prop) === -1) {
        newObj[prop] = obj[prop];
      }
    }
    return newObj;
  };
  /**
 * Remove all owned, enumerable properties from an object.
 *
 * @returns The original object without its owned, enumerable properties.
 * @private
 */
  var _deleteOwnProperties = function(obj) {
    if (obj) {
      for (var prop in obj) {
        if (_hasOwn.call(obj, prop)) {
          delete obj[prop];
        }
      }
    }
    return obj;
  };
  /**
 * Determine if an element is contained within another element.
 *
 * @returns Boolean
 * @private
 */
  var _containedBy = function(el, ancestorEl) {
    if (el && el.nodeType === 1 && el.ownerDocument && ancestorEl && (ancestorEl.nodeType === 1 && ancestorEl.ownerDocument && ancestorEl.ownerDocument === el.ownerDocument || ancestorEl.nodeType === 9 && !ancestorEl.ownerDocument && ancestorEl === el.ownerDocument)) {
      do {
        if (el === ancestorEl) {
          return true;
        }
        el = el.parentNode;
      } while (el);
    }
    return false;
  };
  /**
 * Get the URL path's parent directory.
 *
 * @returns String or `undefined`
 * @private
 */
  var _getDirPathOfUrl = function(url) {
    var dir;
    if (typeof url === "string" && url) {
      dir = url.split("#")[0].split("?")[0];
      dir = url.slice(0, url.lastIndexOf("/") + 1);
    }
    return dir;
  };
  /**
 * Get the current script's URL by throwing an `Error` and analyzing it.
 *
 * @returns String or `undefined`
 * @private
 */
  var _getCurrentScriptUrlFromErrorStack = function(stack) {
    var url, matches;
    if (typeof stack === "string" && stack) {
      matches = stack.match(/^(?:|[^:@]*@|.+\)@(?=http[s]?|file)|.+?\s+(?: at |@)(?:[^:\(]+ )*[\(]?)((?:http[s]?|file):\/\/[\/]?.+?\/[^:\)]*?)(?::\d+)(?::\d+)?/);
      if (matches && matches[1]) {
        url = matches[1];
      } else {
        matches = stack.match(/\)@((?:http[s]?|file):\/\/[\/]?.+?\/[^:\)]*?)(?::\d+)(?::\d+)?/);
        if (matches && matches[1]) {
          url = matches[1];
        }
      }
    }
    return url;
  };
  /**
 * Get the current script's URL by throwing an `Error` and analyzing it.
 *
 * @returns String or `undefined`
 * @private
 */
  var _getCurrentScriptUrlFromError = function() {
    var url, err;
    try {
      throw new _Error();
    } catch (e) {
      err = e;
    }
    if (err) {
      url = err.sourceURL || err.fileName || _getCurrentScriptUrlFromErrorStack(err.stack);
    }
    return url;
  };
  /**
 * Get the current script's URL.
 *
 * @returns String or `undefined`
 * @private
 */
  var _getCurrentScriptUrl = function() {
    var jsPath, scripts, i;
    if (_document.currentScript && (jsPath = _document.currentScript.src)) {
      return jsPath;
    }
    scripts = _document.getElementsByTagName("script");
    if (scripts.length === 1) {
      return scripts[0].src || undefined;
    }
    if ("readyState" in scripts[0]) {
      for (i = scripts.length; i--; ) {
        if (scripts[i].readyState === "interactive" && (jsPath = scripts[i].src)) {
          return jsPath;
        }
      }
    }
    if (_document.readyState === "loading" && (jsPath = scripts[scripts.length - 1].src)) {
      return jsPath;
    }
    if (jsPath = _getCurrentScriptUrlFromError()) {
      return jsPath;
    }
    return undefined;
  };
  /**
 * Get the unanimous parent directory of ALL script tags.
 * If any script tags are either (a) inline or (b) from differing parent
 * directories, this method must return `undefined`.
 *
 * @returns String or `undefined`
 * @private
 */
  var _getUnanimousScriptParentDir = function() {
    var i, jsDir, jsPath, scripts = _document.getElementsByTagName("script");
    for (i = scripts.length; i--; ) {
      if (!(jsPath = scripts[i].src)) {
        jsDir = null;
        break;
      }
      jsPath = _getDirPathOfUrl(jsPath);
      if (jsDir == null) {
        jsDir = jsPath;
      } else if (jsDir !== jsPath) {
        jsDir = null;
        break;
      }
    }
    return jsDir || undefined;
  };
  /**
 * Get the presumed location of the "ZeroClipboard.swf" file, based on the location
 * of the executing JavaScript file (e.g. "ZeroClipboard.js", etc.).
 *
 * @returns String
 * @private
 */
  var _getDefaultSwfPath = function() {
    var jsDir = _getDirPathOfUrl(_getCurrentScriptUrl()) || _getUnanimousScriptParentDir() || "";
    return jsDir + "ZeroClipboard.swf";
  };
  /**
 * Keep track of the state of the Flash object.
 * @private
 */
  var _flashState = {
    bridge: null,
    version: "0.0.0",
    pluginType: "unknown",
    disabled: null,
    outdated: null,
    unavailable: null,
    deactivated: null,
    overdue: null,
    ready: null
  };
  /**
 * The minimum Flash Player version required to use ZeroClipboard completely.
 * @readonly
 * @private
 */
  var _minimumFlashVersion = "11.0.0";
  /**
 * Keep track of all event listener registrations.
 * @private
 */
  var _handlers = {};
  /**
 * Keep track of the currently activated element.
 * @private
 */
  var _currentElement;
  /**
 * Keep track of the element that was activated when a `copy` process started.
 * @private
 */
  var _copyTarget;
  /**
 * Keep track of data for the pending clipboard transaction.
 * @private
 */
  var _clipData = {};
  /**
 * Keep track of data formats for the pending clipboard transaction.
 * @private
 */
  var _clipDataFormatMap = null;
  /**
 * The `message` store for events
 * @private
 */
  var _eventMessages = {
    ready: "Flash communication is established",
    error: {
      "flash-disabled": "Flash is disabled or not installed",
      "flash-outdated": "Flash is too outdated to support ZeroClipboard",
      "flash-unavailable": "Flash is unable to communicate bidirectionally with JavaScript",
      "flash-deactivated": "Flash is too outdated for your browser and/or is configured as click-to-activate",
      "flash-overdue": "Flash communication was established but NOT within the acceptable time limit"
    }
  };
  /**
 * ZeroClipboard configuration defaults for the Core module.
 * @private
 */
  var _globalConfig = {
    swfPath: _getDefaultSwfPath(),
    trustedDomains: window.location.host ? [ window.location.host ] : [],
    cacheBust: true,
    forceEnhancedClipboard: false,
    flashLoadTimeout: 3e4,
    autoActivate: true,
    bubbleEvents: true,
    containerId: "global-zeroclipboard-html-bridge",
    containerClass: "global-zeroclipboard-container",
    swfObjectId: "global-zeroclipboard-flash-bridge",
    hoverClass: "zeroclipboard-is-hover",
    activeClass: "zeroclipboard-is-active",
    forceHandCursor: false,
    title: null,
    zIndex: 999999999
  };
  /**
 * The underlying implementation of `ZeroClipboard.config`.
 * @private
 */
  var _config = function(options) {
    if (typeof options === "object" && options !== null) {
      for (var prop in options) {
        if (_hasOwn.call(options, prop)) {
          if (/^(?:forceHandCursor|title|zIndex|bubbleEvents)$/.test(prop)) {
            _globalConfig[prop] = options[prop];
          } else if (_flashState.bridge == null) {
            if (prop === "containerId" || prop === "swfObjectId") {
              if (_isValidHtml4Id(options[prop])) {
                _globalConfig[prop] = options[prop];
              } else {
                throw new Error("The specified `" + prop + "` value is not valid as an HTML4 Element ID");
              }
            } else {
              _globalConfig[prop] = options[prop];
            }
          }
        }
      }
    }
    if (typeof options === "string" && options) {
      if (_hasOwn.call(_globalConfig, options)) {
        return _globalConfig[options];
      }
      return;
    }
    return _deepCopy(_globalConfig);
  };
  /**
 * The underlying implementation of `ZeroClipboard.state`.
 * @private
 */
  var _state = function() {
    return {
      browser: _pick(_navigator, [ "userAgent", "platform", "appName" ]),
      flash: _omit(_flashState, [ "bridge" ]),
      zeroclipboard: {
        version: ZeroClipboard.version,
        config: ZeroClipboard.config()
      }
    };
  };
  /**
 * The underlying implementation of `ZeroClipboard.isFlashUnusable`.
 * @private
 */
  var _isFlashUnusable = function() {
    return !!(_flashState.disabled || _flashState.outdated || _flashState.unavailable || _flashState.deactivated);
  };
  /**
 * The underlying implementation of `ZeroClipboard.on`.
 * @private
 */
  var _on = function(eventType, listener) {
    var i, len, events, added = {};
    if (typeof eventType === "string" && eventType) {
      events = eventType.toLowerCase().split(/\s+/);
    } else if (typeof eventType === "object" && eventType && typeof listener === "undefined") {
      for (i in eventType) {
        if (_hasOwn.call(eventType, i) && typeof i === "string" && i && typeof eventType[i] === "function") {
          ZeroClipboard.on(i, eventType[i]);
        }
      }
    }
    if (events && events.length) {
      for (i = 0, len = events.length; i < len; i++) {
        eventType = events[i].replace(/^on/, "");
        added[eventType] = true;
        if (!_handlers[eventType]) {
          _handlers[eventType] = [];
        }
        _handlers[eventType].push(listener);
      }
      if (added.ready && _flashState.ready) {
        ZeroClipboard.emit({
          type: "ready"
        });
      }
      if (added.error) {
        var errorTypes = [ "disabled", "outdated", "unavailable", "deactivated", "overdue" ];
        for (i = 0, len = errorTypes.length; i < len; i++) {
          if (_flashState[errorTypes[i]] === true) {
            ZeroClipboard.emit({
              type: "error",
              name: "flash-" + errorTypes[i]
            });
            break;
          }
        }
      }
    }
    return ZeroClipboard;
  };
  /**
 * The underlying implementation of `ZeroClipboard.off`.
 * @private
 */
  var _off = function(eventType, listener) {
    var i, len, foundIndex, events, perEventHandlers;
    if (arguments.length === 0) {
      events = _keys(_handlers);
    } else if (typeof eventType === "string" && eventType) {
      events = eventType.split(/\s+/);
    } else if (typeof eventType === "object" && eventType && typeof listener === "undefined") {
      for (i in eventType) {
        if (_hasOwn.call(eventType, i) && typeof i === "string" && i && typeof eventType[i] === "function") {
          ZeroClipboard.off(i, eventType[i]);
        }
      }
    }
    if (events && events.length) {
      for (i = 0, len = events.length; i < len; i++) {
        eventType = events[i].toLowerCase().replace(/^on/, "");
        perEventHandlers = _handlers[eventType];
        if (perEventHandlers && perEventHandlers.length) {
          if (listener) {
            foundIndex = perEventHandlers.indexOf(listener);
            while (foundIndex !== -1) {
              perEventHandlers.splice(foundIndex, 1);
              foundIndex = perEventHandlers.indexOf(listener, foundIndex);
            }
          } else {
            perEventHandlers.length = 0;
          }
        }
      }
    }
    return ZeroClipboard;
  };
  /**
 * The underlying implementation of `ZeroClipboard.handlers`.
 * @private
 */
  var _listeners = function(eventType) {
    var copy;
    if (typeof eventType === "string" && eventType) {
      copy = _deepCopy(_handlers[eventType]) || null;
    } else {
      copy = _deepCopy(_handlers);
    }
    return copy;
  };
  /**
 * The underlying implementation of `ZeroClipboard.emit`.
 * @private
 */
  var _emit = function(event) {
    var eventCopy, returnVal, tmp;
    event = _createEvent(event);
    if (!event) {
      return;
    }
    if (_preprocessEvent(event)) {
      return;
    }
    if (event.type === "ready" && _flashState.overdue === true) {
      return ZeroClipboard.emit({
        type: "error",
        name: "flash-overdue"
      });
    }
    eventCopy = _extend({}, event);
    _dispatchCallbacks.call(this, eventCopy);
    if (event.type === "copy") {
      tmp = _mapClipDataToFlash(_clipData);
      returnVal = tmp.data;
      _clipDataFormatMap = tmp.formatMap;
    }
    return returnVal;
  };
  /**
 * The underlying implementation of `ZeroClipboard.create`.
 * @private
 */
  var _create = function() {
    if (typeof _flashState.ready !== "boolean") {
      _flashState.ready = false;
    }
    if (!ZeroClipboard.isFlashUnusable() && _flashState.bridge === null) {
      var maxWait = _globalConfig.flashLoadTimeout;
      if (typeof maxWait === "number" && maxWait >= 0) {
        _setTimeout(function() {
          if (typeof _flashState.deactivated !== "boolean") {
            _flashState.deactivated = true;
          }
          if (_flashState.deactivated === true) {
            ZeroClipboard.emit({
              type: "error",
              name: "flash-deactivated"
            });
          }
        }, maxWait);
      }
      _flashState.overdue = false;
      _embedSwf();
    }
  };
  /**
 * The underlying implementation of `ZeroClipboard.destroy`.
 * @private
 */
  var _destroy = function() {
    ZeroClipboard.clearData();
    ZeroClipboard.blur();
    ZeroClipboard.emit("destroy");
    _unembedSwf();
    ZeroClipboard.off();
  };
  /**
 * The underlying implementation of `ZeroClipboard.setData`.
 * @private
 */
  var _setData = function(format, data) {
    var dataObj;
    if (typeof format === "object" && format && typeof data === "undefined") {
      dataObj = format;
      ZeroClipboard.clearData();
    } else if (typeof format === "string" && format) {
      dataObj = {};
      dataObj[format] = data;
    } else {
      return;
    }
    for (var dataFormat in dataObj) {
      if (typeof dataFormat === "string" && dataFormat && _hasOwn.call(dataObj, dataFormat) && typeof dataObj[dataFormat] === "string" && dataObj[dataFormat]) {
        _clipData[dataFormat] = dataObj[dataFormat];
      }
    }
  };
  /**
 * The underlying implementation of `ZeroClipboard.clearData`.
 * @private
 */
  var _clearData = function(format) {
    if (typeof format === "undefined") {
      _deleteOwnProperties(_clipData);
      _clipDataFormatMap = null;
    } else if (typeof format === "string" && _hasOwn.call(_clipData, format)) {
      delete _clipData[format];
    }
  };
  /**
 * The underlying implementation of `ZeroClipboard.getData`.
 * @private
 */
  var _getData = function(format) {
    if (typeof format === "undefined") {
      return _deepCopy(_clipData);
    } else if (typeof format === "string" && _hasOwn.call(_clipData, format)) {
      return _clipData[format];
    }
  };
  /**
 * The underlying implementation of `ZeroClipboard.focus`/`ZeroClipboard.activate`.
 * @private
 */
  var _focus = function(element) {
    if (!(element && element.nodeType === 1)) {
      return;
    }
    if (_currentElement) {
      _removeClass(_currentElement, _globalConfig.activeClass);
      if (_currentElement !== element) {
        _removeClass(_currentElement, _globalConfig.hoverClass);
      }
    }
    _currentElement = element;
    _addClass(element, _globalConfig.hoverClass);
    var newTitle = element.getAttribute("title") || _globalConfig.title;
    if (typeof newTitle === "string" && newTitle) {
      var htmlBridge = _getHtmlBridge(_flashState.bridge);
      if (htmlBridge) {
        htmlBridge.setAttribute("title", newTitle);
      }
    }
    var useHandCursor = _globalConfig.forceHandCursor === true || _getStyle(element, "cursor") === "pointer";
    _setHandCursor(useHandCursor);
    _reposition();
  };
  /**
 * The underlying implementation of `ZeroClipboard.blur`/`ZeroClipboard.deactivate`.
 * @private
 */
  var _blur = function() {
    var htmlBridge = _getHtmlBridge(_flashState.bridge);
    if (htmlBridge) {
      htmlBridge.removeAttribute("title");
      htmlBridge.style.left = "0px";
      htmlBridge.style.top = "-9999px";
      htmlBridge.style.width = "1px";
      htmlBridge.style.top = "1px";
    }
    if (_currentElement) {
      _removeClass(_currentElement, _globalConfig.hoverClass);
      _removeClass(_currentElement, _globalConfig.activeClass);
      _currentElement = null;
    }
  };
  /**
 * The underlying implementation of `ZeroClipboard.activeElement`.
 * @private
 */
  var _activeElement = function() {
    return _currentElement || null;
  };
  /**
 * Check if a value is a valid HTML4 `ID` or `Name` token.
 * @private
 */
  var _isValidHtml4Id = function(id) {
    return typeof id === "string" && id && /^[A-Za-z][A-Za-z0-9_:\-\.]*$/.test(id);
  };
  /**
 * Create or update an `event` object, based on the `eventType`.
 * @private
 */
  var _createEvent = function(event) {
    var eventType;
    if (typeof event === "string" && event) {
      eventType = event;
      event = {};
    } else if (typeof event === "object" && event && typeof event.type === "string" && event.type) {
      eventType = event.type;
    }
    if (!eventType) {
      return;
    }
    if (!event.target && /^(copy|aftercopy|_click)$/.test(eventType.toLowerCase())) {
      event.target = _copyTarget;
    }
    _extend(event, {
      type: eventType.toLowerCase(),
      target: event.target || _currentElement || null,
      relatedTarget: event.relatedTarget || null,
      currentTarget: _flashState && _flashState.bridge || null,
      timeStamp: event.timeStamp || _now() || null
    });
    var msg = _eventMessages[event.type];
    if (event.type === "error" && event.name && msg) {
      msg = msg[event.name];
    }
    if (msg) {
      event.message = msg;
    }
    if (event.type === "ready") {
      _extend(event, {
        target: null,
        version: _flashState.version
      });
    }
    if (event.type === "error") {
      if (/^flash-(disabled|outdated|unavailable|deactivated|overdue)$/.test(event.name)) {
        _extend(event, {
          target: null,
          minimumVersion: _minimumFlashVersion
        });
      }
      if (/^flash-(outdated|unavailable|deactivated|overdue)$/.test(event.name)) {
        _extend(event, {
          version: _flashState.version
        });
      }
    }
    if (event.type === "copy") {
      event.clipboardData = {
        setData: ZeroClipboard.setData,
        clearData: ZeroClipboard.clearData
      };
    }
    if (event.type === "aftercopy") {
      event = _mapClipResultsFromFlash(event, _clipDataFormatMap);
    }
    if (event.target && !event.relatedTarget) {
      event.relatedTarget = _getRelatedTarget(event.target);
    }
    event = _addMouseData(event);
    return event;
  };
  /**
 * Get a relatedTarget from the target's `data-clipboard-target` attribute
 * @private
 */
  var _getRelatedTarget = function(targetEl) {
    var relatedTargetId = targetEl && targetEl.getAttribute && targetEl.getAttribute("data-clipboard-target");
    return relatedTargetId ? _document.getElementById(relatedTargetId) : null;
  };
  /**
 * Add element and position data to `MouseEvent` instances
 * @private
 */
  var _addMouseData = function(event) {
    if (event && /^_(?:click|mouse(?:over|out|down|up|move))$/.test(event.type)) {
      var srcElement = event.target;
      var fromElement = event.type === "_mouseover" && event.relatedTarget ? event.relatedTarget : undefined;
      var toElement = event.type === "_mouseout" && event.relatedTarget ? event.relatedTarget : undefined;
      var pos = _getDOMObjectPosition(srcElement);
      var screenLeft = _window.screenLeft || _window.screenX || 0;
      var screenTop = _window.screenTop || _window.screenY || 0;
      var scrollLeft = _document.body.scrollLeft + _document.documentElement.scrollLeft;
      var scrollTop = _document.body.scrollTop + _document.documentElement.scrollTop;
      var pageX = pos.left + (typeof event._stageX === "number" ? event._stageX : 0);
      var pageY = pos.top + (typeof event._stageY === "number" ? event._stageY : 0);
      var clientX = pageX - scrollLeft;
      var clientY = pageY - scrollTop;
      var screenX = screenLeft + clientX;
      var screenY = screenTop + clientY;
      var moveX = typeof event.movementX === "number" ? event.movementX : 0;
      var moveY = typeof event.movementY === "number" ? event.movementY : 0;
      delete event._stageX;
      delete event._stageY;
      _extend(event, {
        srcElement: srcElement,
        fromElement: fromElement,
        toElement: toElement,
        screenX: screenX,
        screenY: screenY,
        pageX: pageX,
        pageY: pageY,
        clientX: clientX,
        clientY: clientY,
        x: clientX,
        y: clientY,
        movementX: moveX,
        movementY: moveY,
        offsetX: 0,
        offsetY: 0,
        layerX: 0,
        layerY: 0
      });
    }
    return event;
  };
  /**
 * Determine if an event's registered handlers should be execute synchronously or asynchronously.
 *
 * @returns {boolean}
 * @private
 */
  var _shouldPerformAsync = function(event) {
    var eventType = event && typeof event.type === "string" && event.type || "";
    return !/^(?:(?:before)?copy|destroy)$/.test(eventType);
  };
  /**
 * Control if a callback should be executed asynchronously or not.
 *
 * @returns `undefined`
 * @private
 */
  var _dispatchCallback = function(func, context, args, async) {
    if (async) {
      _setTimeout(function() {
        func.apply(context, args);
      }, 0);
    } else {
      func.apply(context, args);
    }
  };
  /**
 * Handle the actual dispatching of events to client instances.
 *
 * @returns `undefined`
 * @private
 */
  var _dispatchCallbacks = function(event) {
    if (!(typeof event === "object" && event && event.type)) {
      return;
    }
    var async = _shouldPerformAsync(event);
    var wildcardTypeHandlers = _handlers["*"] || [];
    var specificTypeHandlers = _handlers[event.type] || [];
    var handlers = wildcardTypeHandlers.concat(specificTypeHandlers);
    if (handlers && handlers.length) {
      var i, len, func, context, eventCopy, originalContext = this;
      for (i = 0, len = handlers.length; i < len; i++) {
        func = handlers[i];
        context = originalContext;
        if (typeof func === "string" && typeof _window[func] === "function") {
          func = _window[func];
        }
        if (typeof func === "object" && func && typeof func.handleEvent === "function") {
          context = func;
          func = func.handleEvent;
        }
        if (typeof func === "function") {
          eventCopy = _extend({}, event);
          _dispatchCallback(func, context, [ eventCopy ], async);
        }
      }
    }
    return this;
  };
  /**
 * Preprocess any special behaviors, reactions, or state changes after receiving this event.
 * Executes only once per event emitted, NOT once per client.
 * @private
 */
  var _preprocessEvent = function(event) {
    var element = event.target || _currentElement || null;
    var sourceIsSwf = event._source === "swf";
    delete event._source;
    var flashErrorNames = [ "flash-disabled", "flash-outdated", "flash-unavailable", "flash-deactivated", "flash-overdue" ];
    switch (event.type) {
     case "error":
      if (flashErrorNames.indexOf(event.name) !== -1) {
        _extend(_flashState, {
          disabled: event.name === "flash-disabled",
          outdated: event.name === "flash-outdated",
          unavailable: event.name === "flash-unavailable",
          deactivated: event.name === "flash-deactivated",
          overdue: event.name === "flash-overdue",
          ready: false
        });
      }
      break;

     case "ready":
      var wasDeactivated = _flashState.deactivated === true;
      _extend(_flashState, {
        disabled: false,
        outdated: false,
        unavailable: false,
        deactivated: false,
        overdue: wasDeactivated,
        ready: !wasDeactivated
      });
      break;

     case "beforecopy":
      _copyTarget = element;
      break;

     case "copy":
      var textContent, htmlContent, targetEl = event.relatedTarget;
      if (!(_clipData["text/html"] || _clipData["text/plain"]) && targetEl && (htmlContent = targetEl.value || targetEl.outerHTML || targetEl.innerHTML) && (textContent = targetEl.value || targetEl.textContent || targetEl.innerText)) {
        event.clipboardData.clearData();
        event.clipboardData.setData("text/plain", textContent);
        if (htmlContent !== textContent) {
          event.clipboardData.setData("text/html", htmlContent);
        }
      } else if (!_clipData["text/plain"] && event.target && (textContent = event.target.getAttribute("data-clipboard-text"))) {
        event.clipboardData.clearData();
        event.clipboardData.setData("text/plain", textContent);
      }
      break;

     case "aftercopy":
      ZeroClipboard.clearData();
      if (element && element !== _safeActiveElement() && element.focus) {
        element.focus();
      }
      break;

     case "_mouseover":
      ZeroClipboard.focus(element);
      if (_globalConfig.bubbleEvents === true && sourceIsSwf) {
        if (element && element !== event.relatedTarget && !_containedBy(event.relatedTarget, element)) {
          _fireMouseEvent(_extend({}, event, {
            type: "mouseenter",
            bubbles: false,
            cancelable: false
          }));
        }
        _fireMouseEvent(_extend({}, event, {
          type: "mouseover"
        }));
      }
      break;

     case "_mouseout":
      ZeroClipboard.blur();
      if (_globalConfig.bubbleEvents === true && sourceIsSwf) {
        if (element && element !== event.relatedTarget && !_containedBy(event.relatedTarget, element)) {
          _fireMouseEvent(_extend({}, event, {
            type: "mouseleave",
            bubbles: false,
            cancelable: false
          }));
        }
        _fireMouseEvent(_extend({}, event, {
          type: "mouseout"
        }));
      }
      break;

     case "_mousedown":
      _addClass(element, _globalConfig.activeClass);
      if (_globalConfig.bubbleEvents === true && sourceIsSwf) {
        _fireMouseEvent(_extend({}, event, {
          type: event.type.slice(1)
        }));
      }
      break;

     case "_mouseup":
      _removeClass(element, _globalConfig.activeClass);
      if (_globalConfig.bubbleEvents === true && sourceIsSwf) {
        _fireMouseEvent(_extend({}, event, {
          type: event.type.slice(1)
        }));
      }
      break;

     case "_click":
      _copyTarget = null;
      if (_globalConfig.bubbleEvents === true && sourceIsSwf) {
        _fireMouseEvent(_extend({}, event, {
          type: event.type.slice(1)
        }));
      }
      break;

     case "_mousemove":
      if (_globalConfig.bubbleEvents === true && sourceIsSwf) {
        _fireMouseEvent(_extend({}, event, {
          type: event.type.slice(1)
        }));
      }
      break;
    }
    if (/^_(?:click|mouse(?:over|out|down|up|move))$/.test(event.type)) {
      return true;
    }
  };
  /**
 * Dispatch a synthetic MouseEvent.
 *
 * @returns `undefined`
 * @private
 */
  var _fireMouseEvent = function(event) {
    if (!(event && typeof event.type === "string" && event)) {
      return;
    }
    var e, target = event.target || null, doc = target && target.ownerDocument || _document, defaults = {
      view: doc.defaultView || _window,
      canBubble: true,
      cancelable: true,
      detail: event.type === "click" ? 1 : 0,
      button: typeof event.which === "number" ? event.which - 1 : typeof event.button === "number" ? event.button : doc.createEvent ? 0 : 1
    }, args = _extend(defaults, event);
    if (!target) {
      return;
    }
    if (doc.createEvent && target.dispatchEvent) {
      args = [ args.type, args.canBubble, args.cancelable, args.view, args.detail, args.screenX, args.screenY, args.clientX, args.clientY, args.ctrlKey, args.altKey, args.shiftKey, args.metaKey, args.button, args.relatedTarget ];
      e = doc.createEvent("MouseEvents");
      if (e.initMouseEvent) {
        e.initMouseEvent.apply(e, args);
        e._source = "js";
        target.dispatchEvent(e);
      }
    }
  };
  /**
 * Create the HTML bridge element to embed the Flash object into.
 * @private
 */
  var _createHtmlBridge = function() {
    var container = _document.createElement("div");
    container.id = _globalConfig.containerId;
    container.className = _globalConfig.containerClass;
    container.style.position = "absolute";
    container.style.left = "0px";
    container.style.top = "-9999px";
    container.style.width = "1px";
    container.style.height = "1px";
    container.style.zIndex = "" + _getSafeZIndex(_globalConfig.zIndex);
    return container;
  };
  /**
 * Get the HTML element container that wraps the Flash bridge object/element.
 * @private
 */
  var _getHtmlBridge = function(flashBridge) {
    var htmlBridge = flashBridge && flashBridge.parentNode;
    while (htmlBridge && htmlBridge.nodeName === "OBJECT" && htmlBridge.parentNode) {
      htmlBridge = htmlBridge.parentNode;
    }
    return htmlBridge || null;
  };
  /**
 * Create the SWF object.
 *
 * @returns The SWF object reference.
 * @private
 */
  var _embedSwf = function() {
    var len, flashBridge = _flashState.bridge, container = _getHtmlBridge(flashBridge);
    if (!flashBridge) {
      var allowScriptAccess = _determineScriptAccess(_window.location.host, _globalConfig);
      var allowNetworking = allowScriptAccess === "never" ? "none" : "all";
      var flashvars = _vars(_globalConfig);
      var swfUrl = _globalConfig.swfPath + _cacheBust(_globalConfig.swfPath, _globalConfig);
      container = _createHtmlBridge();
      var divToBeReplaced = _document.createElement("div");
      container.appendChild(divToBeReplaced);
      _document.body.appendChild(container);
      var tmpDiv = _document.createElement("div");
      var oldIE = _flashState.pluginType === "activex";
      tmpDiv.innerHTML = '<object id="' + _globalConfig.swfObjectId + '" name="' + _globalConfig.swfObjectId + '" ' + 'width="100%" height="100%" ' + (oldIE ? 'classid="clsid:d27cdb6e-ae6d-11cf-96b8-444553540000"' : 'type="application/x-shockwave-flash" data="' + swfUrl + '"') + ">" + (oldIE ? '<param name="movie" value="' + swfUrl + '"/>' : "") + '<param name="allowScriptAccess" value="' + allowScriptAccess + '"/>' + '<param name="allowNetworking" value="' + allowNetworking + '"/>' + '<param name="menu" value="false"/>' + '<param name="wmode" value="transparent"/>' + '<param name="flashvars" value="' + flashvars + '"/>' + "</object>";
      flashBridge = tmpDiv.firstChild;
      tmpDiv = null;
      _unwrap(flashBridge).ZeroClipboard = ZeroClipboard;
      container.replaceChild(flashBridge, divToBeReplaced);
    }
    if (!flashBridge) {
      flashBridge = _document[_globalConfig.swfObjectId];
      if (flashBridge && (len = flashBridge.length)) {
        flashBridge = flashBridge[len - 1];
      }
      if (!flashBridge && container) {
        flashBridge = container.firstChild;
      }
    }
    _flashState.bridge = flashBridge || null;
    return flashBridge;
  };
  /**
 * Destroy the SWF object.
 * @private
 */
  var _unembedSwf = function() {
    var flashBridge = _flashState.bridge;
    if (flashBridge) {
      var htmlBridge = _getHtmlBridge(flashBridge);
      if (htmlBridge) {
        if (_flashState.pluginType === "activex" && "readyState" in flashBridge) {
          flashBridge.style.display = "none";
          (function removeSwfFromIE() {
            if (flashBridge.readyState === 4) {
              for (var prop in flashBridge) {
                if (typeof flashBridge[prop] === "function") {
                  flashBridge[prop] = null;
                }
              }
              if (flashBridge.parentNode) {
                flashBridge.parentNode.removeChild(flashBridge);
              }
              if (htmlBridge.parentNode) {
                htmlBridge.parentNode.removeChild(htmlBridge);
              }
            } else {
              _setTimeout(removeSwfFromIE, 10);
            }
          })();
        } else {
          if (flashBridge.parentNode) {
            flashBridge.parentNode.removeChild(flashBridge);
          }
          if (htmlBridge.parentNode) {
            htmlBridge.parentNode.removeChild(htmlBridge);
          }
        }
      }
      _flashState.ready = null;
      _flashState.bridge = null;
      _flashState.deactivated = null;
    }
  };
  /**
 * Map the data format names of the "clipData" to Flash-friendly names.
 *
 * @returns A new transformed object.
 * @private
 */
  var _mapClipDataToFlash = function(clipData) {
    var newClipData = {}, formatMap = {};
    if (!(typeof clipData === "object" && clipData)) {
      return;
    }
    for (var dataFormat in clipData) {
      if (dataFormat && _hasOwn.call(clipData, dataFormat) && typeof clipData[dataFormat] === "string" && clipData[dataFormat]) {
        switch (dataFormat.toLowerCase()) {
         case "text/plain":
         case "text":
         case "air:text":
         case "flash:text":
          newClipData.text = clipData[dataFormat];
          formatMap.text = dataFormat;
          break;

         case "text/html":
         case "html":
         case "air:html":
         case "flash:html":
          newClipData.html = clipData[dataFormat];
          formatMap.html = dataFormat;
          break;

         case "application/rtf":
         case "text/rtf":
         case "rtf":
         case "richtext":
         case "air:rtf":
         case "flash:rtf":
          newClipData.rtf = clipData[dataFormat];
          formatMap.rtf = dataFormat;
          break;

         default:
          break;
        }
      }
    }
    return {
      data: newClipData,
      formatMap: formatMap
    };
  };
  /**
 * Map the data format names from Flash-friendly names back to their original "clipData" names (via a format mapping).
 *
 * @returns A new transformed object.
 * @private
 */
  var _mapClipResultsFromFlash = function(clipResults, formatMap) {
    if (!(typeof clipResults === "object" && clipResults && typeof formatMap === "object" && formatMap)) {
      return clipResults;
    }
    var newResults = {};
    for (var prop in clipResults) {
      if (_hasOwn.call(clipResults, prop)) {
        if (prop !== "success" && prop !== "data") {
          newResults[prop] = clipResults[prop];
          continue;
        }
        newResults[prop] = {};
        var tmpHash = clipResults[prop];
        for (var dataFormat in tmpHash) {
          if (dataFormat && _hasOwn.call(tmpHash, dataFormat) && _hasOwn.call(formatMap, dataFormat)) {
            newResults[prop][formatMap[dataFormat]] = tmpHash[dataFormat];
          }
        }
      }
    }
    return newResults;
  };
  /**
 * Will look at a path, and will create a "?noCache={time}" or "&noCache={time}"
 * query param string to return. Does NOT append that string to the original path.
 * This is useful because ExternalInterface often breaks when a Flash SWF is cached.
 *
 * @returns The `noCache` query param with necessary "?"/"&" prefix.
 * @private
 */
  var _cacheBust = function(path, options) {
    var cacheBust = options == null || options && options.cacheBust === true;
    if (cacheBust) {
      return (path.indexOf("?") === -1 ? "?" : "&") + "noCache=" + _now();
    } else {
      return "";
    }
  };
  /**
 * Creates a query string for the FlashVars param.
 * Does NOT include the cache-busting query param.
 *
 * @returns FlashVars query string
 * @private
 */
  var _vars = function(options) {
    var i, len, domain, domains, str = "", trustedOriginsExpanded = [];
    if (options.trustedDomains) {
      if (typeof options.trustedDomains === "string") {
        domains = [ options.trustedDomains ];
      } else if (typeof options.trustedDomains === "object" && "length" in options.trustedDomains) {
        domains = options.trustedDomains;
      }
    }
    if (domains && domains.length) {
      for (i = 0, len = domains.length; i < len; i++) {
        if (_hasOwn.call(domains, i) && domains[i] && typeof domains[i] === "string") {
          domain = _extractDomain(domains[i]);
          if (!domain) {
            continue;
          }
          if (domain === "*") {
            trustedOriginsExpanded.length = 0;
            trustedOriginsExpanded.push(domain);
            break;
          }
          trustedOriginsExpanded.push.apply(trustedOriginsExpanded, [ domain, "//" + domain, _window.location.protocol + "//" + domain ]);
        }
      }
    }
    if (trustedOriginsExpanded.length) {
      str += "trustedOrigins=" + _encodeURIComponent(trustedOriginsExpanded.join(","));
    }
    if (options.forceEnhancedClipboard === true) {
      str += (str ? "&" : "") + "forceEnhancedClipboard=true";
    }
    if (typeof options.swfObjectId === "string" && options.swfObjectId) {
      str += (str ? "&" : "") + "swfObjectId=" + _encodeURIComponent(options.swfObjectId);
    }
    return str;
  };
  /**
 * Extract the domain (e.g. "github.com") from an origin (e.g. "https://github.com") or
 * URL (e.g. "https://github.com/zeroclipboard/zeroclipboard/").
 *
 * @returns the domain
 * @private
 */
  var _extractDomain = function(originOrUrl) {
    if (originOrUrl == null || originOrUrl === "") {
      return null;
    }
    originOrUrl = originOrUrl.replace(/^\s+|\s+$/g, "");
    if (originOrUrl === "") {
      return null;
    }
    var protocolIndex = originOrUrl.indexOf("//");
    originOrUrl = protocolIndex === -1 ? originOrUrl : originOrUrl.slice(protocolIndex + 2);
    var pathIndex = originOrUrl.indexOf("/");
    originOrUrl = pathIndex === -1 ? originOrUrl : protocolIndex === -1 || pathIndex === 0 ? null : originOrUrl.slice(0, pathIndex);
    if (originOrUrl && originOrUrl.slice(-4).toLowerCase() === ".swf") {
      return null;
    }
    return originOrUrl || null;
  };
  /**
 * Set `allowScriptAccess` based on `trustedDomains` and `window.location.host` vs. `swfPath`.
 *
 * @returns The appropriate script access level.
 * @private
 */
  var _determineScriptAccess = function() {
    var _extractAllDomains = function(origins) {
      var i, len, tmp, resultsArray = [];
      if (typeof origins === "string") {
        origins = [ origins ];
      }
      if (!(typeof origins === "object" && origins && typeof origins.length === "number")) {
        return resultsArray;
      }
      for (i = 0, len = origins.length; i < len; i++) {
        if (_hasOwn.call(origins, i) && (tmp = _extractDomain(origins[i]))) {
          if (tmp === "*") {
            resultsArray.length = 0;
            resultsArray.push("*");
            break;
          }
          if (resultsArray.indexOf(tmp) === -1) {
            resultsArray.push(tmp);
          }
        }
      }
      return resultsArray;
    };
    return function(currentDomain, configOptions) {
      var swfDomain = _extractDomain(configOptions.swfPath);
      if (swfDomain === null) {
        swfDomain = currentDomain;
      }
      var trustedDomains = _extractAllDomains(configOptions.trustedDomains);
      var len = trustedDomains.length;
      if (len > 0) {
        if (len === 1 && trustedDomains[0] === "*") {
          return "always";
        }
        if (trustedDomains.indexOf(currentDomain) !== -1) {
          if (len === 1 && currentDomain === swfDomain) {
            return "sameDomain";
          }
          return "always";
        }
      }
      return "never";
    };
  }();
  /**
 * Get the currently active/focused DOM element.
 *
 * @returns the currently active/focused element, or `null`
 * @private
 */
  var _safeActiveElement = function() {
    try {
      return _document.activeElement;
    } catch (err) {
      return null;
    }
  };
  /**
 * Add a class to an element, if it doesn't already have it.
 *
 * @returns The element, with its new class added.
 * @private
 */
  var _addClass = function(element, value) {
    if (!element || element.nodeType !== 1) {
      return element;
    }
    if (element.classList) {
      if (!element.classList.contains(value)) {
        element.classList.add(value);
      }
      return element;
    }
    if (value && typeof value === "string") {
      var classNames = (value || "").split(/\s+/);
      if (element.nodeType === 1) {
        if (!element.className) {
          element.className = value;
        } else {
          var className = " " + element.className + " ", setClass = element.className;
          for (var c = 0, cl = classNames.length; c < cl; c++) {
            if (className.indexOf(" " + classNames[c] + " ") < 0) {
              setClass += " " + classNames[c];
            }
          }
          element.className = setClass.replace(/^\s+|\s+$/g, "");
        }
      }
    }
    return element;
  };
  /**
 * Remove a class from an element, if it has it.
 *
 * @returns The element, with its class removed.
 * @private
 */
  var _removeClass = function(element, value) {
    if (!element || element.nodeType !== 1) {
      return element;
    }
    if (element.classList) {
      if (element.classList.contains(value)) {
        element.classList.remove(value);
      }
      return element;
    }
    if (typeof value === "string" && value) {
      var classNames = value.split(/\s+/);
      if (element.nodeType === 1 && element.className) {
        var className = (" " + element.className + " ").replace(/[\n\t]/g, " ");
        for (var c = 0, cl = classNames.length; c < cl; c++) {
          className = className.replace(" " + classNames[c] + " ", " ");
        }
        element.className = className.replace(/^\s+|\s+$/g, "");
      }
    }
    return element;
  };
  /**
 * Attempt to interpret the element's CSS styling. If `prop` is `"cursor"`,
 * then we assume that it should be a hand ("pointer") cursor if the element
 * is an anchor element ("a" tag).
 *
 * @returns The computed style property.
 * @private
 */
  var _getStyle = function(el, prop) {
    var value = _window.getComputedStyle(el, null).getPropertyValue(prop);
    if (prop === "cursor") {
      if (!value || value === "auto") {
        if (el.nodeName === "A") {
          return "pointer";
        }
      }
    }
    return value;
  };
  /**
 * Get the zoom factor of the browser. Always returns `1.0`, except at
 * non-default zoom levels in IE<8 and some older versions of WebKit.
 *
 * @returns Floating unit percentage of the zoom factor (e.g. 150% = `1.5`).
 * @private
 */
  var _getZoomFactor = function() {
    var rect, physicalWidth, logicalWidth, zoomFactor = 1;
    if (typeof _document.body.getBoundingClientRect === "function") {
      rect = _document.body.getBoundingClientRect();
      physicalWidth = rect.right - rect.left;
      logicalWidth = _document.body.offsetWidth;
      zoomFactor = _round(physicalWidth / logicalWidth * 100) / 100;
    }
    return zoomFactor;
  };
  /**
 * Get the DOM positioning info of an element.
 *
 * @returns Object containing the element's position, width, and height.
 * @private
 */
  var _getDOMObjectPosition = function(obj) {
    var info = {
      left: 0,
      top: 0,
      width: 0,
      height: 0
    };
    if (obj.getBoundingClientRect) {
      var rect = obj.getBoundingClientRect();
      var pageXOffset, pageYOffset, zoomFactor;
      if ("pageXOffset" in _window && "pageYOffset" in _window) {
        pageXOffset = _window.pageXOffset;
        pageYOffset = _window.pageYOffset;
      } else {
        zoomFactor = _getZoomFactor();
        pageXOffset = _round(_document.documentElement.scrollLeft / zoomFactor);
        pageYOffset = _round(_document.documentElement.scrollTop / zoomFactor);
      }
      var leftBorderWidth = _document.documentElement.clientLeft || 0;
      var topBorderWidth = _document.documentElement.clientTop || 0;
      info.left = rect.left + pageXOffset - leftBorderWidth;
      info.top = rect.top + pageYOffset - topBorderWidth;
      info.width = "width" in rect ? rect.width : rect.right - rect.left;
      info.height = "height" in rect ? rect.height : rect.bottom - rect.top;
    }
    return info;
  };
  /**
 * Reposition the Flash object to cover the currently activated element.
 *
 * @returns `undefined`
 * @private
 */
  var _reposition = function() {
    var htmlBridge;
    if (_currentElement && (htmlBridge = _getHtmlBridge(_flashState.bridge))) {
      var pos = _getDOMObjectPosition(_currentElement);
      _extend(htmlBridge.style, {
        width: pos.width + "px",
        height: pos.height + "px",
        top: pos.top + "px",
        left: pos.left + "px",
        zIndex: "" + _getSafeZIndex(_globalConfig.zIndex)
      });
    }
  };
  /**
 * Sends a signal to the Flash object to display the hand cursor if `true`.
 *
 * @returns `undefined`
 * @private
 */
  var _setHandCursor = function(enabled) {
    if (_flashState.ready === true) {
      if (_flashState.bridge && typeof _flashState.bridge.setHandCursor === "function") {
        _flashState.bridge.setHandCursor(enabled);
      } else {
        _flashState.ready = false;
      }
    }
  };
  /**
 * Get a safe value for `zIndex`
 *
 * @returns an integer, or "auto"
 * @private
 */
  var _getSafeZIndex = function(val) {
    if (/^(?:auto|inherit)$/.test(val)) {
      return val;
    }
    var zIndex;
    if (typeof val === "number" && !_isNaN(val)) {
      zIndex = val;
    } else if (typeof val === "string") {
      zIndex = _getSafeZIndex(_parseInt(val, 10));
    }
    return typeof zIndex === "number" ? zIndex : "auto";
  };
  /**
 * Detect the Flash Player status, version, and plugin type.
 *
 * @see {@link https://code.google.com/p/doctype-mirror/wiki/ArticleDetectFlash#The_code}
 * @see {@link http://stackoverflow.com/questions/12866060/detecting-pepper-ppapi-flash-with-javascript}
 *
 * @returns `undefined`
 * @private
 */
  var _detectFlashSupport = function(ActiveXObject) {
    var plugin, ax, mimeType, hasFlash = false, isActiveX = false, isPPAPI = false, flashVersion = "";
    /**
   * Derived from Apple's suggested sniffer.
   * @param {String} desc e.g. "Shockwave Flash 7.0 r61"
   * @returns {String} "7.0.61"
   * @private
   */
    function parseFlashVersion(desc) {
      var matches = desc.match(/[\d]+/g);
      matches.length = 3;
      return matches.join(".");
    }
    function isPepperFlash(flashPlayerFileName) {
      return !!flashPlayerFileName && (flashPlayerFileName = flashPlayerFileName.toLowerCase()) && (/^(pepflashplayer\.dll|libpepflashplayer\.so|pepperflashplayer\.plugin)$/.test(flashPlayerFileName) || flashPlayerFileName.slice(-13) === "chrome.plugin");
    }
    function inspectPlugin(plugin) {
      if (plugin) {
        hasFlash = true;
        if (plugin.version) {
          flashVersion = parseFlashVersion(plugin.version);
        }
        if (!flashVersion && plugin.description) {
          flashVersion = parseFlashVersion(plugin.description);
        }
        if (plugin.filename) {
          isPPAPI = isPepperFlash(plugin.filename);
        }
      }
    }
    if (_navigator.plugins && _navigator.plugins.length) {
      plugin = _navigator.plugins["Shockwave Flash"];
      inspectPlugin(plugin);
      if (_navigator.plugins["Shockwave Flash 2.0"]) {
        hasFlash = true;
        flashVersion = "2.0.0.11";
      }
    } else if (_navigator.mimeTypes && _navigator.mimeTypes.length) {
      mimeType = _navigator.mimeTypes["application/x-shockwave-flash"];
      plugin = mimeType && mimeType.enabledPlugin;
      inspectPlugin(plugin);
    } else if (typeof ActiveXObject !== "undefined") {
      isActiveX = true;
      try {
        ax = new ActiveXObject("ShockwaveFlash.ShockwaveFlash.7");
        hasFlash = true;
        flashVersion = parseFlashVersion(ax.GetVariable("$version"));
      } catch (e1) {
        try {
          ax = new ActiveXObject("ShockwaveFlash.ShockwaveFlash.6");
          hasFlash = true;
          flashVersion = "6.0.21";
        } catch (e2) {
          try {
            ax = new ActiveXObject("ShockwaveFlash.ShockwaveFlash");
            hasFlash = true;
            flashVersion = parseFlashVersion(ax.GetVariable("$version"));
          } catch (e3) {
            isActiveX = false;
          }
        }
      }
    }
    _flashState.disabled = hasFlash !== true;
    _flashState.outdated = flashVersion && _parseFloat(flashVersion) < _parseFloat(_minimumFlashVersion);
    _flashState.version = flashVersion || "0.0.0";
    _flashState.pluginType = isPPAPI ? "pepper" : isActiveX ? "activex" : hasFlash ? "netscape" : "unknown";
  };
  /**
 * Invoke the Flash detection algorithms immediately upon inclusion so we're not waiting later.
 */
  _detectFlashSupport(_ActiveXObject);
  /**
 * A shell constructor for `ZeroClipboard` client instances.
 *
 * @constructor
 */
  var ZeroClipboard = function() {
    if (!(this instanceof ZeroClipboard)) {
      return new ZeroClipboard();
    }
    if (typeof ZeroClipboard._createClient === "function") {
      ZeroClipboard._createClient.apply(this, _args(arguments));
    }
  };
  /**
 * The ZeroClipboard library's version number.
 *
 * @static
 * @readonly
 * @property {string}
 */
  _defineProperty(ZeroClipboard, "version", {
    value: "2.1.6",
    writable: false,
    configurable: true,
    enumerable: true
  });
  /**
 * Update or get a copy of the ZeroClipboard global configuration.
 * Returns a copy of the current/updated configuration.
 *
 * @returns Object
 * @static
 */
  ZeroClipboard.config = function() {
    return _config.apply(this, _args(arguments));
  };
  /**
 * Diagnostic method that describes the state of the browser, Flash Player, and ZeroClipboard.
 *
 * @returns Object
 * @static
 */
  ZeroClipboard.state = function() {
    return _state.apply(this, _args(arguments));
  };
  /**
 * Check if Flash is unusable for any reason: disabled, outdated, deactivated, etc.
 *
 * @returns Boolean
 * @static
 */
  ZeroClipboard.isFlashUnusable = function() {
    return _isFlashUnusable.apply(this, _args(arguments));
  };
  /**
 * Register an event listener.
 *
 * @returns `ZeroClipboard`
 * @static
 */
  ZeroClipboard.on = function() {
    return _on.apply(this, _args(arguments));
  };
  /**
 * Unregister an event listener.
 * If no `listener` function/object is provided, it will unregister all listeners for the provided `eventType`.
 * If no `eventType` is provided, it will unregister all listeners for every event type.
 *
 * @returns `ZeroClipboard`
 * @static
 */
  ZeroClipboard.off = function() {
    return _off.apply(this, _args(arguments));
  };
  /**
 * Retrieve event listeners for an `eventType`.
 * If no `eventType` is provided, it will retrieve all listeners for every event type.
 *
 * @returns array of listeners for the `eventType`; if no `eventType`, then a map/hash object of listeners for all event types; or `null`
 */
  ZeroClipboard.handlers = function() {
    return _listeners.apply(this, _args(arguments));
  };
  /**
 * Event emission receiver from the Flash object, forwarding to any registered JavaScript event listeners.
 *
 * @returns For the "copy" event, returns the Flash-friendly "clipData" object; otherwise `undefined`.
 * @static
 */
  ZeroClipboard.emit = function() {
    return _emit.apply(this, _args(arguments));
  };
  /**
 * Create and embed the Flash object.
 *
 * @returns The Flash object
 * @static
 */
  ZeroClipboard.create = function() {
    return _create.apply(this, _args(arguments));
  };
  /**
 * Self-destruct and clean up everything, including the embedded Flash object.
 *
 * @returns `undefined`
 * @static
 */
  ZeroClipboard.destroy = function() {
    return _destroy.apply(this, _args(arguments));
  };
  /**
 * Set the pending data for clipboard injection.
 *
 * @returns `undefined`
 * @static
 */
  ZeroClipboard.setData = function() {
    return _setData.apply(this, _args(arguments));
  };
  /**
 * Clear the pending data for clipboard injection.
 * If no `format` is provided, all pending data formats will be cleared.
 *
 * @returns `undefined`
 * @static
 */
  ZeroClipboard.clearData = function() {
    return _clearData.apply(this, _args(arguments));
  };
  /**
 * Get a copy of the pending data for clipboard injection.
 * If no `format` is provided, a copy of ALL pending data formats will be returned.
 *
 * @returns `String` or `Object`
 * @static
 */
  ZeroClipboard.getData = function() {
    return _getData.apply(this, _args(arguments));
  };
  /**
 * Sets the current HTML object that the Flash object should overlay. This will put the global
 * Flash object on top of the current element; depending on the setup, this may also set the
 * pending clipboard text data as well as the Flash object's wrapping element's title attribute
 * based on the underlying HTML element and ZeroClipboard configuration.
 *
 * @returns `undefined`
 * @static
 */
  ZeroClipboard.focus = ZeroClipboard.activate = function() {
    return _focus.apply(this, _args(arguments));
  };
  /**
 * Un-overlays the Flash object. This will put the global Flash object off-screen; depending on
 * the setup, this may also unset the Flash object's wrapping element's title attribute based on
 * the underlying HTML element and ZeroClipboard configuration.
 *
 * @returns `undefined`
 * @static
 */
  ZeroClipboard.blur = ZeroClipboard.deactivate = function() {
    return _blur.apply(this, _args(arguments));
  };
  /**
 * Returns the currently focused/"activated" HTML element that the Flash object is wrapping.
 *
 * @returns `HTMLElement` or `null`
 * @static
 */
  ZeroClipboard.activeElement = function() {
    return _activeElement.apply(this, _args(arguments));
  };
  /**
 * Keep track of the ZeroClipboard client instance counter.
 */
  var _clientIdCounter = 0;
  /**
 * Keep track of the state of the client instances.
 *
 * Entry structure:
 *   _clientMeta[client.id] = {
 *     instance: client,
 *     elements: [],
 *     handlers: {}
 *   };
 */
  var _clientMeta = {};
  /**
 * Keep track of the ZeroClipboard clipped elements counter.
 */
  var _elementIdCounter = 0;
  /**
 * Keep track of the state of the clipped element relationships to clients.
 *
 * Entry structure:
 *   _elementMeta[element.zcClippingId] = [client1.id, client2.id];
 */
  var _elementMeta = {};
  /**
 * Keep track of the state of the mouse event handlers for clipped elements.
 *
 * Entry structure:
 *   _mouseHandlers[element.zcClippingId] = {
 *     mouseover:  function(event) {},
 *     mouseout:   function(event) {},
 *     mouseenter: function(event) {},
 *     mouseleave: function(event) {},
 *     mousemove:  function(event) {}
 *   };
 */
  var _mouseHandlers = {};
  /**
 * Extending the ZeroClipboard configuration defaults for the Client module.
 */
  _extend(_globalConfig, {
    autoActivate: true
  });
  /**
 * The real constructor for `ZeroClipboard` client instances.
 * @private
 */
  var _clientConstructor = function(elements) {
    var client = this;
    client.id = "" + _clientIdCounter++;
    _clientMeta[client.id] = {
      instance: client,
      elements: [],
      handlers: {}
    };
    if (elements) {
      client.clip(elements);
    }
    ZeroClipboard.on("*", function(event) {
      return client.emit(event);
    });
    ZeroClipboard.on("destroy", function() {
      client.destroy();
    });
    ZeroClipboard.create();
  };
  /**
 * The underlying implementation of `ZeroClipboard.Client.prototype.on`.
 * @private
 */
  var _clientOn = function(eventType, listener) {
    var i, len, events, added = {}, handlers = _clientMeta[this.id] && _clientMeta[this.id].handlers;
    if (typeof eventType === "string" && eventType) {
      events = eventType.toLowerCase().split(/\s+/);
    } else if (typeof eventType === "object" && eventType && typeof listener === "undefined") {
      for (i in eventType) {
        if (_hasOwn.call(eventType, i) && typeof i === "string" && i && typeof eventType[i] === "function") {
          this.on(i, eventType[i]);
        }
      }
    }
    if (events && events.length) {
      for (i = 0, len = events.length; i < len; i++) {
        eventType = events[i].replace(/^on/, "");
        added[eventType] = true;
        if (!handlers[eventType]) {
          handlers[eventType] = [];
        }
        handlers[eventType].push(listener);
      }
      if (added.ready && _flashState.ready) {
        this.emit({
          type: "ready",
          client: this
        });
      }
      if (added.error) {
        var errorTypes = [ "disabled", "outdated", "unavailable", "deactivated", "overdue" ];
        for (i = 0, len = errorTypes.length; i < len; i++) {
          if (_flashState[errorTypes[i]]) {
            this.emit({
              type: "error",
              name: "flash-" + errorTypes[i],
              client: this
            });
            break;
          }
        }
      }
    }
    return this;
  };
  /**
 * The underlying implementation of `ZeroClipboard.Client.prototype.off`.
 * @private
 */
  var _clientOff = function(eventType, listener) {
    var i, len, foundIndex, events, perEventHandlers, handlers = _clientMeta[this.id] && _clientMeta[this.id].handlers;
    if (arguments.length === 0) {
      events = _keys(handlers);
    } else if (typeof eventType === "string" && eventType) {
      events = eventType.split(/\s+/);
    } else if (typeof eventType === "object" && eventType && typeof listener === "undefined") {
      for (i in eventType) {
        if (_hasOwn.call(eventType, i) && typeof i === "string" && i && typeof eventType[i] === "function") {
          this.off(i, eventType[i]);
        }
      }
    }
    if (events && events.length) {
      for (i = 0, len = events.length; i < len; i++) {
        eventType = events[i].toLowerCase().replace(/^on/, "");
        perEventHandlers = handlers[eventType];
        if (perEventHandlers && perEventHandlers.length) {
          if (listener) {
            foundIndex = perEventHandlers.indexOf(listener);
            while (foundIndex !== -1) {
              perEventHandlers.splice(foundIndex, 1);
              foundIndex = perEventHandlers.indexOf(listener, foundIndex);
            }
          } else {
            perEventHandlers.length = 0;
          }
        }
      }
    }
    return this;
  };
  /**
 * The underlying implementation of `ZeroClipboard.Client.prototype.handlers`.
 * @private
 */
  var _clientListeners = function(eventType) {
    var copy = null, handlers = _clientMeta[this.id] && _clientMeta[this.id].handlers;
    if (handlers) {
      if (typeof eventType === "string" && eventType) {
        copy = handlers[eventType] ? handlers[eventType].slice(0) : [];
      } else {
        copy = _deepCopy(handlers);
      }
    }
    return copy;
  };
  /**
 * The underlying implementation of `ZeroClipboard.Client.prototype.emit`.
 * @private
 */
  var _clientEmit = function(event) {
    if (_clientShouldEmit.call(this, event)) {
      if (typeof event === "object" && event && typeof event.type === "string" && event.type) {
        event = _extend({}, event);
      }
      var eventCopy = _extend({}, _createEvent(event), {
        client: this
      });
      _clientDispatchCallbacks.call(this, eventCopy);
    }
    return this;
  };
  /**
 * The underlying implementation of `ZeroClipboard.Client.prototype.clip`.
 * @private
 */
  var _clientClip = function(elements) {
    elements = _prepClip(elements);
    for (var i = 0; i < elements.length; i++) {
      if (_hasOwn.call(elements, i) && elements[i] && elements[i].nodeType === 1) {
        if (!elements[i].zcClippingId) {
          elements[i].zcClippingId = "zcClippingId_" + _elementIdCounter++;
          _elementMeta[elements[i].zcClippingId] = [ this.id ];
          if (_globalConfig.autoActivate === true) {
            _addMouseHandlers(elements[i]);
          }
        } else if (_elementMeta[elements[i].zcClippingId].indexOf(this.id) === -1) {
          _elementMeta[elements[i].zcClippingId].push(this.id);
        }
        var clippedElements = _clientMeta[this.id] && _clientMeta[this.id].elements;
        if (clippedElements.indexOf(elements[i]) === -1) {
          clippedElements.push(elements[i]);
        }
      }
    }
    return this;
  };
  /**
 * The underlying implementation of `ZeroClipboard.Client.prototype.unclip`.
 * @private
 */
  var _clientUnclip = function(elements) {
    var meta = _clientMeta[this.id];
    if (!meta) {
      return this;
    }
    var clippedElements = meta.elements;
    var arrayIndex;
    if (typeof elements === "undefined") {
      elements = clippedElements.slice(0);
    } else {
      elements = _prepClip(elements);
    }
    for (var i = elements.length; i--; ) {
      if (_hasOwn.call(elements, i) && elements[i] && elements[i].nodeType === 1) {
        arrayIndex = 0;
        while ((arrayIndex = clippedElements.indexOf(elements[i], arrayIndex)) !== -1) {
          clippedElements.splice(arrayIndex, 1);
        }
        var clientIds = _elementMeta[elements[i].zcClippingId];
        if (clientIds) {
          arrayIndex = 0;
          while ((arrayIndex = clientIds.indexOf(this.id, arrayIndex)) !== -1) {
            clientIds.splice(arrayIndex, 1);
          }
          if (clientIds.length === 0) {
            if (_globalConfig.autoActivate === true) {
              _removeMouseHandlers(elements[i]);
            }
            delete elements[i].zcClippingId;
          }
        }
      }
    }
    return this;
  };
  /**
 * The underlying implementation of `ZeroClipboard.Client.prototype.elements`.
 * @private
 */
  var _clientElements = function() {
    var meta = _clientMeta[this.id];
    return meta && meta.elements ? meta.elements.slice(0) : [];
  };
  /**
 * The underlying implementation of `ZeroClipboard.Client.prototype.destroy`.
 * @private
 */
  var _clientDestroy = function() {
    this.unclip();
    this.off();
    delete _clientMeta[this.id];
  };
  /**
 * Inspect an Event to see if the Client (`this`) should honor it for emission.
 * @private
 */
  var _clientShouldEmit = function(event) {
    if (!(event && event.type)) {
      return false;
    }
    if (event.client && event.client !== this) {
      return false;
    }
    var clippedEls = _clientMeta[this.id] && _clientMeta[this.id].elements;
    var hasClippedEls = !!clippedEls && clippedEls.length > 0;
    var goodTarget = !event.target || hasClippedEls && clippedEls.indexOf(event.target) !== -1;
    var goodRelTarget = event.relatedTarget && hasClippedEls && clippedEls.indexOf(event.relatedTarget) !== -1;
    var goodClient = event.client && event.client === this;
    if (!(goodTarget || goodRelTarget || goodClient)) {
      return false;
    }
    return true;
  };
  /**
 * Handle the actual dispatching of events to a client instance.
 *
 * @returns `this`
 * @private
 */
  var _clientDispatchCallbacks = function(event) {
    if (!(typeof event === "object" && event && event.type)) {
      return;
    }
    var async = _shouldPerformAsync(event);
    var wildcardTypeHandlers = _clientMeta[this.id] && _clientMeta[this.id].handlers["*"] || [];
    var specificTypeHandlers = _clientMeta[this.id] && _clientMeta[this.id].handlers[event.type] || [];
    var handlers = wildcardTypeHandlers.concat(specificTypeHandlers);
    if (handlers && handlers.length) {
      var i, len, func, context, eventCopy, originalContext = this;
      for (i = 0, len = handlers.length; i < len; i++) {
        func = handlers[i];
        context = originalContext;
        if (typeof func === "string" && typeof _window[func] === "function") {
          func = _window[func];
        }
        if (typeof func === "object" && func && typeof func.handleEvent === "function") {
          context = func;
          func = func.handleEvent;
        }
        if (typeof func === "function") {
          eventCopy = _extend({}, event);
          _dispatchCallback(func, context, [ eventCopy ], async);
        }
      }
    }
    return this;
  };
  /**
 * Prepares the elements for clipping/unclipping.
 *
 * @returns An Array of elements.
 * @private
 */
  var _prepClip = function(elements) {
    if (typeof elements === "string") {
      elements = [];
    }
    return typeof elements.length !== "number" ? [ elements ] : elements;
  };
  /**
 * Add a `mouseover` handler function for a clipped element.
 *
 * @returns `undefined`
 * @private
 */
  var _addMouseHandlers = function(element) {
    if (!(element && element.nodeType === 1)) {
      return;
    }
    var _suppressMouseEvents = function(event) {
      if (!(event || (event = _window.event))) {
        return;
      }
      if (event._source !== "js") {
        event.stopImmediatePropagation();
        event.preventDefault();
      }
      delete event._source;
    };
    var _elementMouseOver = function(event) {
      if (!(event || (event = _window.event))) {
        return;
      }
      _suppressMouseEvents(event);
      ZeroClipboard.focus(element);
    };
    element.addEventListener("mouseover", _elementMouseOver, false);
    element.addEventListener("mouseout", _suppressMouseEvents, false);
    element.addEventListener("mouseenter", _suppressMouseEvents, false);
    element.addEventListener("mouseleave", _suppressMouseEvents, false);
    element.addEventListener("mousemove", _suppressMouseEvents, false);
    _mouseHandlers[element.zcClippingId] = {
      mouseover: _elementMouseOver,
      mouseout: _suppressMouseEvents,
      mouseenter: _suppressMouseEvents,
      mouseleave: _suppressMouseEvents,
      mousemove: _suppressMouseEvents
    };
  };
  /**
 * Remove a `mouseover` handler function for a clipped element.
 *
 * @returns `undefined`
 * @private
 */
  var _removeMouseHandlers = function(element) {
    if (!(element && element.nodeType === 1)) {
      return;
    }
    var mouseHandlers = _mouseHandlers[element.zcClippingId];
    if (!(typeof mouseHandlers === "object" && mouseHandlers)) {
      return;
    }
    var key, val, mouseEvents = [ "move", "leave", "enter", "out", "over" ];
    for (var i = 0, len = mouseEvents.length; i < len; i++) {
      key = "mouse" + mouseEvents[i];
      val = mouseHandlers[key];
      if (typeof val === "function") {
        element.removeEventListener(key, val, false);
      }
    }
    delete _mouseHandlers[element.zcClippingId];
  };
  /**
 * Creates a new ZeroClipboard client instance.
 * Optionally, auto-`clip` an element or collection of elements.
 *
 * @constructor
 */
  ZeroClipboard._createClient = function() {
    _clientConstructor.apply(this, _args(arguments));
  };
  /**
 * Register an event listener to the client.
 *
 * @returns `this`
 */
  ZeroClipboard.prototype.on = function() {
    return _clientOn.apply(this, _args(arguments));
  };
  /**
 * Unregister an event handler from the client.
 * If no `listener` function/object is provided, it will unregister all handlers for the provided `eventType`.
 * If no `eventType` is provided, it will unregister all handlers for every event type.
 *
 * @returns `this`
 */
  ZeroClipboard.prototype.off = function() {
    return _clientOff.apply(this, _args(arguments));
  };
  /**
 * Retrieve event listeners for an `eventType` from the client.
 * If no `eventType` is provided, it will retrieve all listeners for every event type.
 *
 * @returns array of listeners for the `eventType`; if no `eventType`, then a map/hash object of listeners for all event types; or `null`
 */
  ZeroClipboard.prototype.handlers = function() {
    return _clientListeners.apply(this, _args(arguments));
  };
  /**
 * Event emission receiver from the Flash object for this client's registered JavaScript event listeners.
 *
 * @returns For the "copy" event, returns the Flash-friendly "clipData" object; otherwise `undefined`.
 */
  ZeroClipboard.prototype.emit = function() {
    return _clientEmit.apply(this, _args(arguments));
  };
  /**
 * Register clipboard actions for new element(s) to the client.
 *
 * @returns `this`
 */
  ZeroClipboard.prototype.clip = function() {
    return _clientClip.apply(this, _args(arguments));
  };
  /**
 * Unregister the clipboard actions of previously registered element(s) on the page.
 * If no elements are provided, ALL registered elements will be unregistered.
 *
 * @returns `this`
 */
  ZeroClipboard.prototype.unclip = function() {
    return _clientUnclip.apply(this, _args(arguments));
  };
  /**
 * Get all of the elements to which this client is clipped.
 *
 * @returns array of clipped elements
 */
  ZeroClipboard.prototype.elements = function() {
    return _clientElements.apply(this, _args(arguments));
  };
  /**
 * Self-destruct and clean up everything for a single client.
 * This will NOT destroy the embedded Flash object.
 *
 * @returns `undefined`
 */
  ZeroClipboard.prototype.destroy = function() {
    return _clientDestroy.apply(this, _args(arguments));
  };
  /**
 * Stores the pending plain text to inject into the clipboard.
 *
 * @returns `this`
 */
  ZeroClipboard.prototype.setText = function(text) {
    ZeroClipboard.setData("text/plain", text);
    return this;
  };
  /**
 * Stores the pending HTML text to inject into the clipboard.
 *
 * @returns `this`
 */
  ZeroClipboard.prototype.setHtml = function(html) {
    ZeroClipboard.setData("text/html", html);
    return this;
  };
  /**
 * Stores the pending rich text (RTF) to inject into the clipboard.
 *
 * @returns `this`
 */
  ZeroClipboard.prototype.setRichText = function(richText) {
    ZeroClipboard.setData("application/rtf", richText);
    return this;
  };
  /**
 * Stores the pending data to inject into the clipboard.
 *
 * @returns `this`
 */
  ZeroClipboard.prototype.setData = function() {
    ZeroClipboard.setData.apply(this, _args(arguments));
    return this;
  };
  /**
 * Clears the pending data to inject into the clipboard.
 * If no `format` is provided, all pending data formats will be cleared.
 *
 * @returns `this`
 */
  ZeroClipboard.prototype.clearData = function() {
    ZeroClipboard.clearData.apply(this, _args(arguments));
    return this;
  };
  /**
 * Gets a copy of the pending data to inject into the clipboard.
 * If no `format` is provided, a copy of ALL pending data formats will be returned.
 *
 * @returns `String` or `Object`
 */
  ZeroClipboard.prototype.getData = function() {
    return ZeroClipboard.getData.apply(this, _args(arguments));
  };
  if (false) {
    define(function() {
      return ZeroClipboard;
    });
  } else if (typeof module === "object" && module && typeof module.exports === "object" && module.exports) {
    module.exports = ZeroClipboard;
  } else {
    window.ZeroClipboard = ZeroClipboard;
  }
})(function() {
  return this || window;
}());
/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(44)(module)))

/***/ },

/***/ 154:
/***/ function(module, exports, __webpack_require__) {

/**
 * Abstract module that controls the addon node settings. Includes Knockout view-model
 * for syncing data, and HGrid-folderpicker for selecting a folder.
 */
'use strict';
__webpack_require__(155);
var ko = __webpack_require__(48);
__webpack_require__(152);
var $ = __webpack_require__(38);
var bootbox = __webpack_require__(138);
var Raven = __webpack_require__(52);

var FolderPicker = __webpack_require__(157);
var ZeroClipboard = __webpack_require__(153);
ZeroClipboard.config('/static/vendor/bower_components/zeroclipboard/dist/ZeroClipboard.swf');
var $osf = __webpack_require__(47);

var oop = __webpack_require__(146);

ko.punches.enableAll();

/**
 * @class FolderPickerViewModel
 * @param {String} addonName Full display name of the addon
 * @param {String} url API url to initially fetch settings
 * @param {String} selector CSS selector for containing div
 * @param {String} folderPicker CSS selector for folderPicker div
 *
 * Notes:
 * - Subclasses of this VM can be created using the oop module like: oop.extend(FolderPickerViewModel, { ... });
 * - Subclasses must:
 *   - provide a VM.messages.submitSettingsSuccess()
 *   - override VM.treebeardOptions.onPickFolder and VM.treebeardOptions.resolveLazyloadUrl
 * - Subclasses can:
 *   - implement an _updateCustomFields method to capture additional parameters in updateFromData
 */
var FolderPickerViewModel = oop.defclass({
    constructor: function(addonName, url, selector, folderpickerSelector) {
        var self = this;
        self.url = url;
        self.addonName = addonName;
        self.selector = selector;
        self.folderpickerSelector = folderpickerSelector;
        self.folderpicker = null;
        // Auth information
        self.nodeHasAuth = ko.observable(false);
        // whether current user has an auth token
        self.userHasAuth = ko.observable(false);
        // whether current user is authorizer of the addon
        self.userIsOwner = ko.observable(false);
        // display name of owner of credentials
        self.ownerName = ko.observable('');
        // whether the auth token is valid
        self.validCredentials = ko.observable(true);
        // whether import token has been clicked
        self.loadingImport = ko.observable(false);
        // current folder
        self.folder = ko.observable({
            name: null,
            id: null,
            path: null
        });
        // set of urls used for API calls internally
        self.urls = ko.observable({});
        // Flashed messages
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');
        // Display names
        self.PICKER = 'picker';
        // Currently selected folder name
        self.selected = ko.observable(false);
        self.loading = ko.observable(false);
        // Whether the initial data has been fetched form the server. Used for
        // error handling.
        self.loadedSettings = ko.observable(false);
        // Current folder display
        self.currentDisplay = ko.observable(null);
        // Whether the folders have been loaded from the API
        self.loadedFolders = ko.observable(false);

        self.messages = {
            invalidCredOwner: ko.pureComputed(function() {
                return 'Could not retrieve ' + self.addonName + ' settings at ' +
                    'this time. The credentials associated with this ' + self.addonName + ' account may no longer be valid.' +
                    ' Try disconnecting and reconnecting the ' + self.addonName + ' account on your <a href="' +
                    self.urls().settings + '">account settings page</a>.';
            }),
            invalidCredNotOwner: ko.pureComputed(function() {
                return 'Could not retrieve ' + self.addonName + ' settings at ' +
                    'this time. The credentials' + self.addonName + ' addon credentials may no longer be valid.' +
                    ' Contact ' + self.ownerName() + ' to verify.';
            }),
            cantRetrieveSettings: ko.pureComputed(function() {
                return 'Could not retrieve ' + self.addonName + ' settings at ' +
                    'this time. Please refresh ' +
                    'the page. If the problem persists, email ' +
                    '<a href="mailto:support@osf.io">support@osf.io</a>.';
            }),
            updateAccountsError: ko.pureComputed(function() {
                return 'Could not retrieve ' + self.addonName + ' account list at ' +
                    'this time. Please refresh the page. If the problem persists, email ' +
                    '<a href="mailto:support@osf.io">support@osf.io</a>.';
            }),
            deauthorizeSuccess: ko.pureComputed(function() {
                return 'Disconnected ' + self.addonName + '.';
            }),
            deauthorizeFail: ko.pureComputed(function() {
                return 'Could not disconnect ' + self.addonName + ' account because of an error. Please try again later.';
            }),
            connectAccountSuccess: ko.pureComputed(function() {
                return 'Successfully connected a ' + self.addonName + ' account';
            }),
            connectAccountDenied: ko.pureComputed(function() {
                return 'Error while authorizing addon. Please log in to your ' + self.addonName + ' account and grant access to the OSF to enable this addon.';
            }),
            submitSettingsSuccess: ko.pureComputed(function() {
                throw new Error('Subclasses of FolderPickerViewModel must provide a message for successful settings updates. ' +
                                'This should take the form: "Successfully linked \'{FOLDER_NAME}\'. Go to the <a href="{URL}"> ' +
                                '{PAGE_NAME} to view your {CONTENT_TYPE}.');
            }),
            submitSettingsError: ko.pureComputed(function() {
                return 'Could not change ' + self.addonName + ' settings. Please try again later.';
            }),
            confirmDeauth: ko.pureComputed(function() {
                return 'Are you sure you want to remove this ' + self.addonName + ' account?';
            }),
            confirmAuth: ko.pureComputed(function() {
                return 'Are you sure you want to link your ' + self.addonName + ' account with this project?';
            }),
            tokenImportSuccess: ko.pureComputed(function() {
                return 'Successfully imported ' + self.addonName + ' account from profile.';
            }),
            tokenImportError: ko.pureComputed(function() {
                return 'Error occurred while importing ' + self.addonName + ' account.';
            }),
            connectError: ko.pureComputed(function() {
                return 'Could not connect to ' + self.addonName + ' at this time. Please try again later.';
            })
        };

        /**
         * Whether or not to show the Import Access Token Button
         */
        self.showImport = ko.pureComputed(function() {
            // Invoke the observables to ensure dependency tracking
            var userHasAuth = self.userHasAuth();
            var nodeHasAuth = self.nodeHasAuth();
            var loaded = self.loadedSettings();
            var onclick = self.loadingImport();
            return userHasAuth && !nodeHasAuth && loaded && !onclick;
        });

        /** Whether or not show loading icon after import button */
        self.showLoading = ko.pureComputed(function() {
            var userHasAuth = self.userHasAuth();
            var nodeHasAuth = self.nodeHasAuth();
            var loaded = self.loadedSettings();
            var onclick = self.loadingImport();
            return userHasAuth && !nodeHasAuth && loaded && onclick;
        });

        /** Whether or not to show the full settings pane. */
        self.showSettings = ko.pureComputed(function() {
            return self.nodeHasAuth() && self.validCredentials();
        });

        /** Whether or not to show the Connect Account button */
        self.showTokenCreateButton = ko.pureComputed(function() {
            // Invoke the observables to ensure dependency tracking
            var userHasAuth = self.userHasAuth();
            var nodeHasAuth = self.nodeHasAuth();
            var loaded = self.loadedSettings();
            return loaded && !userHasAuth && !nodeHasAuth;
        });

        /** Computed functions for the linked and selected folders' display text.*/
        self.folderName = ko.pureComputed(function() {
            var nodeHasAuth = self.nodeHasAuth();
            var folder = self.folder();
            return (nodeHasAuth && folder && folder.name) ? folder.name.trim() : '';
        });

        self.selectedFolderName = ko.pureComputed(function() {
            var userIsOwner = self.userIsOwner();
            var selected = self.selected();
            var name = selected.name || 'None';
            return userIsOwner ? name : '';
        });

        self.treebeardOptions = {
            lazyLoadPreprocess: function(data) {
                return data;
            },
            onPickFolder: function() {
                throw new Error('Subclasses of FolderPickerViewModel must implement a "onPickFolder(evt, item)" method');
            },
            resolveLazyloadUrl: function(item) {
                throw new Error('Subclasses of FolderPickerViewModel must implement a "resolveLazyloadUrl(item)" method');
            }
        };
    },
    /**
     * Change the flashed message.
     *
     * @param {String} text Text to show
     * @param {String} css CSS class of text to be show, defaults to 'text-info'
     * @param {Number} timeout Optional number of ms to wait until removing the flashed message
     */
    changeMessage: function(text, css, timeout) {
        var self = this;

        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(function() {
                self.resetMessage();
            }, timeout);
        }
    },
    resetMessage: function() {
        this.message('');
        this.messageClass('text-info');
    },
    /**
     * Abstract hook called after updateFromData, before the promise is resolved.
     * - use to validate the VM state after update
     **/
    afterUpdate: function() {},
    /**
     * Abstract hook where subclasses can capture extra data from the API response
     *
     * @param {Object} settings Settings passed from server response in #updateFromData
     */
    _updateCustomFields: function(settings) {},
    /**
     * Update the view model from data returned from the server or data passed explicitly.
     *
     * @param {Object} data optional data to update from rather than from API
     */
    updateFromData: function(data) {
        var self = this;
        var ret = $.Deferred();
        var applySettings = function(settings){
            self.ownerName(settings.ownerName);
            self.nodeHasAuth(settings.nodeHasAuth);
            self.userIsOwner(settings.userIsOwner);
            self.userHasAuth(settings.userHasAuth);
            self.folder(settings.folder || {
                name: null,
                path: null,
                id: null
            });
            self.urls(settings.urls);
            self._updateCustomFields(settings);
            self.afterUpdate();
            ret.resolve();
        };
        if (typeof data === 'undefined'){
            self.fetchFromServer()
                .done(applySettings)
                .fail(ret.reject);
        }
        else{
            applySettings(data);
        }
        return ret.promise();
    },
    fetchFromServer: function() {
        var self = this;
        var ret = $.Deferred();
        var request = $.ajax({
            url: self.url,
            type: 'GET',
            dataType: 'json'
        });
        request.done(function(response) {
            self.loadedSettings(true);
            ret.resolve(response.result);
        });
        request.fail(function(xhr, textStatus, error) {
            self.changeMessage(self.messages.cantRetrieveSettings(), 'text-danger');
            Raven.captureMessage('Could not GET ' + self.addonName + 'settings', {
                url: self.url,
                textStatus: textStatus,
                error: error
            });
            ret.reject(xhr, textStatus, error);
        });
        return ret.promise();
    },
    _serializeSettings: function(){
        return ko.toJS(this);
    },
    /**
     * Send a PUT request to change the linked folder.
     */
    submitSettings: function() {
        var self = this;
        function onSubmitSuccess(response) {
            // Update folder in ViewModel
            self.folder(response.result.folder);
            self.urls(response.result.urls);
            self.cancelSelection();
            self.changeMessage(self.messages.submitSettingsSuccess(), 'text-success');
        }
        function onSubmitError(xhr, status, error) {
            self.changeMessage(self.messages.submitSettingsError(), 'text-danger');
            Raven.captureMessage('Failed to update ' + self.addonName + ' settings.', {
                xhr: xhr,
                status: status,
                error: error
            });
        }
        return $osf.putJSON(self.urls().config, self._serializeSettings())
            .done(onSubmitSuccess)
            .fail(onSubmitError);
    },
    onImportSuccess: function(response) {
        var self = this;
        var msg = response.message || self.messages.tokenImportSuccess();
        // Update view model based on response
        self.changeMessage(msg, 'text-success', 3000);
        self.updateFromData(response.result);
        self.activatePicker();
    },
    onImportError: function(xhr, status, error) {
        var self = this;
        self.changeMessage(self.messages.tokenImportError(), 'text-danger');
        Raven.captureMessage('Failed to import ' + self.addonName + ' access token.', {
            xhr: xhr,
            status: status,
            error: error
        });
    },
    _importAuthPayload: function() {
        return {};
    },
    _importAuthConfirm: function() {
        var self = this;
        return $osf.putJSON(self.urls().importAuth, self._importAuthPayload())
            .done(self.onImportSuccess.bind(self))
            .fail(self.onImportError.bind(self));
    },
    /**
     * Send PUT request to import access token from user profile.
     */
    importAuth: function() {
        var self = this;
        bootbox.confirm({
            title: 'Import ' + self.addonName + ' Account?',
            message: self.messages.confirmAuth(),
            callback: function(confirmed) {
                if (confirmed) {
                    self._importAuthConfirm();
                    self.loadingImport(true);
                }
            },
            buttons:{
                confirm:{
                    label:'Import'
                }
            }
        });
    },
    /**
     * Send DELETE request to deauthorize this node.
     */
    _deauthorizeConfirm: function(){
        var self = this;
        var request = $.ajax({
            url: self.urls().deauthorize,
            type: 'DELETE'
        });
        request.done(function() {
            // Update observables
            self.nodeHasAuth(false);
            self.cancelSelection();
            self.currentDisplay(null);
            self.changeMessage(self.messages.deauthorizeSuccess(), 'text-warning', 3000);
            self.loadedFolders(false);
            self.destroyPicker();
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
    },
    /** Pop up a confirmation to deauthorize addon from this node.
     *  Send DELETE request if confirmed.
     */
    deauthorize: function() {
        var self = this;
        bootbox.confirm({
            title: 'Disconnect ' + self.addonName + ' Account?',
            message: self.messages.confirmDeauth(),
            callback: function(confirmed) {
                if (confirmed) {
                    self._deauthorizeConfirm();
                    self.loadingImport(false);
                }
            },
            buttons:{
                confirm:{
                    label:'Disconnect',
                    className:'btn-danger'
                }
            }
        });
    },
    /**
     * Must be used to update radio buttons and knockout view model simultaneously
     */
    cancelSelection: function() {
        this.selected(null);
    },
    /**
     *  Toggles the visibility of the folder picker.
     */
    togglePicker: function() {
        var shown = this.currentDisplay() === this.PICKER;
        if (!shown) {
            this.currentDisplay(this.PICKER);
            this.activatePicker();
        } else {
            this.currentDisplay(null);
            // Clear selection
            this.cancelSelection();
        }
    },
    destroyPicker: function() {
        if (this.folderpicker) {
            this.folderpicker.destroy();
        }
    },
    doActivatePicker: function(opts) {
        var self = this;
        // Show loading indicator
        self.loading(true);
        self.folderpicker = new FolderPicker(self.folderpickerSelector, opts);
    },
    /**
     *  Activates the HGrid folder picker.
     */
    activatePicker: function() {
        var self = this;
        var opts = $.extend({}, {
            initialFolderPath: self.folder().path || '',
            // Fetch folders with AJAX
            filesData: self.urls().folders, // URL for fetching folders
            // Lazy-load each folder's contents
            // Each row stores its url for fetching the folders it contains
            oddEvenClass: {
                odd: 'addon-folderpicker-odd',
                even: 'addon-folderpicker-even'
            },
            multiselect: false,
            allowMove: false,
            ajaxOptions: {
                error: function(xhr, textStatus, error) {
                    self.loading(false);
                    self.changeMessage(self.messages.connectError(), 'text-danger');
                    Raven.captureMessage('Could not GET get ' + self.addonName + ' contents.', {
                        textStatus: textStatus,
                        error: error
                    });
                }
            },
            folderPickerOnload: function() {
                // Hide loading indicator
                self.loading(false);
                // Set flag to prevent repeated requests
                self.loadedFolders(true);
            }
        }, self.treebeardOptions);
        self.currentDisplay(self.PICKER);
        // Only load folders if they haven't already been requested
        if (!self.loadedFolders()) {
            self.doActivatePicker(opts);
        }
    }
});

module.exports = FolderPickerViewModel;


/***/ },

/***/ 155:
/***/ function(module, exports, __webpack_require__) {

// style-loader: Adds some css to the DOM by adding a <style> tag

// load the styles
var content = __webpack_require__(156);
if(typeof content === 'string') content = [[module.id, content, '']];
// add the styles to the DOM
var update = __webpack_require__(19)(content, {});
// Hot Module Replacement
if(false) {
	// When the styles change, update the <style> tags
	module.hot.accept("!!/Users/laurenbarker/GitHub/osf.io/node_modules/css-loader/index.js!/Users/laurenbarker/GitHub/osf.io/website/static/css/addon_folderpicker.css", function() {
		var newContent = require("!!/Users/laurenbarker/GitHub/osf.io/node_modules/css-loader/index.js!/Users/laurenbarker/GitHub/osf.io/website/static/css/addon_folderpicker.css");
		if(typeof newContent === 'string') newContent = [[module.id, newContent, '']];
		update(newContent);
	});
	// When the module is disposed, remove the <style> tags
	module.hot.dispose(function() { update(); });
}

/***/ },

/***/ 156:
/***/ function(module, exports, __webpack_require__) {

exports = module.exports = __webpack_require__(16)();
exports.push([module.id, "/*\nOverride treebeard styles\n*/\n.addon-folderpicker-widget .title-text {\n    cursor: initial;\n}\n.addon-folderpicker-widget .tb-expand-icon-holder {\n    cursor: initial;\n}\n.addon-folderpicker-widget .tb-multiselect {\n    background-color: white;\n}\n/* ---------------- */\n", ""]);

/***/ },

/***/ 157:
/***/ function(module, exports, __webpack_require__) {

/**
* A simple folder picker plugin built on HGrid.
* Takes the same options as HGrid and additionally requires an
* `onPickFolder` option (the callback executed when a folder is selected).
*
* Usage:
*
*     $('#myPicker').folderpicker({
*         data: // Array of HGrid-formatted data or URL to fetch data
*         onPickFolder: function(evt, folder) {
*             // do something with folder
*         }
*     });
*/
'use strict';
var $ = __webpack_require__(38);
var m = __webpack_require__(158);
var Treebeard = __webpack_require__(159);


function treebeardToggleCheck(item) {
    return ((typeof item.data.hasChildren === 'undefined') || item.data.hasChildren);
}

function treebeardResolveToggle(item) {
    if ((typeof item.data.hasChildren !== 'undefined') && item.data.hasChildren === false) {
        return '';
    }

    return item.open ?
        m('i.fa.fa-minus', ' '):
        m('i.fa.fa-plus', ' ');
}

// Returns custom icons for OSF
function treebeardResolveIcon(item) {
    return item.open ?
        m('i.fa.fa-folder-open-o', ' '):
        m('i.fa.fa-folder-o', ' ');
}

var INPUT_NAME = '-folder-select';

function treebeardTitleColumn(item, col) {
    var tb = this; // jshint ignore: line

    var cls = '';
    var onclick = function() {};
    if (typeof item.data.hasChildren === 'undefined' || item.data.hasChildren) {
        cls = 'hasChildren';
        onclick = function() {
            tb.updateFolder(null, item);
        };
    }

    return m('span', {
        className: cls,
        onclick: onclick
    }, tb.options.decodeFolder(item.data.name));
}

/**
 * Returns the folder select button for a single row.
 */
function treebeardSelectView(item) {
    var tb = this; // jshint ignore: line
    var setTempPicked = function() {
        this._tempPicked = item.id;
    };
    var templateChecked = m('input', {
        type: 'radio',
        checked: 'checked',
        name: '#' + tb.options.divID + INPUT_NAME,
        value: item.id
    }, ' ');
    var templateUnchecked = m('input', {
        type: 'radio',
        onclick: setTempPicked.bind(tb),
        onmousedown: function(evt) {
            tb.options.onPickFolder(evt, item);
        },
        name: '#' + tb.options.divID + INPUT_NAME
    }, ' ');

    if (tb._tempPicked) {
        if (tb._tempPicked === item.id) {
            return templateChecked;
        }
        return templateUnchecked;
    }

    if (item.data.path === tb.options.folderPath || (tb.options.folderArray && tb.options.folderArray[tb.options.folderArray.length - 1] === item.data.name)) {
        return templateChecked;
    }

    return templateUnchecked;
}

function treebeardColumnTitle() {
    return [{
        title: 'Folders',
        width: '75%',
        sort: false
    }, {
        title: 'Select',
        width: '25%',
        sort: false
    }];
}

function treebeardResolveRows(item) {
    // this = treebeard;
    item.css = '';
    return [{
        data: 'name', // Data field name
        folderIcons: true,
        filter: false,
        custom: treebeardTitleColumn
    }, {
        sortInclude: false,
        css: 'p-l-xs',
        custom: treebeardSelectView
    }];
}

function treebeardOnload() {
    var tb = this; // jshint ignore: line

    tb.options.folderIndex = 0;
    if (tb.options.folderPath) {
        tb.options.folderArray = tb.options.folderPath.split('/');
        if (tb.options.folderArray.length > 1) {
            tb.options.folderArray.splice(0, 1);
        }
    } else {
        tb.options.folderArray = [''];
    }

    var node = tb.treeData.children[0];
    if ((typeof node.data.hasChildren === 'undefined') || node.data.hasChildren) {
        tb.updateFolder(null, tb.treeData.children[0]);
    }
    tb.options.folderPickerOnload();
}

function treebeardLazyLoadOnLoad(item) {
    var tb = this; // jshint ignore: line

    for (var i = 0; i < item.children.length; i++) {
        if ((typeof item.data.hasChildren !== 'undefined') && item.data.hasChildren === false) {
            return;
        }
        if (item.children[i].data.name === tb.options.folderArray[tb.options.folderIndex]) {
            tb.updateFolder(null, item.children[i]);
            tb.options.folderIndex++;
            return;
        }
    }
}

function treebeardDecodeFolder(item) {
    return item;
}

// Default Treebeard options
var defaults = {
    columnTitles: treebeardColumnTitle,
    resolveRows: treebeardResolveRows,
    resolveIcon: treebeardResolveIcon,
    togglecheck: treebeardToggleCheck,
    resolveToggle: treebeardResolveToggle,
    ondataload: treebeardOnload,
    lazyLoadOnLoad: treebeardLazyLoadOnLoad,
    decodeFolder: treebeardDecodeFolder,
    // Disable uploads
    uploads: false,
    showFilter : false,
    resizeColumns : false,
    rowHeight : 35,
    resolveRefreshIcon : function() {
        return m('i.fa.fa-refresh.fa-spin');
    }
};

function FolderPicker(selector, opts) {
    var self = this;
    self.selector = selector;
    self.checkedRowId = null;
    // Custom Treebeard action to select a folder that uses the passed in
    // "onChooseFolder" callback
    if (!opts.onPickFolder) {
        throw new Error('FolderPicker must have the "onPickFolder" option defined');
    }
    self.options = $.extend({}, defaults, opts);
    self.options.divID = selector.substring(1);
    self.options.initialFolderName = opts.initialFolderName;
    self.options.folderPath = opts.initialFolderPath;
    self.options.rootName = opts.rootName;

    // Start up the grid
    self.grid = new Treebeard(self.options).tbController;
}

FolderPicker.prototype.destroy = function() {
    this.grid.destroy();
};

// Augment jQuery
$.fn.folderpicker = function(options) {
    var $el = $(this);
    this.each(function() {
        // Treebeard must take an ID as a selector if using as a jQuery plugin
        if (!this.id) {
            throw new Error('FolderPicker must have an ID if initializing with jQuery.');
        }
        var selector = '#' + this.id;
        this._tb = new FolderPicker(selector, options);
    });
};


FolderPicker.selectView = treebeardSelectView;

module.exports = FolderPicker;


/***/ },

/***/ 367:
/***/ function(module, exports, __webpack_require__) {

/**
 * Module that controls the citations addons node settings. Includes Knockout view-model
 * for syncing data, and HGrid-folderpicker for selecting a folder.
 */
'use strict';

var ko = __webpack_require__(48);
__webpack_require__(152);
var $ = __webpack_require__(38);
var Raven = __webpack_require__(52);
var bootbox = __webpack_require__(138);
__webpack_require__(195);

var $osf = __webpack_require__(47);
var oop = __webpack_require__(146);
var FolderPickerViewModel = __webpack_require__(154);

ko.punches.enableAll();

/**
 * View model to support instances of CitationsNodeConfig (folder picker widget)
 *
 * @class AddonFolderPickerViewModel
 * @param {String} addonName Full display name of the addon
 * @param {String} url API url to initially fetch settings
 * @param {String} selector CSS selector for containing div
 * @param {String} folderPicker CSS selector for folderPicker div
 */
var CitationsFolderPickerViewModel = oop.extend(FolderPickerViewModel, {
    constructor: function(addonName, url, selector, folderPicker) {
        var self = this;
        self.super.constructor.call(self, addonName, url, selector, folderPicker);
        self.userAccountId = ko.observable('');
        // externalAccounts
        self.accounts = ko.observable([]);

        self.messages.submitSettingsSuccess = ko.pureComputed(function(){
            return 'Successfully linked "' + $osf.htmlEscape(self.folder().name) + '". Go to the <a href="' +
                self.urls().files + '">Overview page</a> to view your citations.';
        });

        self.treebeardOptions = $.extend(
            {},
            FolderPickerViewModel.prototype.treebeardOptions,
            {
                /** Callback for chooseFolder action.
                 *   Just changes the ViewModel's self.selected observable to the selected
                 *   folder.
                 */
                onPickFolder: function(evt, item){
                    evt.preventDefault();
                    this.selected({
                        name: item.data.name,
                        id: item.data.id
                    });
                    return false; // Prevent event propagation
                }.bind(this),
                lazyLoadPreprocess: function(data) {
                    return data.contents.filter(function(item) {
                    return item.kind === 'folder';
                    });
                },
                resolveLazyloadUrl: function(item) {
                    return this.urls().folders + item.data.id + '/?view=folders';
                }.bind(this)
            });
    },
    fetchAccounts: function() {
        var self = this;
        var ret = $.Deferred();
        var request = $.get(self.urls().accounts);
        request.then(function(data) {
            ret.resolve(data.accounts);
            $('.addon-auth-table').osfToggleHeight({height: 140});
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
    },
    updateAccounts: function() {
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
    },
    /**
     * Allows a user to create an access token from the nodeSettings page
     */
    connectAccount: function() {
        var self = this;

        window.oauthComplete = function(res) {
            // Update view model based on response
            self.changeMessage(self.messages.connectAccountSuccess(), 'text-success', 3000);
            self.userHasAuth(true);
            self.importAuth.call(self);
        };
        window.open(self.urls().auth);
    },
    connectExistingAccount: function(account_id) {
        var self = this;

        return $osf.putJSON(
            self.urls().importAuth, {
                external_account_id: account_id
            }
        ).then(self.onImportSuccess.bind(self), self.onImportError.bind(self));
    },
    _updateCustomFields: function(settings){
        this.userAccountId(settings.userAccountId);
    },
    _serializeSettings: function(){
        return {
            external_account_id: this.userAccountId(),
            external_list_id: this.selected().id,
            external_list_name: this.selected().name
        };
    },
    importAuth: function() {
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
                        title: 'Import ' + self.addonName + ' access token',
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
    }
});
// Public API
function CitationsNodeConfig(addonName, selector, url, folderPicker) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    self.viewModel = new CitationsFolderPickerViewModel(addonName, url, selector, folderPicker);
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = {
    CitationsNodeConfig: CitationsNodeConfig,
    _CitationsNodeConfigViewModel: CitationsFolderPickerViewModel
};


/***/ }

});
//# sourceMappingURL=node-cfg.js.map