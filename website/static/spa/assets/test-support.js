/* jshint ignore:start */

/* jshint ignore:end */

/*!
 * @overview  Ember - JavaScript Application Framework
 * @copyright Copyright 2011-2015 Tilde Inc. and contributors
 *            Portions Copyright 2006-2011 Strobe Inc.
 *            Portions Copyright 2008-2011 Apple Inc. All rights reserved.
 * @license   Licensed under MIT license
 *            See https://raw.github.com/emberjs/ember.js/master/LICENSE
 * @version   1.13.7
 */

(function() {
var enifed, requireModule, eriuqer, requirejs, Ember;
var mainContext = this;

(function() {
  var isNode = typeof process !== 'undefined' && {}.toString.call(process) === '[object process]';

  if (!isNode) {
    Ember = this.Ember = this.Ember || {};
  }

  if (typeof Ember === 'undefined') { Ember = {}; };

  if (typeof Ember.__loader === 'undefined') {
    var registry = {};
    var seen = {};

    enifed = function(name, deps, callback) {
      var value = { };

      if (!callback) {
        value.deps = [];
        value.callback = deps;
      } else {
        value.deps = deps;
        value.callback = callback;
      }

        registry[name] = value;
    };

    requirejs = eriuqer = requireModule = function(name) {
      return internalRequire(name, null);
    }

    function internalRequire(name, referrerName) {
      var exports = seen[name];

      if (exports !== undefined) {
        return exports;
      }

      exports = seen[name] = {};

      if (!registry[name]) {
        if (referrerName) {
          throw new Error('Could not find module ' + name + ' required by: ' + referrerName);
        } else {
          throw new Error('Could not find module ' + name);
        }
      }

      var mod = registry[name];
      var deps = mod.deps;
      var callback = mod.callback;
      var reified = [];
      var length = deps.length;

      for (var i=0; i<length; i++) {
        if (deps[i] === 'exports') {
          reified.push(exports);
        } else {
          reified.push(internalRequire(resolve(deps[i], name), name));
        }
      }

      callback.apply(this, reified);

      return exports;
    };

    function resolve(child, name) {
      if (child.charAt(0) !== '.') {
        return child;
      }
      var parts = child.split('/');
      var parentBase = name.split('/').slice(0, -1);

      for (var i=0, l=parts.length; i<l; i++) {
        var part = parts[i];

        if (part === '..') {
          parentBase.pop();
        } else if (part === '.') {
          continue;
        } else {
          parentBase.push(part);
        }
      }

      return parentBase.join('/');
    }

    requirejs._eak_seen = registry;

    Ember.__loader = {
      define: enifed,
      require: eriuqer,
      registry: registry
    };
  } else {
    enifed = Ember.__loader.define;
    requirejs = eriuqer = requireModule = Ember.__loader.require;
  }
})();

enifed("ember-debug", ["exports", "ember-metal/core", "ember-metal/error", "ember-metal/logger", "ember-debug/deprecation-manager", "ember-metal/environment"], function (exports, _emberMetalCore, _emberMetalError, _emberMetalLogger, _emberDebugDeprecationManager, _emberMetalEnvironment) {
  /*global __fail__*/

  "use strict";

  exports._warnIfUsingStrippedFeatureFlags = _warnIfUsingStrippedFeatureFlags;

  /**
  @module ember
  @submodule ember-debug
  */

  /**
  @class Ember
  @public
  */

  function isPlainFunction(test) {
    return typeof test === 'function' && test.PrototypeMixin === undefined;
  }

  /**
    Define an assertion that will throw an exception if the condition is not
    met. Ember build tools will remove any calls to `Ember.assert()` when
    doing a production build. Example:
  
    ```javascript
    // Test for truthiness
    Ember.assert('Must pass a valid object', obj);
  
    // Fail unconditionally
    Ember.assert('This code path should never be run');
    ```
  
    @method assert
    @param {String} desc A description of the assertion. This will become
      the text of the Error thrown if the assertion fails.
    @param {Boolean|Function} test Must be truthy for the assertion to pass. If
      falsy, an exception will be thrown. If this is a function, it will be executed and
      its return value will be used as condition.
    @public
  */
  _emberMetalCore["default"].assert = function (desc, test) {
    var throwAssertion;

    if (isPlainFunction(test)) {
      throwAssertion = !test();
    } else {
      throwAssertion = !test;
    }

    if (throwAssertion) {
      throw new _emberMetalError["default"]("Assertion Failed: " + desc);
    }
  };

  /**
    Display a warning with the provided message. Ember build tools will
    remove any calls to `Ember.warn()` when doing a production build.
  
    @method warn
    @param {String} message A warning to display.
    @param {Boolean} test An optional boolean. If falsy, the warning
      will be displayed.
    @public
  */
  _emberMetalCore["default"].warn = function (message, test) {
    if (!test) {
      _emberMetalLogger["default"].warn("WARNING: " + message);
      if ('trace' in _emberMetalLogger["default"]) {
        _emberMetalLogger["default"].trace();
      }
    }
  };

  /**
    Display a debug notice. Ember build tools will remove any calls to
    `Ember.debug()` when doing a production build.
  
    ```javascript
    Ember.debug('I\'m a debug notice!');
    ```
  
    @method debug
    @param {String} message A debug message to display.
    @public
  */
  _emberMetalCore["default"].debug = function (message) {
    _emberMetalLogger["default"].debug("DEBUG: " + message);
  };

  /**
    Display a deprecation warning with the provided message and a stack trace
    (Chrome and Firefox only). Ember build tools will remove any calls to
    `Ember.deprecate()` when doing a production build.
  
    @method deprecate
    @param {String} message A description of the deprecation.
    @param {Boolean|Function} test An optional boolean. If falsy, the deprecation
      will be displayed. If this is a function, it will be executed and its return
      value will be used as condition.
    @param {Object} options An optional object that can be used to pass
      in a `url` to the transition guide on the emberjs.com website, and a unique
      `id` for this deprecation. The `id` can be used by Ember debugging tools
      to change the behavior (raise, log or silence) for that specific deprecation.
      The `id` should be namespaced by dots, e.g. "view.helper.select".
    @public
  */
  _emberMetalCore["default"].deprecate = function (message, test, options) {
    if (_emberMetalCore["default"].ENV.RAISE_ON_DEPRECATION) {
      _emberDebugDeprecationManager["default"].setDefaultLevel(_emberDebugDeprecationManager.deprecationLevels.RAISE);
    }
    if (_emberDebugDeprecationManager["default"].getLevel(options && options.id) === _emberDebugDeprecationManager.deprecationLevels.SILENCE) {
      return;
    }

    var noDeprecation;

    if (isPlainFunction(test)) {
      noDeprecation = test();
    } else {
      noDeprecation = test;
    }

    if (noDeprecation) {
      return;
    }

    if (options && options.id) {
      message = message + (" [deprecation id: " + options.id + "]");
    }

    if (_emberDebugDeprecationManager["default"].getLevel(options && options.id) === _emberDebugDeprecationManager.deprecationLevels.RAISE) {
      throw new _emberMetalError["default"](message);
    }

    var error;

    // When using new Error, we can't do the arguments check for Chrome. Alternatives are welcome
    try {
      __fail__.fail();
    } catch (e) {
      error = e;
    }

    if (arguments.length === 3) {
      _emberMetalCore["default"].assert('options argument to Ember.deprecate should be an object', options && typeof options === 'object');
      if (options.url) {
        message += ' See ' + options.url + ' for more details.';
      }
    }

    if (_emberMetalCore["default"].LOG_STACKTRACE_ON_DEPRECATION && error.stack) {
      var stack;
      var stackStr = '';

      if (error['arguments']) {
        // Chrome
        stack = error.stack.replace(/^\s+at\s+/gm, '').replace(/^([^\(]+?)([\n$])/gm, '{anonymous}($1)$2').replace(/^Object.<anonymous>\s*\(([^\)]+)\)/gm, '{anonymous}($1)').split('\n');
        stack.shift();
      } else {
        // Firefox
        stack = error.stack.replace(/(?:\n@:0)?\s+$/m, '').replace(/^\(/gm, '{anonymous}(').split('\n');
      }

      stackStr = "\n    " + stack.slice(2).join("\n    ");
      message = message + stackStr;
    }

    _emberMetalLogger["default"].warn("DEPRECATION: " + message);
  };

  /**
    Alias an old, deprecated method with its new counterpart.
  
    Display a deprecation warning with the provided message and a stack trace
    (Chrome and Firefox only) when the assigned method is called.
  
    Ember build tools will not remove calls to `Ember.deprecateFunc()`, though
    no warnings will be shown in production.
  
    ```javascript
    Ember.oldMethod = Ember.deprecateFunc('Please use the new, updated method', Ember.newMethod);
    ```
  
    @method deprecateFunc
    @param {String} message A description of the deprecation.
    @param {Object} [options] The options object for Ember.deprecate.
    @param {Function} func The new function called to replace its deprecated counterpart.
    @return {Function} a new function that wrapped the original function with a deprecation warning
    @private
  */
  _emberMetalCore["default"].deprecateFunc = function () {
    for (var _len = arguments.length, args = Array(_len), _key = 0; _key < _len; _key++) {
      args[_key] = arguments[_key];
    }

    if (args.length === 3) {
      var _ret = (function () {
        var message = args[0];
        var options = args[1];
        var func = args[2];

        return {
          v: function () {
            _emberMetalCore["default"].deprecate(message, false, options);
            return func.apply(this, arguments);
          }
        };
      })();

      if (typeof _ret === "object") return _ret.v;
    } else {
      var _ret2 = (function () {
        var message = args[0];
        var func = args[1];

        return {
          v: function () {
            _emberMetalCore["default"].deprecate(message);
            return func.apply(this, arguments);
          }
        };
      })();

      if (typeof _ret2 === "object") return _ret2.v;
    }
  };

  /**
    Run a function meant for debugging. Ember build tools will remove any calls to
    `Ember.runInDebug()` when doing a production build.
  
    ```javascript
    Ember.runInDebug(() => {
      Ember.Component.reopen({
        didInsertElement() {
          console.log("I'm happy");
        }
      });
    });
    ```
  
    @method runInDebug
    @param {Function} func The function to be executed.
    @since 1.5.0
    @public
  */
  _emberMetalCore["default"].runInDebug = function (func) {
    func();
  };

  /**
    Will call `Ember.warn()` if ENABLE_ALL_FEATURES, ENABLE_OPTIONAL_FEATURES, or
    any specific FEATURES flag is truthy.
  
    This method is called automatically in debug canary builds.
  
    @private
    @method _warnIfUsingStrippedFeatureFlags
    @return {void}
  */

  function _warnIfUsingStrippedFeatureFlags(FEATURES, featuresWereStripped) {
    if (featuresWereStripped) {
      _emberMetalCore["default"].warn('Ember.ENV.ENABLE_ALL_FEATURES is only available in canary builds.', !_emberMetalCore["default"].ENV.ENABLE_ALL_FEATURES);
      _emberMetalCore["default"].warn('Ember.ENV.ENABLE_OPTIONAL_FEATURES is only available in canary builds.', !_emberMetalCore["default"].ENV.ENABLE_OPTIONAL_FEATURES);

      for (var key in FEATURES) {
        if (FEATURES.hasOwnProperty(key) && key !== 'isEnabled') {
          _emberMetalCore["default"].warn('FEATURE["' + key + '"] is set as enabled, but FEATURE flags are only available in canary builds.', !FEATURES[key]);
        }
      }
    }
  }

  if (!_emberMetalCore["default"].testing) {
    // Complain if they're using FEATURE flags in builds other than canary
    _emberMetalCore["default"].FEATURES['features-stripped-test'] = true;
    var featuresWereStripped = true;

    
    delete _emberMetalCore["default"].FEATURES['features-stripped-test'];
    _warnIfUsingStrippedFeatureFlags(_emberMetalCore["default"].ENV.FEATURES, featuresWereStripped);

    // Inform the developer about the Ember Inspector if not installed.
    var isFirefox = _emberMetalEnvironment["default"].isFirefox;
    var isChrome = _emberMetalEnvironment["default"].isChrome;

    if (typeof window !== 'undefined' && (isFirefox || isChrome) && window.addEventListener) {
      window.addEventListener("load", function () {
        if (document.documentElement && document.documentElement.dataset && !document.documentElement.dataset.emberExtension) {
          var downloadURL;

          if (isChrome) {
            downloadURL = 'https://chrome.google.com/webstore/detail/ember-inspector/bmdblncegkenkacieihfhpjfppoconhi';
          } else if (isFirefox) {
            downloadURL = 'https://addons.mozilla.org/en-US/firefox/addon/ember-inspector/';
          }

          _emberMetalCore["default"].debug('For more advanced debugging, install the Ember Inspector from ' + downloadURL);
        }
      }, false);
    }
  }

  _emberMetalCore["default"].Debug = {
    _addDeprecationLevel: function (id, level) {
      _emberDebugDeprecationManager["default"].setLevel(id, level);
    },
    _deprecationLevels: _emberDebugDeprecationManager.deprecationLevels
  };

  /*
    We are transitioning away from `ember.js` to `ember.debug.js` to make
    it much clearer that it is only for local development purposes.
  
    This flag value is changed by the tooling (by a simple string replacement)
    so that if `ember.js` (which must be output for backwards compat reasons) is
    used a nice helpful warning message will be printed out.
  */
  var runningNonEmberDebugJS = false;
  exports.runningNonEmberDebugJS = runningNonEmberDebugJS;
  if (runningNonEmberDebugJS) {
    _emberMetalCore["default"].warn('Please use `ember.debug.js` instead of `ember.js` for development and debugging.');
  }
});
enifed('ember-debug/deprecation-manager', ['exports', 'ember-metal/dictionary', 'ember-metal/utils'], function (exports, _emberMetalDictionary, _emberMetalUtils) {
  'use strict';

  var deprecationLevels = {
    RAISE: _emberMetalUtils.symbol('RAISE'),
    LOG: _emberMetalUtils.symbol('LOG'),
    SILENCE: _emberMetalUtils.symbol('SILENCE')
  };

  exports.deprecationLevels = deprecationLevels;
  exports["default"] = {
    defaultLevel: deprecationLevels.LOG,
    individualLevels: _emberMetalDictionary["default"](null),
    setDefaultLevel: function (level) {
      this.defaultLevel = level;
    },
    setLevel: function (id, level) {
      this.individualLevels[id] = level;
    },
    getLevel: function (id) {
      var level = this.individualLevels[id];
      if (!level) {
        level = this.defaultLevel;
      }
      return level;
    }
  };
});
enifed("ember-testing", ["exports", "ember-metal/core", "ember-testing/initializers", "ember-testing/support", "ember-testing/setup_for_testing", "ember-testing/test", "ember-testing/adapters/adapter", "ember-testing/adapters/qunit", "ember-testing/helpers"], function (exports, _emberMetalCore, _emberTestingInitializers, _emberTestingSupport, _emberTestingSetup_for_testing, _emberTestingTest, _emberTestingAdaptersAdapter, _emberTestingAdaptersQunit, _emberTestingHelpers) {
  "use strict";

  // adds helpers to helpers object in Test

  /**
    @module ember
    @submodule ember-testing
  */

  _emberMetalCore["default"].Test = _emberTestingTest["default"];
  _emberMetalCore["default"].Test.Adapter = _emberTestingAdaptersAdapter["default"];
  _emberMetalCore["default"].Test.QUnitAdapter = _emberTestingAdaptersQunit["default"];
  _emberMetalCore["default"].setupForTesting = _emberTestingSetup_for_testing["default"];
});
// to setup initializer
// to handle various edge cases
enifed("ember-testing/adapters/adapter", ["exports", "ember-runtime/system/object"], function (exports, _emberRuntimeSystemObject) {
  "use strict";

  function K() {
    return this;
  }

  /**
   @module ember
   @submodule ember-testing
  */

  /**
    The primary purpose of this class is to create hooks that can be implemented
    by an adapter for various test frameworks.
  
    @class Adapter
    @namespace Ember.Test
    @public
  */
  var Adapter = _emberRuntimeSystemObject["default"].extend({
    /**
      This callback will be called whenever an async operation is about to start.
       Override this to call your framework's methods that handle async
      operations.
       @public
      @method asyncStart
    */
    asyncStart: K,

    /**
      This callback will be called whenever an async operation has completed.
       @public
      @method asyncEnd
    */
    asyncEnd: K,

    /**
      Override this method with your testing framework's false assertion.
      This function is called whenever an exception occurs causing the testing
      promise to fail.
       QUnit example:
       ```javascript
        exception: function(error) {
          ok(false, error);
        };
      ```
       @public
      @method exception
      @param {String} error The exception to be raised.
    */
    exception: function (error) {
      throw error;
    }
  });

  exports["default"] = Adapter;
});
enifed("ember-testing/adapters/qunit", ["exports", "ember-testing/adapters/adapter", "ember-metal/utils"], function (exports, _emberTestingAdaptersAdapter, _emberMetalUtils) {
  "use strict";

  /**
    This class implements the methods defined by Ember.Test.Adapter for the
    QUnit testing framework.
  
    @class QUnitAdapter
    @namespace Ember.Test
    @extends Ember.Test.Adapter
    @public
  */
  exports["default"] = _emberTestingAdaptersAdapter["default"].extend({
    asyncStart: function () {
      QUnit.stop();
    },
    asyncEnd: function () {
      QUnit.start();
    },
    exception: function (error) {
      ok(false, _emberMetalUtils.inspect(error));
    }
  });
});
enifed("ember-testing/helpers", ["exports", "ember-metal/core", "ember-metal/property_get", "ember-metal/error", "ember-metal/run_loop", "ember-views/system/jquery", "ember-testing/test", "ember-runtime/ext/rsvp"], function (exports, _emberMetalCore, _emberMetalProperty_get, _emberMetalError, _emberMetalRun_loop, _emberViewsSystemJquery, _emberTestingTest, _emberRuntimeExtRsvp) {
  "use strict";

  /**
  @module ember
  @submodule ember-testing
  */

  var helper = _emberTestingTest["default"].registerHelper;
  var asyncHelper = _emberTestingTest["default"].registerAsyncHelper;

  function currentRouteName(app) {
    var appController = app.__container__.lookup('controller:application');

    return _emberMetalProperty_get.get(appController, 'currentRouteName');
  }

  function currentPath(app) {
    var appController = app.__container__.lookup('controller:application');

    return _emberMetalProperty_get.get(appController, 'currentPath');
  }

  function currentURL(app) {
    var router = app.__container__.lookup('router:main');

    return _emberMetalProperty_get.get(router, 'location').getURL();
  }

  function pauseTest() {
    _emberTestingTest["default"].adapter.asyncStart();
    return new _emberMetalCore["default"].RSVP.Promise(function () {}, 'TestAdapter paused promise');
  }

  function focus(el) {
    if (el && el.is(':input, [contenteditable=true]')) {
      var type = el.prop('type');
      if (type !== 'checkbox' && type !== 'radio' && type !== 'hidden') {
        _emberMetalRun_loop["default"](el, function () {
          // Firefox does not trigger the `focusin` event if the window
          // does not have focus. If the document doesn't have focus just
          // use trigger('focusin') instead.
          if (!document.hasFocus || document.hasFocus()) {
            this.focus();
          } else {
            this.trigger('focusin');
          }
        });
      }
    }
  }

  function visit(app, url) {
    var router = app.__container__.lookup('router:main');
    var shouldHandleURL = false;

    app.boot().then(function () {
      router.location.setURL(url);

      if (shouldHandleURL) {
        _emberMetalRun_loop["default"](app.__deprecatedInstance__, 'handleURL', url);
      }
    });

    if (app._readinessDeferrals > 0) {
      router['initialURL'] = url;
      _emberMetalRun_loop["default"](app, 'advanceReadiness');
      delete router['initialURL'];
    } else {
      shouldHandleURL = true;
    }

    return app.testHelpers.wait();
  }

  function click(app, selector, context) {
    var $el = app.testHelpers.findWithAssert(selector, context);
    _emberMetalRun_loop["default"]($el, 'mousedown');

    focus($el);

    _emberMetalRun_loop["default"]($el, 'mouseup');
    _emberMetalRun_loop["default"]($el, 'click');

    return app.testHelpers.wait();
  }

  function check(app, selector, context) {
    var $el = app.testHelpers.findWithAssert(selector, context);
    var type = $el.prop('type');

    _emberMetalCore["default"].assert('To check \'' + selector + '\', the input must be a checkbox', type === 'checkbox');

    if (!$el.prop('checked')) {
      app.testHelpers.click(selector, context);
    }

    return app.testHelpers.wait();
  }

  function uncheck(app, selector, context) {
    var $el = app.testHelpers.findWithAssert(selector, context);
    var type = $el.prop('type');

    _emberMetalCore["default"].assert('To uncheck \'' + selector + '\', the input must be a checkbox', type === 'checkbox');

    if ($el.prop('checked')) {
      app.testHelpers.click(selector, context);
    }

    return app.testHelpers.wait();
  }

  function triggerEvent(app, selector, contextOrType, typeOrOptions, possibleOptions) {
    var arity = arguments.length;
    var context, type, options;

    if (arity === 3) {
      // context and options are optional, so this is
      // app, selector, type
      context = null;
      type = contextOrType;
      options = {};
    } else if (arity === 4) {
      // context and options are optional, so this is
      if (typeof typeOrOptions === "object") {
        // either
        // app, selector, type, options
        context = null;
        type = contextOrType;
        options = typeOrOptions;
      } else {
        // or
        // app, selector, context, type
        context = contextOrType;
        type = typeOrOptions;
        options = {};
      }
    } else {
      context = contextOrType;
      type = typeOrOptions;
      options = possibleOptions;
    }

    var $el = app.testHelpers.findWithAssert(selector, context);

    var event = _emberViewsSystemJquery["default"].Event(type, options);

    _emberMetalRun_loop["default"]($el, 'trigger', event);

    return app.testHelpers.wait();
  }

  function keyEvent(app, selector, contextOrType, typeOrKeyCode, keyCode) {
    var context, type;

    if (typeof keyCode === 'undefined') {
      context = null;
      keyCode = typeOrKeyCode;
      type = contextOrType;
    } else {
      context = contextOrType;
      type = typeOrKeyCode;
    }

    return app.testHelpers.triggerEvent(selector, context, type, { keyCode: keyCode, which: keyCode });
  }

  function fillIn(app, selector, contextOrText, text) {
    var $el, context;
    if (typeof text === 'undefined') {
      text = contextOrText;
    } else {
      context = contextOrText;
    }
    $el = app.testHelpers.findWithAssert(selector, context);
    focus($el);
    _emberMetalRun_loop["default"](function () {
      $el.val(text).change();
    });
    return app.testHelpers.wait();
  }

  function findWithAssert(app, selector, context) {
    var $el = app.testHelpers.find(selector, context);
    if ($el.length === 0) {
      throw new _emberMetalError["default"]("Element " + selector + " not found.");
    }
    return $el;
  }

  function find(app, selector, context) {
    var $el;
    context = context || _emberMetalProperty_get.get(app, 'rootElement');
    $el = app.$(selector, context);

    return $el;
  }

  function andThen(app, callback) {
    return app.testHelpers.wait(callback(app));
  }

  function wait(app, value) {
    return new _emberRuntimeExtRsvp["default"].Promise(function (resolve) {
      // Every 10ms, poll for the async thing to have finished
      var watcher = setInterval(function () {
        var router = app.__container__.lookup('router:main');

        // 1. If the router is loading, keep polling
        var routerIsLoading = router.router && !!router.router.activeTransition;
        if (routerIsLoading) {
          return;
        }

        // 2. If there are pending Ajax requests, keep polling
        if (_emberTestingTest["default"].pendingAjaxRequests) {
          return;
        }

        // 3. If there are scheduled timers or we are inside of a run loop, keep polling
        if (_emberMetalRun_loop["default"].hasScheduledTimers() || _emberMetalRun_loop["default"].currentRunLoop) {
          return;
        }
        if (_emberTestingTest["default"].waiters && _emberTestingTest["default"].waiters.any(function (waiter) {
          var context = waiter[0];
          var callback = waiter[1];
          return !callback.call(context);
        })) {
          return;
        }
        // Stop polling
        clearInterval(watcher);

        // Synchronously resolve the promise
        _emberMetalRun_loop["default"](null, resolve, value);
      }, 10);
    });
  }

  /**
    Loads a route, sets up any controllers, and renders any templates associated
    with the route as though a real user had triggered the route change while
    using your app.
  
    Example:
  
    ```javascript
    visit('posts/index').then(function() {
      // assert something
    });
    ```
  
    @method visit
    @param {String} url the name of the route
    @return {RSVP.Promise}
    @public
  */
  asyncHelper('visit', visit);

  /**
    Clicks an element and triggers any actions triggered by the element's `click`
    event.
  
    Example:
  
    ```javascript
    click('.some-jQuery-selector').then(function() {
      // assert something
    });
    ```
  
    @method click
    @param {String} selector jQuery selector for finding element on the DOM
    @return {RSVP.Promise}
    @public
  */
  asyncHelper('click', click);

    /**
    Simulates a key event, e.g. `keypress`, `keydown`, `keyup` with the desired keyCode
  
    Example:
  
    ```javascript
    keyEvent('.some-jQuery-selector', 'keypress', 13).then(function() {
     // assert something
    });
    ```
  
    @method keyEvent
    @param {String} selector jQuery selector for finding element on the DOM
    @param {String} type the type of key event, e.g. `keypress`, `keydown`, `keyup`
    @param {Number} keyCode the keyCode of the simulated key event
    @return {RSVP.Promise}
    @since 1.5.0
    @public
  */
  asyncHelper('keyEvent', keyEvent);

  /**
    Fills in an input element with some text.
  
    Example:
  
    ```javascript
    fillIn('#email', 'you@example.com').then(function() {
      // assert something
    });
    ```
  
    @method fillIn
    @param {String} selector jQuery selector finding an input element on the DOM
    to fill text with
    @param {String} text text to place inside the input element
    @return {RSVP.Promise}
    @public
  */
  asyncHelper('fillIn', fillIn);

  /**
    Finds an element in the context of the app's container element. A simple alias
    for `app.$(selector)`.
  
    Example:
  
    ```javascript
    var $el = find('.my-selector');
    ```
  
    @method find
    @param {String} selector jQuery string selector for element lookup
    @return {Object} jQuery object representing the results of the query
    @public
  */
  helper('find', find);

  /**
    Like `find`, but throws an error if the element selector returns no results.
  
    Example:
  
    ```javascript
    var $el = findWithAssert('.doesnt-exist'); // throws error
    ```
  
    @method findWithAssert
    @param {String} selector jQuery selector string for finding an element within
    the DOM
    @return {Object} jQuery object representing the results of the query
    @throws {Error} throws error if jQuery object returned has a length of 0
    @public
  */
  helper('findWithAssert', findWithAssert);

  /**
    Causes the run loop to process any pending events. This is used to ensure that
    any async operations from other helpers (or your assertions) have been processed.
  
    This is most often used as the return value for the helper functions (see 'click',
    'fillIn','visit',etc).
  
    Example:
  
    ```javascript
    Ember.Test.registerAsyncHelper('loginUser', function(app, username, password) {
      visit('secured/path/here')
      .fillIn('#username', username)
      .fillIn('#password', password)
      .click('.submit')
  
      return app.testHelpers.wait();
    });
  
    @method wait
    @param {Object} value The value to be returned.
    @return {RSVP.Promise}
    @public
  */
  asyncHelper('wait', wait);
  asyncHelper('andThen', andThen);

  /**
    Returns the currently active route name.
  
  Example:
  
  ```javascript
  function validateRouteName() {
    equal(currentRouteName(), 'some.path', "correct route was transitioned into.");
  }
  
  visit('/some/path').then(validateRouteName)
  ```
  
  @method currentRouteName
  @return {Object} The name of the currently active route.
  @since 1.5.0
  @public
  */
  helper('currentRouteName', currentRouteName);

  /**
    Returns the current path.
  
  Example:
  
  ```javascript
  function validateURL() {
    equal(currentPath(), 'some.path.index', "correct path was transitioned into.");
  }
  
  click('#some-link-id').then(validateURL);
  ```
  
  @method currentPath
  @return {Object} The currently active path.
  @since 1.5.0
  @public
  */
  helper('currentPath', currentPath);

  /**
    Returns the current URL.
  
  Example:
  
  ```javascript
  function validateURL() {
    equal(currentURL(), '/some/path', "correct URL was transitioned into.");
  }
  
  click('#some-link-id').then(validateURL);
  ```
  
  @method currentURL
  @return {Object} The currently active URL.
  @since 1.5.0
  @public
  */
  helper('currentURL', currentURL);

  /**
   Pauses the current test - this is useful for debugging while testing or for test-driving.
   It allows you to inspect the state of your application at any point.
  
   Example (The test will pause before clicking the button):
  
   ```javascript
   visit('/')
   return pauseTest();
  
   click('.btn');
   ```
  
   @since 1.9.0
   @method pauseTest
   @return {Object} A promise that will never resolve
   @public
  */
  helper('pauseTest', pauseTest);

  /**
    Triggers the given DOM event on the element identified by the provided selector.
  
    Example:
  
    ```javascript
    triggerEvent('#some-elem-id', 'blur');
    ```
  
    This is actually used internally by the `keyEvent` helper like so:
  
    ```javascript
    triggerEvent('#some-elem-id', 'keypress', { keyCode: 13 });
    ```
  
   @method triggerEvent
   @param {String} selector jQuery selector for finding element on the DOM
   @param {String} [context] jQuery selector that will limit the selector
                             argument to find only within the context's children
   @param {String} type The event type to be triggered.
   @param {Object} [options] The options to be passed to jQuery.Event.
   @return {RSVP.Promise}
   @since 1.5.0
   @public
  */
  asyncHelper('triggerEvent', triggerEvent);
});
enifed('ember-testing/initializers', ['exports', 'ember-runtime/system/lazy_load'], function (exports, _emberRuntimeSystemLazy_load) {
  'use strict';

  var name = 'deferReadiness in `testing` mode';

  _emberRuntimeSystemLazy_load.onLoad('Ember.Application', function (Application) {
    if (!Application.initializers[name]) {
      Application.initializer({
        name: name,

        initialize: function (registry, application) {
          if (application.testing) {
            application.deferReadiness();
          }
        }
      });
    }
  });
});
enifed("ember-testing/setup_for_testing", ["exports", "ember-metal/core", "ember-testing/adapters/qunit", "ember-views/system/jquery"], function (exports, _emberMetalCore, _emberTestingAdaptersQunit, _emberViewsSystemJquery) {
  "use strict";

  exports["default"] = setupForTesting;

  var Test, requests;

  function incrementAjaxPendingRequests(_, xhr) {
    requests.push(xhr);
    Test.pendingAjaxRequests = requests.length;
  }

  function decrementAjaxPendingRequests(_, xhr) {
    for (var i = 0; i < requests.length; i++) {
      if (xhr === requests[i]) {
        requests.splice(i, 1);
      }
    }
    Test.pendingAjaxRequests = requests.length;
  }

  /**
    Sets Ember up for testing. This is useful to perform
    basic setup steps in order to unit test.
  
    Use `App.setupForTesting` to perform integration tests (full
    application testing).
  
    @method setupForTesting
    @namespace Ember
    @since 1.5.0
    @private
  */

  function setupForTesting() {
    if (!Test) {
      Test = requireModule('ember-testing/test')['default'];
    }

    _emberMetalCore["default"].testing = true;

    // if adapter is not manually set default to QUnit
    if (!Test.adapter) {
      Test.adapter = _emberTestingAdaptersQunit["default"].create();
    }

    requests = [];
    Test.pendingAjaxRequests = requests.length;

    _emberViewsSystemJquery["default"](document).off('ajaxSend', incrementAjaxPendingRequests);
    _emberViewsSystemJquery["default"](document).off('ajaxComplete', decrementAjaxPendingRequests);
    _emberViewsSystemJquery["default"](document).on('ajaxSend', incrementAjaxPendingRequests);
    _emberViewsSystemJquery["default"](document).on('ajaxComplete', decrementAjaxPendingRequests);
  }
});

// import Test from "ember-testing/test";  // ES6TODO: fix when cycles are supported
enifed("ember-testing/support", ["exports", "ember-metal/core", "ember-views/system/jquery", "ember-metal/environment"], function (exports, _emberMetalCore, _emberViewsSystemJquery, _emberMetalEnvironment) {
  "use strict";

  /**
    @module ember
    @submodule ember-testing
  */

  var $ = _emberViewsSystemJquery["default"];

  /**
    This method creates a checkbox and triggers the click event to fire the
    passed in handler. It is used to correct for a bug in older versions
    of jQuery (e.g 1.8.3).
  
    @private
    @method testCheckboxClick
  */
  function testCheckboxClick(handler) {
    $('<input type="checkbox">').css({ position: 'absolute', left: '-1000px', top: '-1000px' }).appendTo('body').on('click', handler).trigger('click').remove();
  }

  if (_emberMetalEnvironment["default"].hasDOM) {
    $(function () {
      /*
        Determine whether a checkbox checked using jQuery's "click" method will have
        the correct value for its checked property.
         If we determine that the current jQuery version exhibits this behavior,
        patch it to work correctly as in the commit for the actual fix:
        https://github.com/jquery/jquery/commit/1fb2f92.
      */
      testCheckboxClick(function () {
        if (!this.checked && !$.event.special.click) {
          $.event.special.click = {
            // For checkbox, fire native event so checked state will be right
            trigger: function () {
              if ($.nodeName(this, "input") && this.type === "checkbox" && this.click) {
                this.click();
                return false;
              }
            }
          };
        }
      });

      // Try again to verify that the patch took effect or blow up.
      testCheckboxClick(function () {
        _emberMetalCore["default"].warn("clicked checkboxes should be checked! the jQuery patch didn't work", this.checked);
      });
    });
  }
});
enifed("ember-testing/test", ["exports", "ember-metal/core", "ember-metal/run_loop", "ember-metal/platform/create", "ember-runtime/ext/rsvp", "ember-testing/setup_for_testing", "ember-application/system/application"], function (exports, _emberMetalCore, _emberMetalRun_loop, _emberMetalPlatformCreate, _emberRuntimeExtRsvp, _emberTestingSetup_for_testing, _emberApplicationSystemApplication) {
  "use strict";

  /**
    @module ember
    @submodule ember-testing
  */
  var helpers = {};
  var injectHelpersCallbacks = [];

  /**
    This is a container for an assortment of testing related functionality:
  
    * Choose your default test adapter (for your framework of choice).
    * Register/Unregister additional test helpers.
    * Setup callbacks to be fired when the test helpers are injected into
      your application.
  
    @class Test
    @namespace Ember
    @public
  */
  var Test = {
    /**
      Hash containing all known test helpers.
       @property _helpers
      @private
      @since 1.7.0
    */
    _helpers: helpers,

    /**
      `registerHelper` is used to register a test helper that will be injected
      when `App.injectTestHelpers` is called.
       The helper method will always be called with the current Application as
      the first parameter.
       For example:
       ```javascript
      Ember.Test.registerHelper('boot', function(app) {
        Ember.run(app, app.advanceReadiness);
      });
      ```
       This helper can later be called without arguments because it will be
      called with `app` as the first parameter.
       ```javascript
      App = Ember.Application.create();
      App.injectTestHelpers();
      boot();
      ```
       @public
      @method registerHelper
      @param {String} name The name of the helper method to add.
      @param {Function} helperMethod
      @param options {Object}
    */
    registerHelper: function (name, helperMethod) {
      helpers[name] = {
        method: helperMethod,
        meta: { wait: false }
      };
    },

    /**
      `registerAsyncHelper` is used to register an async test helper that will be injected
      when `App.injectTestHelpers` is called.
       The helper method will always be called with the current Application as
      the first parameter.
       For example:
       ```javascript
      Ember.Test.registerAsyncHelper('boot', function(app) {
        Ember.run(app, app.advanceReadiness);
      });
      ```
       The advantage of an async helper is that it will not run
      until the last async helper has completed.  All async helpers
      after it will wait for it complete before running.
        For example:
       ```javascript
      Ember.Test.registerAsyncHelper('deletePost', function(app, postId) {
        click('.delete-' + postId);
      });
       // ... in your test
      visit('/post/2');
      deletePost(2);
      visit('/post/3');
      deletePost(3);
      ```
       @public
      @method registerAsyncHelper
      @param {String} name The name of the helper method to add.
      @param {Function} helperMethod
      @since 1.2.0
    */
    registerAsyncHelper: function (name, helperMethod) {
      helpers[name] = {
        method: helperMethod,
        meta: { wait: true }
      };
    },

    /**
      Remove a previously added helper method.
       Example:
       ```javascript
      Ember.Test.unregisterHelper('wait');
      ```
       @public
      @method unregisterHelper
      @param {String} name The helper to remove.
    */
    unregisterHelper: function (name) {
      delete helpers[name];
      delete Test.Promise.prototype[name];
    },

    /**
      Used to register callbacks to be fired whenever `App.injectTestHelpers`
      is called.
       The callback will receive the current application as an argument.
       Example:
       ```javascript
      Ember.Test.onInjectHelpers(function() {
        Ember.$(document).ajaxSend(function() {
          Test.pendingAjaxRequests++;
        });
         Ember.$(document).ajaxComplete(function() {
          Test.pendingAjaxRequests--;
        });
      });
      ```
       @public
      @method onInjectHelpers
      @param {Function} callback The function to be called.
    */
    onInjectHelpers: function (callback) {
      injectHelpersCallbacks.push(callback);
    },

    /**
      This returns a thenable tailored for testing.  It catches failed
      `onSuccess` callbacks and invokes the `Ember.Test.adapter.exception`
      callback in the last chained then.
       This method should be returned by async helpers such as `wait`.
       @public
      @method promise
      @param {Function} resolver The function used to resolve the promise.
      @param {String} label An optional string for identifying the promise.
    */
    promise: function (resolver, label) {
      var fullLabel = "Ember.Test.promise: " + (label || "<Unknown Promise>");
      return new Test.Promise(resolver, fullLabel);
    },

    /**
     Used to allow ember-testing to communicate with a specific testing
     framework.
      You can manually set it before calling `App.setupForTesting()`.
      Example:
      ```javascript
     Ember.Test.adapter = MyCustomAdapter.create()
     ```
      If you do not set it, ember-testing will default to `Ember.Test.QUnitAdapter`.
      @public
     @property adapter
     @type {Class} The adapter to be used.
     @default Ember.Test.QUnitAdapter
    */
    adapter: null,

    /**
      Replacement for `Ember.RSVP.resolve`
      The only difference is this uses
      an instance of `Ember.Test.Promise`
       @public
      @method resolve
      @param {Mixed} The value to resolve
      @since 1.2.0
    */
    resolve: function (val) {
      return Test.promise(function (resolve) {
        return resolve(val);
      });
    },

    /**
       This allows ember-testing to play nicely with other asynchronous
       events, such as an application that is waiting for a CSS3
       transition or an IndexDB transaction.
        For example:
        ```javascript
       Ember.Test.registerWaiter(function() {
         return myPendingTransactions() == 0;
       });
       ```
       The `context` argument allows you to optionally specify the `this`
       with which your callback will be invoked.
        For example:
        ```javascript
       Ember.Test.registerWaiter(MyDB, MyDB.hasPendingTransactions);
       ```
        @public
       @method registerWaiter
       @param {Object} context (optional)
       @param {Function} callback
       @since 1.2.0
    */
    registerWaiter: function (context, callback) {
      if (arguments.length === 1) {
        callback = context;
        context = null;
      }
      if (!this.waiters) {
        this.waiters = _emberMetalCore["default"].A();
      }
      this.waiters.push([context, callback]);
    },
    /**
       `unregisterWaiter` is used to unregister a callback that was
       registered with `registerWaiter`.
        @public
       @method unregisterWaiter
       @param {Object} context (optional)
       @param {Function} callback
       @since 1.2.0
    */
    unregisterWaiter: function (context, callback) {
      if (!this.waiters) {
        return;
      }
      if (arguments.length === 1) {
        callback = context;
        context = null;
      }
      this.waiters = _emberMetalCore["default"].A(this.waiters.filter(function (elt) {
        return !(elt[0] === context && elt[1] === callback);
      }));
    }
  };

  function helper(app, name) {
    var fn = helpers[name].method;
    var meta = helpers[name].meta;

    return function () {
      for (var _len = arguments.length, args = Array(_len), _key = 0; _key < _len; _key++) {
        args[_key] = arguments[_key];
      }

      var lastPromise;

      args.unshift(app);

      // some helpers are not async and
      // need to return a value immediately.
      // example: `find`
      if (!meta.wait) {
        return fn.apply(app, args);
      }

      lastPromise = run(function () {
        return Test.resolve(Test.lastPromise);
      });

      // wait for last helper's promise to resolve and then
      // execute. To be safe, we need to tell the adapter we're going
      // asynchronous here, because fn may not be invoked before we
      // return.
      Test.adapter.asyncStart();
      return lastPromise.then(function () {
        return fn.apply(app, args);
      })["finally"](function () {
        Test.adapter.asyncEnd();
      });
    };
  }

  function run(fn) {
    if (!_emberMetalRun_loop["default"].currentRunLoop) {
      return _emberMetalRun_loop["default"](fn);
    } else {
      return fn();
    }
  }

  _emberApplicationSystemApplication["default"].reopen({
    /**
     This property contains the testing helpers for the current application. These
     are created once you call `injectTestHelpers` on your `Ember.Application`
     instance. The included helpers are also available on the `window` object by
     default, but can be used from this object on the individual application also.
       @property testHelpers
      @type {Object}
      @default {}
      @public
    */
    testHelpers: {},

    /**
     This property will contain the original methods that were registered
     on the `helperContainer` before `injectTestHelpers` is called.
      When `removeTestHelpers` is called, these methods are restored to the
     `helperContainer`.
       @property originalMethods
      @type {Object}
      @default {}
      @private
      @since 1.3.0
    */
    originalMethods: {},

    /**
    This property indicates whether or not this application is currently in
    testing mode. This is set when `setupForTesting` is called on the current
    application.
     @property testing
    @type {Boolean}
    @default false
    @since 1.3.0
    @public
    */
    testing: false,

    /**
      This hook defers the readiness of the application, so that you can start
      the app when your tests are ready to run. It also sets the router's
      location to 'none', so that the window's location will not be modified
      (preventing both accidental leaking of state between tests and interference
      with your testing framework).
       Example:
       ```
      App.setupForTesting();
      ```
       @method setupForTesting
      @public
    */
    setupForTesting: function () {
      _emberTestingSetup_for_testing["default"]();

      this.testing = true;

      this.Router.reopen({
        location: 'none'
      });
    },

    /**
      This will be used as the container to inject the test helpers into. By
      default the helpers are injected into `window`.
       @property helperContainer
      @type {Object} The object to be used for test helpers.
      @default window
      @since 1.2.0
      @private
    */
    helperContainer: null,

    /**
      This injects the test helpers into the `helperContainer` object. If an object is provided
      it will be used as the helperContainer. If `helperContainer` is not set it will default
      to `window`. If a function of the same name has already been defined it will be cached
      (so that it can be reset if the helper is removed with `unregisterHelper` or
      `removeTestHelpers`).
       Any callbacks registered with `onInjectHelpers` will be called once the
      helpers have been injected.
       Example:
      ```
      App.injectTestHelpers();
      ```
       @method injectTestHelpers
      @public
    */
    injectTestHelpers: function (helperContainer) {
      if (helperContainer) {
        this.helperContainer = helperContainer;
      } else {
        this.helperContainer = window;
      }

      this.reopen({
        willDestroy: function () {
          this._super.apply(this, arguments);
          this.removeTestHelpers();
        }
      });

      this.testHelpers = {};
      for (var name in helpers) {
        this.originalMethods[name] = this.helperContainer[name];
        this.testHelpers[name] = this.helperContainer[name] = helper(this, name);
        protoWrap(Test.Promise.prototype, name, helper(this, name), helpers[name].meta.wait);
      }

      for (var i = 0, l = injectHelpersCallbacks.length; i < l; i++) {
        injectHelpersCallbacks[i](this);
      }
    },

    /**
      This removes all helpers that have been registered, and resets and functions
      that were overridden by the helpers.
       Example:
       ```javascript
      App.removeTestHelpers();
      ```
       @public
      @method removeTestHelpers
    */
    removeTestHelpers: function () {
      if (!this.helperContainer) {
        return;
      }

      for (var name in helpers) {
        this.helperContainer[name] = this.originalMethods[name];
        delete Test.Promise.prototype[name];
        delete this.testHelpers[name];
        delete this.originalMethods[name];
      }
    }
  });

  // This method is no longer needed
  // But still here for backwards compatibility
  // of helper chaining
  function protoWrap(proto, name, callback, isAsync) {
    proto[name] = function () {
      for (var _len2 = arguments.length, args = Array(_len2), _key2 = 0; _key2 < _len2; _key2++) {
        args[_key2] = arguments[_key2];
      }

      if (isAsync) {
        return callback.apply(this, args);
      } else {
        return this.then(function () {
          return callback.apply(this, args);
        });
      }
    };
  }

  Test.Promise = function () {
    _emberRuntimeExtRsvp["default"].Promise.apply(this, arguments);
    Test.lastPromise = this;
  };

  Test.Promise.prototype = _emberMetalPlatformCreate["default"](_emberRuntimeExtRsvp["default"].Promise.prototype);
  Test.Promise.prototype.constructor = Test.Promise;
  Test.Promise.resolve = Test.resolve;

  // Patch `then` to isolate async methods
  // specifically `Ember.Test.lastPromise`
  var originalThen = _emberRuntimeExtRsvp["default"].Promise.prototype.then;
  Test.Promise.prototype.then = function (onSuccess, onFailure) {
    return originalThen.call(this, function (val) {
      return isolate(onSuccess, val);
    }, onFailure);
  };

  // This method isolates nested async methods
  // so that they don't conflict with other last promises.
  //
  // 1. Set `Ember.Test.lastPromise` to null
  // 2. Invoke method
  // 3. Return the last promise created during method
  function isolate(fn, val) {
    var value, lastPromise;

    // Reset lastPromise for nested helpers
    Test.lastPromise = null;

    value = fn(val);

    lastPromise = Test.lastPromise;
    Test.lastPromise = null;

    // If the method returned a promise
    // return that promise. If not,
    // return the last async helper's promise
    if (value && value instanceof Test.Promise || !lastPromise) {
      return value;
    } else {
      return run(function () {
        return Test.resolve(lastPromise).then(function () {
          return value;
        });
      });
    }
  }

  exports["default"] = Test;
});
requireModule("ember-testing");

})();
define('ember-qunit', ['exports', 'ember-qunit/module-for', 'ember-qunit/module-for-component', 'ember-qunit/module-for-model', 'ember-qunit/test', 'ember-test-helpers'], function (exports, moduleFor, moduleForComponent, moduleForModel, test, ember_test_helpers) {

  'use strict';



  exports.moduleFor = moduleFor['default'];
  exports.moduleForComponent = moduleForComponent['default'];
  exports.moduleForModel = moduleForModel['default'];
  exports.test = test['default'];
  exports.setResolver = ember_test_helpers.setResolver;

});
define('ember-qunit/module-for-component', ['exports', 'ember-qunit/qunit-module', 'ember-test-helpers'], function (exports, qunit_module, ember_test_helpers) {

  'use strict';

  function moduleForComponent(name, description, callbacks) {
    qunit_module.createModule(ember_test_helpers.TestModuleForComponent, name, description, callbacks);
  }
  exports['default'] = moduleForComponent;

});
define('ember-qunit/module-for-model', ['exports', 'ember-qunit/qunit-module', 'ember-test-helpers'], function (exports, qunit_module, ember_test_helpers) {

  'use strict';

  function moduleForModel(name, description, callbacks) {
    qunit_module.createModule(ember_test_helpers.TestModuleForModel, name, description, callbacks);
  }
  exports['default'] = moduleForModel;

});
define('ember-qunit/module-for', ['exports', 'ember-qunit/qunit-module', 'ember-test-helpers'], function (exports, qunit_module, ember_test_helpers) {

  'use strict';

  function moduleFor(name, description, callbacks) {
    qunit_module.createModule(ember_test_helpers.TestModule, name, description, callbacks);
  }
  exports['default'] = moduleFor;

});
define('ember-qunit/qunit-module', ['exports', 'qunit'], function (exports, qunit) {

  'use strict';

  exports.createModule = createModule;

  function beforeEachCallback(callbacks) {
    if (typeof callbacks !== 'object') { return; }
    if (!callbacks) { return; }

    var beforeEach;
    
    if (callbacks.setup) {
      beforeEach = callbacks.setup;
      delete callbacks.setup;
    }

    if (callbacks.beforeEach) {
      beforeEach = callbacks.beforeEach;
      delete callbacks.beforeEach;
    }

    return beforeEach;
  }

  function afterEachCallback(callbacks) {
    if (typeof callbacks !== 'object') { return; }
    if (!callbacks) { return; }

    var afterEach;

    if (callbacks.teardown) {
      afterEach = callbacks.teardown;
      delete callbacks.teardown;
    }

    if (callbacks.afterEach) {
      afterEach = callbacks.afterEach;
      delete callbacks.afterEach;
    }

    return afterEach;
  }

  function createModule(Constructor, name, description, callbacks) {
    var beforeEach = beforeEachCallback(callbacks || description);
    var afterEach  = afterEachCallback(callbacks || description);

    var module = new Constructor(name, description, callbacks);

    qunit.module(module.name, {
      setup: function(assert) {
        var done = assert.async();
        module.setup().then(function() {
          if (beforeEach) {
            beforeEach.call(module.context, assert);
          }
        })['finally'](done);
      },

      teardown: function(assert) {
        if (afterEach) {
          afterEach.call(module.context, assert);
        }
        var done = assert.async();
        module.teardown()['finally'](done);
      }
    });
  }

});
define('ember-qunit/test', ['exports', 'ember', 'ember-test-helpers', 'qunit'], function (exports, Ember, ember_test_helpers, qunit) {

  'use strict';

  function test(testName, callback) {
    function wrapper(assert) {
      var context = ember_test_helpers.getContext();

      var result = callback.call(context, assert);

      function failTestOnPromiseRejection(reason) {
        var message;
        if (reason instanceof Error) {
          message = reason.stack;
        } else {
          message = Ember['default'].inspect(reason);
        }
        ok(false, message);
      }

      Ember['default'].run(function(){
        QUnit.stop();
        Ember['default'].RSVP.Promise.resolve(result)['catch'](failTestOnPromiseRejection)['finally'](QUnit.start);
      });
    }

    qunit.test(testName, wrapper);
  }
  exports['default'] = test;

});
define('ember-test-helpers', ['exports', 'ember', 'ember-test-helpers/test-module', 'ember-test-helpers/test-module-for-component', 'ember-test-helpers/test-module-for-model', 'ember-test-helpers/test-context', 'ember-test-helpers/test-resolver'], function (exports, Ember, TestModule, TestModuleForComponent, TestModuleForModel, test_context, test_resolver) {

  'use strict';

  Ember['default'].testing = true;

  exports.TestModule = TestModule['default'];
  exports.TestModuleForComponent = TestModuleForComponent['default'];
  exports.TestModuleForModel = TestModuleForModel['default'];
  exports.getContext = test_context.getContext;
  exports.setContext = test_context.setContext;
  exports.setResolver = test_resolver.setResolver;

});
define('ember-test-helpers/build-registry', ['exports'], function (exports) {

  'use strict';

  function exposeRegistryMethodsWithoutDeprecations(container) {
    var methods = [
      'register',
      'unregister',
      'resolve',
      'normalize',
      'typeInjection',
      'injection',
      'factoryInjection',
      'factoryTypeInjection',
      'has',
      'options',
      'optionsForType'
    ];

    function exposeRegistryMethod(container, method) {
      if (method in container) {
        container[method] = function() {
          return container._registry[method].apply(container._registry, arguments);
        };
      }
    }

    for (var i = 0, l = methods.length; i < l; i++) {
      exposeRegistryMethod(container, methods[i]);
    }
  }

  exports['default'] = function(resolver) {
    var registry, container;
    var namespace = Ember.Object.create({
      Resolver: { create: function() { return resolver; } }
    });

    function register(name, factory) {
      var thingToRegisterWith = registry || container;

      if (!container.lookupFactory(name)) {
        thingToRegisterWith.register(name, factory);
      }
    }

    if (Ember.Application.buildRegistry) {
      registry = Ember.Application.buildRegistry(namespace);
      registry.register('component-lookup:main', Ember.ComponentLookup);

      registry = registry;
      container = registry.container();
      exposeRegistryMethodsWithoutDeprecations(container);
    } else {
      container = Ember.Application.buildContainer(namespace);
      container.register('component-lookup:main', Ember.ComponentLookup);
    }

    // Ember 1.10.0 did not properly add `view:toplevel` or `view:default`
    // to the registry in Ember.Application.buildRegistry :(
    //
    // Ember 2.0.0 removed Ember.View as public API, so only do this when
    // Ember.View is present
    if (Ember.View) {
      register('view:toplevel', Ember.View.extend());
    }

    // Ember 2.0.0 removed Ember._MetamorphView from the Ember global, so only
    // do this when present
    if (Ember._MetamorphView) {
      register('view:default', Ember._MetamorphView);
    }

    var globalContext = typeof global === 'object' && global || self;
    if (globalContext.DS) {
      var DS = globalContext.DS;
      if (DS._setupContainer) {
        DS._setupContainer(registry || container);
      } else {
        register('transform:boolean', DS.BooleanTransform);
        register('transform:date', DS.DateTransform);
        register('transform:number', DS.NumberTransform);
        register('transform:string', DS.StringTransform);
        register('serializer:-default', DS.JSONSerializer);
        register('serializer:-rest', DS.RESTSerializer);
        register('adapter:-rest', DS.RESTAdapter);
      }
    }

    return {
      registry: registry,
      container: container
    };
  }

});
define('ember-test-helpers/isolated-container', function () {

	'use strict';

});
define('ember-test-helpers/test-context', ['exports'], function (exports) {

  'use strict';

  exports.setContext = setContext;
  exports.getContext = getContext;
  exports.unsetContext = unsetContext;

  var __test_context__;

  function setContext(context) {
    __test_context__ = context;
  }

  function getContext() {
    return __test_context__;
  }

  function unsetContext() {
    __test_context__ = undefined;
  }

});
define('ember-test-helpers/test-module-for-component', ['exports', 'ember-test-helpers/test-module', 'ember', 'ember-test-helpers/test-resolver'], function (exports, TestModule, Ember, test_resolver) {

  'use strict';

  exports['default'] = TestModule['default'].extend({
    init: function(componentName, description, callbacks) {
      // Allow `description` to be omitted
      if (!callbacks && typeof description === 'object') {
        callbacks = description;
        description = null;
      } else if (!callbacks) {
        callbacks = {};
      }

      this.componentName = componentName;

      if (callbacks.needs || callbacks.unit || callbacks.integration === false) {
        this.isUnitTest = true;
      } else if (callbacks.integration) {
        this.isUnitTest = false;
      } else {
        Ember['default'].deprecate("the component:" + componentName + " test module is implicitly running in unit test mode, which will change to integration test mode by default in an upcoming version of ember-test-helpers. Add `unit: true` or a `needs:[]` list to explicitly opt in to unit test mode.");
        this.isUnitTest = true;
      }

      if (!this.isUnitTest) {
        callbacks.integration = true;
      }

      if (description) {
        this._super.call(this, 'component:' + componentName, description, callbacks);
      } else {
        this._super.call(this, 'component:' + componentName, callbacks);
      }

      if (this.isUnitTest) {
        this.setupSteps.push(this.setupComponentUnitTest);
      } else {
        this.callbacks.subject = function() {
          throw new Error("component integration tests do not support `subject()`.");
        };
        this.setupSteps.push(this.setupComponentIntegrationTest);
        this.teardownSteps.push(this.teardownComponent);
      }

      if (Ember['default'].View && Ember['default'].View.views) {
        this.setupSteps.push(this._aliasViewRegistry);
        this.teardownSteps.push(this._resetViewRegistry);
      }
    },

    _aliasViewRegistry: function() {
      this._originalGlobalViewRegistry = Ember['default'].View.views;
      var viewRegistry = this.container.lookup('-view-registry:main');

      if (viewRegistry) {
        Ember['default'].View.views = viewRegistry;
      }
    },

    _resetViewRegistry: function() {
      Ember['default'].View.views = this._originalGlobalViewRegistry;
    },

    setupComponentUnitTest: function() {
      var _this = this;
      var resolver = test_resolver.getResolver();
      var context = this.context;

      var layoutName = 'template:components/' + this.componentName;

      var layout = resolver.resolve(layoutName);

      var thingToRegisterWith = this.registry || this.container;
      if (layout) {
        thingToRegisterWith.register(layoutName, layout);
        thingToRegisterWith.injection(this.subjectName, 'layout', layoutName);
      }

      context.dispatcher = this.container.lookup('event_dispatcher:main') || Ember['default'].EventDispatcher.create();
      context.dispatcher.setup({}, '#ember-testing');

      this.callbacks.render = function() {
        var subject;

        Ember['default'].run(function(){
          subject = context.subject();
          subject.appendTo('#ember-testing');
        });

        _this.teardownSteps.unshift(function() {
          Ember['default'].run(function() {
            Ember['default'].tryInvoke(subject, 'destroy');
          });
        });
      };

      this.callbacks.append = function() {
        Ember['default'].deprecate('this.append() is deprecated. Please use this.render() or this.$() instead.');
        return context.$();
      };

      context.$ = function() {
        this.render();
        var subject = this.subject();

        return subject.$.apply(subject, arguments);
      };
    },

    setupComponentIntegrationTest: function() {
      var module = this;
      var context = this.context;

      this.actionHooks = {};

      context.dispatcher = this.container.lookup('event_dispatcher:main') || Ember['default'].EventDispatcher.create();
      context.dispatcher.setup({}, '#ember-testing');
      context.actions = module.actionHooks;

      (this.registry || this.container).register('component:-test-holder', Ember['default'].Component.extend());

      context.render = function(template) {
        if (!template) {
          throw new Error("in a component integration test you must pass a template to `render()`");
        }
        if (Ember['default'].isArray(template)) {
          template = template.join('');
        }
        if (typeof template === 'string') {
          template = Ember['default'].Handlebars.compile(template);
        }
        module.component = module.container.lookupFactory('component:-test-holder').create({
          layout: template
        });

        module.component.set('context' ,context);
        module.component.set('controller', module);

        Ember['default'].run(function() {
          module.component.appendTo('#ember-testing');
        });
      };

      context.$ = function() {
        return module.component.$.apply(module.component, arguments);
      };

      context.set = function(key, value) {
        Ember['default'].run(function() {
          Ember['default'].set(context, key, value);
        });
      };

      context.setProperties = function(hash) {
        Ember['default'].run(function() {
          Ember['default'].setProperties(context, hash);
        });
      };

      context.get = function(key) {
        return Ember['default'].get(context, key);
      };

      context.getProperties = function() {
        var args = Array.prototype.slice.call(arguments);
        return Ember['default'].getProperties(context, args);
      };

      context.on = function(actionName, handler) {
        module.actionHooks[actionName] = handler;
      };

    },

    setupContext: function() {
      this._super.call(this);

      // only setup the injection if we are running against a version
      // of Ember that has `-view-registry:main` (Ember >= 1.12)
      if (this.container.lookupFactory('-view-registry:main')) {
        (this.registry || this.container).injection('component', '_viewRegistry', '-view-registry:main');
      }

      if (!this.isUnitTest) {
        this.context.factory = function() {};
      }
    },

    send: function(actionName) {
      var hook = this.actionHooks[actionName];
      if (!hook) {
        throw new Error("integration testing template received unexpected action " + actionName);
      }
      hook.apply(this, Array.prototype.slice.call(arguments, 1));
    },

    teardownComponent: function() {
      var component = this.component;
      if (component) {
        Ember['default'].run(function() {
          component.destroy();
        });
      }
    }
  });

});
define('ember-test-helpers/test-module-for-model', ['exports', 'ember-test-helpers/test-module', 'ember'], function (exports, TestModule, Ember) {

  'use strict';

  exports['default'] = TestModule['default'].extend({
    init: function(modelName, description, callbacks) {
      this.modelName = modelName;

      this._super.call(this, 'model:' + modelName, description, callbacks);

      this.setupSteps.push(this.setupModel);
    },

    setupModel: function() {
      var container = this.container;
      var defaultSubject = this.defaultSubject;
      var callbacks = this.callbacks;
      var modelName = this.modelName;

      var adapterFactory = container.lookupFactory('adapter:application');
      if (!adapterFactory) {
        adapterFactory = DS.JSONAPIAdapter || DS.FixtureAdapter;

        var thingToRegisterWith = this.registry || this.container;
        thingToRegisterWith.register('adapter:application', adapterFactory);
      }

      callbacks.store = function(){
        var container = this.container;
        var store = container.lookup('service:store') || container.lookup('store:main');
        return store;
      };

      if (callbacks.subject === defaultSubject) {
        callbacks.subject = function(options) {
          var container = this.container;

          return Ember['default'].run(function() {
            var store = container.lookup('service:store') || container.lookup('store:main');
            return store.createRecord(modelName, options);
          });
        };
      }
    }
  });

});
define('ember-test-helpers/test-module', ['exports', 'ember', 'ember-test-helpers/test-context', 'klassy', 'ember-test-helpers/test-resolver', 'ember-test-helpers/build-registry'], function (exports, Ember, test_context, klassy, test_resolver, buildRegistry) {

  'use strict';

  exports['default'] = klassy.Klass.extend({
    init: function(subjectName, description, callbacks) {
      // Allow `description` to be omitted, in which case it should
      // default to `subjectName`
      if (!callbacks && typeof description === 'object') {
        callbacks = description;
        description = subjectName;
      }

      this.subjectName = subjectName;
      this.description = description || subjectName;
      this.name = description || subjectName;
      this.callbacks = callbacks || {};

      if (this.callbacks.integration) {
        this.isIntegration = callbacks.integration;
        delete callbacks.integration;
      }

      this.initSubject();
      this.initNeeds();
      this.initSetupSteps();
      this.initTeardownSteps();
    },

    initSubject: function() {
      this.callbacks.subject = this.callbacks.subject || this.defaultSubject;
    },

    initNeeds: function() {
      this.needs = [this.subjectName];
      if (this.callbacks.needs) {
        this.needs = this.needs.concat(this.callbacks.needs);
        delete this.callbacks.needs;
      }
    },

    initSetupSteps: function() {
      this.setupSteps = [];
      this.contextualizedSetupSteps = [];

      if (this.callbacks.beforeSetup) {
        this.setupSteps.push( this.callbacks.beforeSetup );
        delete this.callbacks.beforeSetup;
      }

      this.setupSteps.push(this.setupContainer);
      this.setupSteps.push(this.setupContext);
      this.setupSteps.push(this.setupTestElements);

      if (this.callbacks.setup) {
        this.contextualizedSetupSteps.push( this.callbacks.setup );
        delete this.callbacks.setup;
      }
    },

    initTeardownSteps: function() {
      this.teardownSteps = [];
      this.contextualizedTeardownSteps = [];

      if (this.callbacks.teardown) {
        this.contextualizedTeardownSteps.push( this.callbacks.teardown );
        delete this.callbacks.teardown;
      }

      this.teardownSteps.push(this.teardownSubject);
      this.teardownSteps.push(this.teardownContainer);
      this.teardownSteps.push(this.teardownContext);
      this.teardownSteps.push(this.teardownTestElements);

      if (this.callbacks.afterTeardown) {
        this.teardownSteps.push( this.callbacks.afterTeardown );
        delete this.callbacks.afterTeardown;
      }
    },

    setup: function() {
      var self = this;
      return self.invokeSteps(self.setupSteps).then(function() {
        self.contextualizeCallbacks();
        return self.invokeSteps(self.contextualizedSetupSteps, self.context);
      });
    },

    teardown: function() {
      var self = this;
      return self.invokeSteps(self.contextualizedTeardownSteps, self.context).then(function() {
        return self.invokeSteps(self.teardownSteps);
      }).then(function() {
        self.cache = null;
        self.cachedCalls = null;
      });
    },

    invokeSteps: function(steps, _context) {
      var context = _context;
      if (!context) {
        context = this;
      }
      steps = steps.slice();
      function nextStep() {
        var step = steps.shift();
        if (step) {
          // guard against exceptions, for example missing components referenced from needs.
          return new Ember['default'].RSVP.Promise(function(ok) {
            ok(step.call(context));
          }).then(nextStep);
        } else {
          return Ember['default'].RSVP.resolve();
        }
      }
      return nextStep();
    },

    setupContainer: function() {
      if (this.isIntegration) {
        this._setupIntegratedContainer();
      } else {
        this._setupIsolatedContainer();
      }
    },

    setupContext: function() {
      var subjectName = this.subjectName;
      var container = this.container;

      var factory = function() {
        return container.lookupFactory(subjectName);
      };

      test_context.setContext({
        container:  this.container,
        registry: this.registry,
        factory:    factory,
        dispatcher: null
      });

      this.context = test_context.getContext();
    },

    setupTestElements: function() {
      if (Ember['default'].$('#ember-testing').length === 0) {
        Ember['default'].$('<div id="ember-testing"/>').appendTo(document.body);
      }
    },

    teardownSubject: function() {
      var subject = this.cache.subject;

      if (subject) {
        Ember['default'].run(function() {
          Ember['default'].tryInvoke(subject, 'destroy');
        });
      }
    },

    teardownContainer: function() {
      var container = this.container;
      Ember['default'].run(function() {
        container.destroy();
      });
    },

    teardownContext: function() {
      var context = this.context;
      this.context = undefined;
      test_context.unsetContext();

      if (context.dispatcher && !context.dispatcher.isDestroyed) {
        Ember['default'].run(function() {
          context.dispatcher.destroy();
        });
      }
    },

    teardownTestElements: function() {
      Ember['default'].$('#ember-testing').empty();

      // Ember 2.0.0 removed Ember.View as public API, so only do this when
      // Ember.View is present
      if (Ember['default'].View && Ember['default'].View.views) {
        Ember['default'].View.views = {};
      }
    },

    defaultSubject: function(options, factory) {
      return factory.create(options);
    },

    // allow arbitrary named factories, like rspec let
    contextualizeCallbacks: function() {
      var _this     = this;
      var callbacks = this.callbacks;
      var context   = this.context;
      var factory   = context.factory;

      this.cache = this.cache || {};
      this.cachedCalls = this.cachedCalls || {};

      var keys = (Object.keys || Ember['default'].keys)(callbacks);

      for (var i = 0, l = keys.length; i < l; i++) {
        (function(key) {

          context[key] = function(options) {
            if (_this.cachedCalls[key]) { return _this.cache[key]; }

            var result = callbacks[key].call(_this, options, factory());

            _this.cache[key] = result;
            _this.cachedCalls[key] = true;

            return result;
          };

        })(keys[i]);
      }
    },

    _setupContainer: function() {
      var resolver = test_resolver.getResolver();
      var items = buildRegistry['default'](resolver);

      this.container = items.container;
      this.registry = items.registry;


      var thingToRegisterWith = this.registry || this.container;
      var router = resolver.resolve('router:main');
      router = router || Ember['default'].Router.extend();
      thingToRegisterWith.register('router:main', router);
    },

    _setupIsolatedContainer: function() {
      var resolver = test_resolver.getResolver();
      this._setupContainer();

      var thingToRegisterWith = this.registry || this.container;

      for (var i = this.needs.length; i > 0; i--) {
        var fullName = this.needs[i - 1];
        var normalizedFullName = resolver.normalize(fullName);
        thingToRegisterWith.register(fullName, resolver.resolve(normalizedFullName));
      }

      thingToRegisterWith.resolver = function() { };
    },

    _setupIntegratedContainer: function() {
      this._setupContainer();
    }

  });

});
define('ember-test-helpers/test-resolver', ['exports'], function (exports) {

  'use strict';

  exports.setResolver = setResolver;
  exports.getResolver = getResolver;

  var __resolver__;

  function setResolver(resolver) {
    __resolver__ = resolver;
  }

  function getResolver() {
    if (__resolver__ == null) throw new Error('you must set a resolver with `testResolver.set(resolver)`');
    return __resolver__;
  }

});
define('klassy', ['exports'], function (exports) {

  'use strict';

  /**
   Extend a class with the properties and methods of one or more other classes.

   When a method is replaced with another method, it will be wrapped in a
   function that makes the replaced method accessible via `this._super`.

   @method extendClass
   @param {Object} destination The class to merge into
   @param {Object} source One or more source classes
   */
  var extendClass = function(destination) {
    var sources = Array.prototype.slice.call(arguments, 1);
    var source;

    for (var i = 0, l = sources.length; i < l; i++) {
      source = sources[i];

      for (var p in source) {
        if (source.hasOwnProperty(p) &&
          destination[p] &&
          typeof destination[p] === 'function' &&
          typeof source[p] === 'function') {

          /* jshint loopfunc:true */
          destination[p] =
            (function(destinationFn, sourceFn) {
              var wrapper = function() {
                var prevSuper = this._super;
                this._super = destinationFn;

                var ret = sourceFn.apply(this, arguments);

                this._super = prevSuper;

                return ret;
              };
              wrapper.wrappedFunction = sourceFn;
              return wrapper;
            })(destination[p], source[p]);

        } else {
          destination[p] = source[p];
        }
      }
    }
  };

  // `subclassing` is a state flag used by `defineClass` to track when a class is
  // being subclassed. It allows constructors to avoid calling `init`, which can
  // be expensive and cause undesirable side effects.
  var subclassing = false;

  /**
   Define a new class with the properties and methods of one or more other classes.

   The new class can be based on a `SuperClass`, which will be inserted into its
   prototype chain.

   Furthermore, one or more mixins (object that contain properties and/or methods)
   may be specified, which will be applied in order. When a method is replaced
   with another method, it will be wrapped in a function that makes the previous
   method accessible via `this._super`.

   @method defineClass
   @param {Object} SuperClass A base class to extend. If `mixins` are to be included
   without a `SuperClass`, pass `null` for SuperClass.
   @param {Object} mixins One or more objects that contain properties and methods
   to apply to the new class.
   */
  var defineClass = function(SuperClass) {
    var Klass = function() {
      if (!subclassing && this.init) {
        this.init.apply(this, arguments);
      }
    };

    if (SuperClass) {
      subclassing = true;
      Klass.prototype = new SuperClass();
      subclassing = false;
    }

    if (arguments.length > 1) {
      var extendArgs = Array.prototype.slice.call(arguments, 1);
      extendArgs.unshift(Klass.prototype);
      extendClass.apply(Klass.prototype, extendArgs);
    }

    Klass.constructor = Klass;

    Klass.extend = function() {
      var args = Array.prototype.slice.call(arguments, 0);
      args.unshift(Klass);
      return defineClass.apply(Klass, args);
    };

    return Klass;
  };

  /**
   A base class that can be extended.

   @example

   ```javascript
   var CelestialObject = Klass.extend({
     init: function(name) {
       this._super();
       this.name = name;
       this.isCelestialObject = true;
     },
     greeting: function() {
       return 'Hello from ' + this.name;
     }
   });

   var Planet = CelestialObject.extend({
     init: function(name) {
       this._super.apply(this, arguments);
       this.isPlanet = true;
     },
     greeting: function() {
       return this._super() + '!';
     },
   });

   var earth = new Planet('Earth');

   console.log(earth instanceof Klass);           // true
   console.log(earth instanceof CelestialObject); // true
   console.log(earth instanceof Planet);          // true

   console.log(earth.isCelestialObject);          // true
   console.log(earth.isPlanet);                   // true

   console.log(earth.greeting());                 // 'Hello from Earth!'
   ```

   @class Klass
   */
  var Klass = defineClass(null, {
    init: function() {}
  });

  exports.Klass = Klass;
  exports.defineClass = defineClass;
  exports.extendClass = extendClass;

});
define('qunit', ['exports'], function (exports) {

	'use strict';

	/* globals test:true */

	var module = QUnit.module;
	var test = QUnit.test;
	var skip = QUnit.skip;

	exports['default'] = QUnit;

	exports.module = module;
	exports.test = test;
	exports.skip = skip;

});
/*!
 * QUnit 1.18.0
 * http://qunitjs.com/
 *
 * Copyright jQuery Foundation and other contributors
 * Released under the MIT license
 * http://jquery.org/license
 *
 * Date: 2015-04-03T10:23Z
 */

(function( window ) {

var QUnit,
	config,
	onErrorFnPrev,
	loggingCallbacks = {},
	fileName = ( sourceFromStacktrace( 0 ) || "" ).replace( /(:\d+)+\)?/, "" ).replace( /.+\//, "" ),
	toString = Object.prototype.toString,
	hasOwn = Object.prototype.hasOwnProperty,
	// Keep a local reference to Date (GH-283)
	Date = window.Date,
	now = Date.now || function() {
		return new Date().getTime();
	},
	globalStartCalled = false,
	runStarted = false,
	setTimeout = window.setTimeout,
	clearTimeout = window.clearTimeout,
	defined = {
		document: window.document !== undefined,
		setTimeout: window.setTimeout !== undefined,
		sessionStorage: (function() {
			var x = "qunit-test-string";
			try {
				sessionStorage.setItem( x, x );
				sessionStorage.removeItem( x );
				return true;
			} catch ( e ) {
				return false;
			}
		}())
	},
	/**
	 * Provides a normalized error string, correcting an issue
	 * with IE 7 (and prior) where Error.prototype.toString is
	 * not properly implemented
	 *
	 * Based on http://es5.github.com/#x15.11.4.4
	 *
	 * @param {String|Error} error
	 * @return {String} error message
	 */
	errorString = function( error ) {
		var name, message,
			errorString = error.toString();
		if ( errorString.substring( 0, 7 ) === "[object" ) {
			name = error.name ? error.name.toString() : "Error";
			message = error.message ? error.message.toString() : "";
			if ( name && message ) {
				return name + ": " + message;
			} else if ( name ) {
				return name;
			} else if ( message ) {
				return message;
			} else {
				return "Error";
			}
		} else {
			return errorString;
		}
	},
	/**
	 * Makes a clone of an object using only Array or Object as base,
	 * and copies over the own enumerable properties.
	 *
	 * @param {Object} obj
	 * @return {Object} New object with only the own properties (recursively).
	 */
	objectValues = function( obj ) {
		var key, val,
			vals = QUnit.is( "array", obj ) ? [] : {};
		for ( key in obj ) {
			if ( hasOwn.call( obj, key ) ) {
				val = obj[ key ];
				vals[ key ] = val === Object( val ) ? objectValues( val ) : val;
			}
		}
		return vals;
	};

QUnit = {};

/**
 * Config object: Maintain internal state
 * Later exposed as QUnit.config
 * `config` initialized at top of scope
 */
config = {
	// The queue of tests to run
	queue: [],

	// block until document ready
	blocking: true,

	// by default, run previously failed tests first
	// very useful in combination with "Hide passed tests" checked
	reorder: true,

	// by default, modify document.title when suite is done
	altertitle: true,

	// by default, scroll to top of the page when suite is done
	scrolltop: true,

	// when enabled, all tests must call expect()
	requireExpects: false,

	// depth up-to which object will be dumped
	maxDepth: 5,

	// add checkboxes that are persisted in the query-string
	// when enabled, the id is set to `true` as a `QUnit.config` property
	urlConfig: [
		{
			id: "hidepassed",
			label: "Hide passed tests",
			tooltip: "Only show tests and assertions that fail. Stored as query-strings."
		},
		{
			id: "noglobals",
			label: "Check for Globals",
			tooltip: "Enabling this will test if any test introduces new properties on the " +
				"`window` object. Stored as query-strings."
		},
		{
			id: "notrycatch",
			label: "No try-catch",
			tooltip: "Enabling this will run tests outside of a try-catch block. Makes debugging " +
				"exceptions in IE reasonable. Stored as query-strings."
		}
	],

	// Set of all modules.
	modules: [],

	// The first unnamed module
	currentModule: {
		name: "",
		tests: []
	},

	callbacks: {}
};

// Push a loose unnamed module to the modules collection
config.modules.push( config.currentModule );

// Initialize more QUnit.config and QUnit.urlParams
(function() {
	var i, current,
		location = window.location || { search: "", protocol: "file:" },
		params = location.search.slice( 1 ).split( "&" ),
		length = params.length,
		urlParams = {};

	if ( params[ 0 ] ) {
		for ( i = 0; i < length; i++ ) {
			current = params[ i ].split( "=" );
			current[ 0 ] = decodeURIComponent( current[ 0 ] );

			// allow just a key to turn on a flag, e.g., test.html?noglobals
			current[ 1 ] = current[ 1 ] ? decodeURIComponent( current[ 1 ] ) : true;
			if ( urlParams[ current[ 0 ] ] ) {
				urlParams[ current[ 0 ] ] = [].concat( urlParams[ current[ 0 ] ], current[ 1 ] );
			} else {
				urlParams[ current[ 0 ] ] = current[ 1 ];
			}
		}
	}

	if ( urlParams.filter === true ) {
		delete urlParams.filter;
	}

	QUnit.urlParams = urlParams;

	// String search anywhere in moduleName+testName
	config.filter = urlParams.filter;

	if ( urlParams.maxDepth ) {
		config.maxDepth = parseInt( urlParams.maxDepth, 10 ) === -1 ?
			Number.POSITIVE_INFINITY :
			urlParams.maxDepth;
	}

	config.testId = [];
	if ( urlParams.testId ) {

		// Ensure that urlParams.testId is an array
		urlParams.testId = decodeURIComponent( urlParams.testId ).split( "," );
		for ( i = 0; i < urlParams.testId.length; i++ ) {
			config.testId.push( urlParams.testId[ i ] );
		}
	}

	// Figure out if we're running the tests from a server or not
	QUnit.isLocal = location.protocol === "file:";

	// Expose the current QUnit version
	QUnit.version = "1.18.0";
}());

// Root QUnit object.
// `QUnit` initialized at top of scope
extend( QUnit, {

	// call on start of module test to prepend name to all tests
	module: function( name, testEnvironment ) {
		var currentModule = {
			name: name,
			testEnvironment: testEnvironment,
			tests: []
		};

		// DEPRECATED: handles setup/teardown functions,
		// beforeEach and afterEach should be used instead
		if ( testEnvironment && testEnvironment.setup ) {
			testEnvironment.beforeEach = testEnvironment.setup;
			delete testEnvironment.setup;
		}
		if ( testEnvironment && testEnvironment.teardown ) {
			testEnvironment.afterEach = testEnvironment.teardown;
			delete testEnvironment.teardown;
		}

		config.modules.push( currentModule );
		config.currentModule = currentModule;
	},

	// DEPRECATED: QUnit.asyncTest() will be removed in QUnit 2.0.
	asyncTest: function( testName, expected, callback ) {
		if ( arguments.length === 2 ) {
			callback = expected;
			expected = null;
		}

		QUnit.test( testName, expected, callback, true );
	},

	test: function( testName, expected, callback, async ) {
		var test;

		if ( arguments.length === 2 ) {
			callback = expected;
			expected = null;
		}

		test = new Test({
			testName: testName,
			expected: expected,
			async: async,
			callback: callback
		});

		test.queue();
	},

	skip: function( testName ) {
		var test = new Test({
			testName: testName,
			skip: true
		});

		test.queue();
	},

	// DEPRECATED: The functionality of QUnit.start() will be altered in QUnit 2.0.
	// In QUnit 2.0, invoking it will ONLY affect the `QUnit.config.autostart` blocking behavior.
	start: function( count ) {
		var globalStartAlreadyCalled = globalStartCalled;

		if ( !config.current ) {
			globalStartCalled = true;

			if ( runStarted ) {
				throw new Error( "Called start() outside of a test context while already started" );
			} else if ( globalStartAlreadyCalled || count > 1 ) {
				throw new Error( "Called start() outside of a test context too many times" );
			} else if ( config.autostart ) {
				throw new Error( "Called start() outside of a test context when " +
					"QUnit.config.autostart was true" );
			} else if ( !config.pageLoaded ) {

				// The page isn't completely loaded yet, so bail out and let `QUnit.load` handle it
				config.autostart = true;
				return;
			}
		} else {

			// If a test is running, adjust its semaphore
			config.current.semaphore -= count || 1;

			// Don't start until equal number of stop-calls
			if ( config.current.semaphore > 0 ) {
				return;
			}

			// throw an Error if start is called more often than stop
			if ( config.current.semaphore < 0 ) {
				config.current.semaphore = 0;

				QUnit.pushFailure(
					"Called start() while already started (test's semaphore was 0 already)",
					sourceFromStacktrace( 2 )
				);
				return;
			}
		}

		resumeProcessing();
	},

	// DEPRECATED: QUnit.stop() will be removed in QUnit 2.0.
	stop: function( count ) {

		// If there isn't a test running, don't allow QUnit.stop() to be called
		if ( !config.current ) {
			throw new Error( "Called stop() outside of a test context" );
		}

		// If a test is running, adjust its semaphore
		config.current.semaphore += count || 1;

		pauseProcessing();
	},

	config: config,

	// Safe object type checking
	is: function( type, obj ) {
		return QUnit.objectType( obj ) === type;
	},

	objectType: function( obj ) {
		if ( typeof obj === "undefined" ) {
			return "undefined";
		}

		// Consider: typeof null === object
		if ( obj === null ) {
			return "null";
		}

		var match = toString.call( obj ).match( /^\[object\s(.*)\]$/ ),
			type = match && match[ 1 ] || "";

		switch ( type ) {
			case "Number":
				if ( isNaN( obj ) ) {
					return "nan";
				}
				return "number";
			case "String":
			case "Boolean":
			case "Array":
			case "Date":
			case "RegExp":
			case "Function":
				return type.toLowerCase();
		}
		if ( typeof obj === "object" ) {
			return "object";
		}
		return undefined;
	},

	extend: extend,

	load: function() {
		config.pageLoaded = true;

		// Initialize the configuration options
		extend( config, {
			stats: { all: 0, bad: 0 },
			moduleStats: { all: 0, bad: 0 },
			started: 0,
			updateRate: 1000,
			autostart: true,
			filter: ""
		}, true );

		config.blocking = false;

		if ( config.autostart ) {
			resumeProcessing();
		}
	}
});

// Register logging callbacks
(function() {
	var i, l, key,
		callbacks = [ "begin", "done", "log", "testStart", "testDone",
			"moduleStart", "moduleDone" ];

	function registerLoggingCallback( key ) {
		var loggingCallback = function( callback ) {
			if ( QUnit.objectType( callback ) !== "function" ) {
				throw new Error(
					"QUnit logging methods require a callback function as their first parameters."
				);
			}

			config.callbacks[ key ].push( callback );
		};

		// DEPRECATED: This will be removed on QUnit 2.0.0+
		// Stores the registered functions allowing restoring
		// at verifyLoggingCallbacks() if modified
		loggingCallbacks[ key ] = loggingCallback;

		return loggingCallback;
	}

	for ( i = 0, l = callbacks.length; i < l; i++ ) {
		key = callbacks[ i ];

		// Initialize key collection of logging callback
		if ( QUnit.objectType( config.callbacks[ key ] ) === "undefined" ) {
			config.callbacks[ key ] = [];
		}

		QUnit[ key ] = registerLoggingCallback( key );
	}
})();

// `onErrorFnPrev` initialized at top of scope
// Preserve other handlers
onErrorFnPrev = window.onerror;

// Cover uncaught exceptions
// Returning true will suppress the default browser handler,
// returning false will let it run.
window.onerror = function( error, filePath, linerNr ) {
	var ret = false;
	if ( onErrorFnPrev ) {
		ret = onErrorFnPrev( error, filePath, linerNr );
	}

	// Treat return value as window.onerror itself does,
	// Only do our handling if not suppressed.
	if ( ret !== true ) {
		if ( QUnit.config.current ) {
			if ( QUnit.config.current.ignoreGlobalErrors ) {
				return true;
			}
			QUnit.pushFailure( error, filePath + ":" + linerNr );
		} else {
			QUnit.test( "global failure", extend(function() {
				QUnit.pushFailure( error, filePath + ":" + linerNr );
			}, { validTest: true } ) );
		}
		return false;
	}

	return ret;
};

function done() {
	var runtime, passed;

	config.autorun = true;

	// Log the last module results
	if ( config.previousModule ) {
		runLoggingCallbacks( "moduleDone", {
			name: config.previousModule.name,
			tests: config.previousModule.tests,
			failed: config.moduleStats.bad,
			passed: config.moduleStats.all - config.moduleStats.bad,
			total: config.moduleStats.all,
			runtime: now() - config.moduleStats.started
		});
	}
	delete config.previousModule;

	runtime = now() - config.started;
	passed = config.stats.all - config.stats.bad;

	runLoggingCallbacks( "done", {
		failed: config.stats.bad,
		passed: passed,
		total: config.stats.all,
		runtime: runtime
	});
}

// Doesn't support IE6 to IE9, it will return undefined on these browsers
// See also https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Error/Stack
function extractStacktrace( e, offset ) {
	offset = offset === undefined ? 4 : offset;

	var stack, include, i;

	if ( e.stack ) {
		stack = e.stack.split( "\n" );
		if ( /^error$/i.test( stack[ 0 ] ) ) {
			stack.shift();
		}
		if ( fileName ) {
			include = [];
			for ( i = offset; i < stack.length; i++ ) {
				if ( stack[ i ].indexOf( fileName ) !== -1 ) {
					break;
				}
				include.push( stack[ i ] );
			}
			if ( include.length ) {
				return include.join( "\n" );
			}
		}
		return stack[ offset ];

	// Support: Safari <=6 only
	} else if ( e.sourceURL ) {

		// exclude useless self-reference for generated Error objects
		if ( /qunit.js$/.test( e.sourceURL ) ) {
			return;
		}

		// for actual exceptions, this is useful
		return e.sourceURL + ":" + e.line;
	}
}

function sourceFromStacktrace( offset ) {
	var error = new Error();

	// Support: Safari <=7 only, IE <=10 - 11 only
	// Not all browsers generate the `stack` property for `new Error()`, see also #636
	if ( !error.stack ) {
		try {
			throw error;
		} catch ( err ) {
			error = err;
		}
	}

	return extractStacktrace( error, offset );
}

function synchronize( callback, last ) {
	if ( QUnit.objectType( callback ) === "array" ) {
		while ( callback.length ) {
			synchronize( callback.shift() );
		}
		return;
	}
	config.queue.push( callback );

	if ( config.autorun && !config.blocking ) {
		process( last );
	}
}

function process( last ) {
	function next() {
		process( last );
	}
	var start = now();
	config.depth = ( config.depth || 0 ) + 1;

	while ( config.queue.length && !config.blocking ) {
		if ( !defined.setTimeout || config.updateRate <= 0 ||
				( ( now() - start ) < config.updateRate ) ) {
			if ( config.current ) {

				// Reset async tracking for each phase of the Test lifecycle
				config.current.usedAsync = false;
			}
			config.queue.shift()();
		} else {
			setTimeout( next, 13 );
			break;
		}
	}
	config.depth--;
	if ( last && !config.blocking && !config.queue.length && config.depth === 0 ) {
		done();
	}
}

function begin() {
	var i, l,
		modulesLog = [];

	// If the test run hasn't officially begun yet
	if ( !config.started ) {

		// Record the time of the test run's beginning
		config.started = now();

		verifyLoggingCallbacks();

		// Delete the loose unnamed module if unused.
		if ( config.modules[ 0 ].name === "" && config.modules[ 0 ].tests.length === 0 ) {
			config.modules.shift();
		}

		// Avoid unnecessary information by not logging modules' test environments
		for ( i = 0, l = config.modules.length; i < l; i++ ) {
			modulesLog.push({
				name: config.modules[ i ].name,
				tests: config.modules[ i ].tests
			});
		}

		// The test run is officially beginning now
		runLoggingCallbacks( "begin", {
			totalTests: Test.count,
			modules: modulesLog
		});
	}

	config.blocking = false;
	process( true );
}

function resumeProcessing() {
	runStarted = true;

	// A slight delay to allow this iteration of the event loop to finish (more assertions, etc.)
	if ( defined.setTimeout ) {
		setTimeout(function() {
			if ( config.current && config.current.semaphore > 0 ) {
				return;
			}
			if ( config.timeout ) {
				clearTimeout( config.timeout );
			}

			begin();
		}, 13 );
	} else {
		begin();
	}
}

function pauseProcessing() {
	config.blocking = true;

	if ( config.testTimeout && defined.setTimeout ) {
		clearTimeout( config.timeout );
		config.timeout = setTimeout(function() {
			if ( config.current ) {
				config.current.semaphore = 0;
				QUnit.pushFailure( "Test timed out", sourceFromStacktrace( 2 ) );
			} else {
				throw new Error( "Test timed out" );
			}
			resumeProcessing();
		}, config.testTimeout );
	}
}

function saveGlobal() {
	config.pollution = [];

	if ( config.noglobals ) {
		for ( var key in window ) {
			if ( hasOwn.call( window, key ) ) {
				// in Opera sometimes DOM element ids show up here, ignore them
				if ( /^qunit-test-output/.test( key ) ) {
					continue;
				}
				config.pollution.push( key );
			}
		}
	}
}

function checkPollution() {
	var newGlobals,
		deletedGlobals,
		old = config.pollution;

	saveGlobal();

	newGlobals = diff( config.pollution, old );
	if ( newGlobals.length > 0 ) {
		QUnit.pushFailure( "Introduced global variable(s): " + newGlobals.join( ", " ) );
	}

	deletedGlobals = diff( old, config.pollution );
	if ( deletedGlobals.length > 0 ) {
		QUnit.pushFailure( "Deleted global variable(s): " + deletedGlobals.join( ", " ) );
	}
}

// returns a new Array with the elements that are in a but not in b
function diff( a, b ) {
	var i, j,
		result = a.slice();

	for ( i = 0; i < result.length; i++ ) {
		for ( j = 0; j < b.length; j++ ) {
			if ( result[ i ] === b[ j ] ) {
				result.splice( i, 1 );
				i--;
				break;
			}
		}
	}
	return result;
}

function extend( a, b, undefOnly ) {
	for ( var prop in b ) {
		if ( hasOwn.call( b, prop ) ) {

			// Avoid "Member not found" error in IE8 caused by messing with window.constructor
			if ( !( prop === "constructor" && a === window ) ) {
				if ( b[ prop ] === undefined ) {
					delete a[ prop ];
				} else if ( !( undefOnly && typeof a[ prop ] !== "undefined" ) ) {
					a[ prop ] = b[ prop ];
				}
			}
		}
	}

	return a;
}

function runLoggingCallbacks( key, args ) {
	var i, l, callbacks;

	callbacks = config.callbacks[ key ];
	for ( i = 0, l = callbacks.length; i < l; i++ ) {
		callbacks[ i ]( args );
	}
}

// DEPRECATED: This will be removed on 2.0.0+
// This function verifies if the loggingCallbacks were modified by the user
// If so, it will restore it, assign the given callback and print a console warning
function verifyLoggingCallbacks() {
	var loggingCallback, userCallback;

	for ( loggingCallback in loggingCallbacks ) {
		if ( QUnit[ loggingCallback ] !== loggingCallbacks[ loggingCallback ] ) {

			userCallback = QUnit[ loggingCallback ];

			// Restore the callback function
			QUnit[ loggingCallback ] = loggingCallbacks[ loggingCallback ];

			// Assign the deprecated given callback
			QUnit[ loggingCallback ]( userCallback );

			if ( window.console && window.console.warn ) {
				window.console.warn(
					"QUnit." + loggingCallback + " was replaced with a new value.\n" +
					"Please, check out the documentation on how to apply logging callbacks.\n" +
					"Reference: http://api.qunitjs.com/category/callbacks/"
				);
			}
		}
	}
}

// from jquery.js
function inArray( elem, array ) {
	if ( array.indexOf ) {
		return array.indexOf( elem );
	}

	for ( var i = 0, length = array.length; i < length; i++ ) {
		if ( array[ i ] === elem ) {
			return i;
		}
	}

	return -1;
}

function Test( settings ) {
	var i, l;

	++Test.count;

	extend( this, settings );
	this.assertions = [];
	this.semaphore = 0;
	this.usedAsync = false;
	this.module = config.currentModule;
	this.stack = sourceFromStacktrace( 3 );

	// Register unique strings
	for ( i = 0, l = this.module.tests; i < l.length; i++ ) {
		if ( this.module.tests[ i ].name === this.testName ) {
			this.testName += " ";
		}
	}

	this.testId = generateHash( this.module.name, this.testName );

	this.module.tests.push({
		name: this.testName,
		testId: this.testId
	});

	if ( settings.skip ) {

		// Skipped tests will fully ignore any sent callback
		this.callback = function() {};
		this.async = false;
		this.expected = 0;
	} else {
		this.assert = new Assert( this );
	}
}

Test.count = 0;

Test.prototype = {
	before: function() {
		if (

			// Emit moduleStart when we're switching from one module to another
			this.module !== config.previousModule ||

				// They could be equal (both undefined) but if the previousModule property doesn't
				// yet exist it means this is the first test in a suite that isn't wrapped in a
				// module, in which case we'll just emit a moduleStart event for 'undefined'.
				// Without this, reporters can get testStart before moduleStart  which is a problem.
				!hasOwn.call( config, "previousModule" )
		) {
			if ( hasOwn.call( config, "previousModule" ) ) {
				runLoggingCallbacks( "moduleDone", {
					name: config.previousModule.name,
					tests: config.previousModule.tests,
					failed: config.moduleStats.bad,
					passed: config.moduleStats.all - config.moduleStats.bad,
					total: config.moduleStats.all,
					runtime: now() - config.moduleStats.started
				});
			}
			config.previousModule = this.module;
			config.moduleStats = { all: 0, bad: 0, started: now() };
			runLoggingCallbacks( "moduleStart", {
				name: this.module.name,
				tests: this.module.tests
			});
		}

		config.current = this;

		this.testEnvironment = extend( {}, this.module.testEnvironment );
		delete this.testEnvironment.beforeEach;
		delete this.testEnvironment.afterEach;

		this.started = now();
		runLoggingCallbacks( "testStart", {
			name: this.testName,
			module: this.module.name,
			testId: this.testId
		});

		if ( !config.pollution ) {
			saveGlobal();
		}
	},

	run: function() {
		var promise;

		config.current = this;

		if ( this.async ) {
			QUnit.stop();
		}

		this.callbackStarted = now();

		if ( config.notrycatch ) {
			promise = this.callback.call( this.testEnvironment, this.assert );
			this.resolvePromise( promise );
			return;
		}

		try {
			promise = this.callback.call( this.testEnvironment, this.assert );
			this.resolvePromise( promise );
		} catch ( e ) {
			this.pushFailure( "Died on test #" + ( this.assertions.length + 1 ) + " " +
				this.stack + ": " + ( e.message || e ), extractStacktrace( e, 0 ) );

			// else next test will carry the responsibility
			saveGlobal();

			// Restart the tests if they're blocking
			if ( config.blocking ) {
				QUnit.start();
			}
		}
	},

	after: function() {
		checkPollution();
	},

	queueHook: function( hook, hookName ) {
		var promise,
			test = this;
		return function runHook() {
			config.current = test;
			if ( config.notrycatch ) {
				promise = hook.call( test.testEnvironment, test.assert );
				test.resolvePromise( promise, hookName );
				return;
			}
			try {
				promise = hook.call( test.testEnvironment, test.assert );
				test.resolvePromise( promise, hookName );
			} catch ( error ) {
				test.pushFailure( hookName + " failed on " + test.testName + ": " +
					( error.message || error ), extractStacktrace( error, 0 ) );
			}
		};
	},

	// Currently only used for module level hooks, can be used to add global level ones
	hooks: function( handler ) {
		var hooks = [];

		// Hooks are ignored on skipped tests
		if ( this.skip ) {
			return hooks;
		}

		if ( this.module.testEnvironment &&
				QUnit.objectType( this.module.testEnvironment[ handler ] ) === "function" ) {
			hooks.push( this.queueHook( this.module.testEnvironment[ handler ], handler ) );
		}

		return hooks;
	},

	finish: function() {
		config.current = this;
		if ( config.requireExpects && this.expected === null ) {
			this.pushFailure( "Expected number of assertions to be defined, but expect() was " +
				"not called.", this.stack );
		} else if ( this.expected !== null && this.expected !== this.assertions.length ) {
			this.pushFailure( "Expected " + this.expected + " assertions, but " +
				this.assertions.length + " were run", this.stack );
		} else if ( this.expected === null && !this.assertions.length ) {
			this.pushFailure( "Expected at least one assertion, but none were run - call " +
				"expect(0) to accept zero assertions.", this.stack );
		}

		var i,
			bad = 0;

		this.runtime = now() - this.started;
		config.stats.all += this.assertions.length;
		config.moduleStats.all += this.assertions.length;

		for ( i = 0; i < this.assertions.length; i++ ) {
			if ( !this.assertions[ i ].result ) {
				bad++;
				config.stats.bad++;
				config.moduleStats.bad++;
			}
		}

		runLoggingCallbacks( "testDone", {
			name: this.testName,
			module: this.module.name,
			skipped: !!this.skip,
			failed: bad,
			passed: this.assertions.length - bad,
			total: this.assertions.length,
			runtime: this.runtime,

			// HTML Reporter use
			assertions: this.assertions,
			testId: this.testId,

			// DEPRECATED: this property will be removed in 2.0.0, use runtime instead
			duration: this.runtime
		});

		// QUnit.reset() is deprecated and will be replaced for a new
		// fixture reset function on QUnit 2.0/2.1.
		// It's still called here for backwards compatibility handling
		QUnit.reset();

		config.current = undefined;
	},

	queue: function() {
		var bad,
			test = this;

		if ( !this.valid() ) {
			return;
		}

		function run() {

			// each of these can by async
			synchronize([
				function() {
					test.before();
				},

				test.hooks( "beforeEach" ),

				function() {
					test.run();
				},

				test.hooks( "afterEach" ).reverse(),

				function() {
					test.after();
				},
				function() {
					test.finish();
				}
			]);
		}

		// `bad` initialized at top of scope
		// defer when previous test run passed, if storage is available
		bad = QUnit.config.reorder && defined.sessionStorage &&
				+sessionStorage.getItem( "qunit-test-" + this.module.name + "-" + this.testName );

		if ( bad ) {
			run();
		} else {
			synchronize( run, true );
		}
	},

	push: function( result, actual, expected, message ) {
		var source,
			details = {
				module: this.module.name,
				name: this.testName,
				result: result,
				message: message,
				actual: actual,
				expected: expected,
				testId: this.testId,
				runtime: now() - this.started
			};

		if ( !result ) {
			source = sourceFromStacktrace();

			if ( source ) {
				details.source = source;
			}
		}

		runLoggingCallbacks( "log", details );

		this.assertions.push({
			result: !!result,
			message: message
		});
	},

	pushFailure: function( message, source, actual ) {
		if ( !this instanceof Test ) {
			throw new Error( "pushFailure() assertion outside test context, was " +
				sourceFromStacktrace( 2 ) );
		}

		var details = {
				module: this.module.name,
				name: this.testName,
				result: false,
				message: message || "error",
				actual: actual || null,
				testId: this.testId,
				runtime: now() - this.started
			};

		if ( source ) {
			details.source = source;
		}

		runLoggingCallbacks( "log", details );

		this.assertions.push({
			result: false,
			message: message
		});
	},

	resolvePromise: function( promise, phase ) {
		var then, message,
			test = this;
		if ( promise != null ) {
			then = promise.then;
			if ( QUnit.objectType( then ) === "function" ) {
				QUnit.stop();
				then.call(
					promise,
					QUnit.start,
					function( error ) {
						message = "Promise rejected " +
							( !phase ? "during" : phase.replace( /Each$/, "" ) ) +
							" " + test.testName + ": " + ( error.message || error );
						test.pushFailure( message, extractStacktrace( error, 0 ) );

						// else next test will carry the responsibility
						saveGlobal();

						// Unblock
						QUnit.start();
					}
				);
			}
		}
	},

	valid: function() {
		var include,
			filter = config.filter && config.filter.toLowerCase(),
			module = QUnit.urlParams.module && QUnit.urlParams.module.toLowerCase(),
			fullName = ( this.module.name + ": " + this.testName ).toLowerCase();

		// Internally-generated tests are always valid
		if ( this.callback && this.callback.validTest ) {
			return true;
		}

		if ( config.testId.length > 0 && inArray( this.testId, config.testId ) < 0 ) {
			return false;
		}

		if ( module && ( !this.module.name || this.module.name.toLowerCase() !== module ) ) {
			return false;
		}

		if ( !filter ) {
			return true;
		}

		include = filter.charAt( 0 ) !== "!";
		if ( !include ) {
			filter = filter.slice( 1 );
		}

		// If the filter matches, we need to honour include
		if ( fullName.indexOf( filter ) !== -1 ) {
			return include;
		}

		// Otherwise, do the opposite
		return !include;
	}

};

// Resets the test setup. Useful for tests that modify the DOM.
/*
DEPRECATED: Use multiple tests instead of resetting inside a test.
Use testStart or testDone for custom cleanup.
This method will throw an error in 2.0, and will be removed in 2.1
*/
QUnit.reset = function() {

	// Return on non-browser environments
	// This is necessary to not break on node tests
	if ( typeof window === "undefined" ) {
		return;
	}

	var fixture = defined.document && document.getElementById &&
			document.getElementById( "qunit-fixture" );

	if ( fixture ) {
		fixture.innerHTML = config.fixture;
	}
};

QUnit.pushFailure = function() {
	if ( !QUnit.config.current ) {
		throw new Error( "pushFailure() assertion outside test context, in " +
			sourceFromStacktrace( 2 ) );
	}

	// Gets current test obj
	var currentTest = QUnit.config.current;

	return currentTest.pushFailure.apply( currentTest, arguments );
};

// Based on Java's String.hashCode, a simple but not
// rigorously collision resistant hashing function
function generateHash( module, testName ) {
	var hex,
		i = 0,
		hash = 0,
		str = module + "\x1C" + testName,
		len = str.length;

	for ( ; i < len; i++ ) {
		hash  = ( ( hash << 5 ) - hash ) + str.charCodeAt( i );
		hash |= 0;
	}

	// Convert the possibly negative integer hash code into an 8 character hex string, which isn't
	// strictly necessary but increases user understanding that the id is a SHA-like hash
	hex = ( 0x100000000 + hash ).toString( 16 );
	if ( hex.length < 8 ) {
		hex = "0000000" + hex;
	}

	return hex.slice( -8 );
}

function Assert( testContext ) {
	this.test = testContext;
}

// Assert helpers
QUnit.assert = Assert.prototype = {

	// Specify the number of expected assertions to guarantee that failed test
	// (no assertions are run at all) don't slip through.
	expect: function( asserts ) {
		if ( arguments.length === 1 ) {
			this.test.expected = asserts;
		} else {
			return this.test.expected;
		}
	},

	// Increment this Test's semaphore counter, then return a single-use function that
	// decrements that counter a maximum of once.
	async: function() {
		var test = this.test,
			popped = false;

		test.semaphore += 1;
		test.usedAsync = true;
		pauseProcessing();

		return function done() {
			if ( !popped ) {
				test.semaphore -= 1;
				popped = true;
				resumeProcessing();
			} else {
				test.pushFailure( "Called the callback returned from `assert.async` more than once",
					sourceFromStacktrace( 2 ) );
			}
		};
	},

	// Exports test.push() to the user API
	push: function( /* result, actual, expected, message */ ) {
		var assert = this,
			currentTest = ( assert instanceof Assert && assert.test ) || QUnit.config.current;

		// Backwards compatibility fix.
		// Allows the direct use of global exported assertions and QUnit.assert.*
		// Although, it's use is not recommended as it can leak assertions
		// to other tests from async tests, because we only get a reference to the current test,
		// not exactly the test where assertion were intended to be called.
		if ( !currentTest ) {
			throw new Error( "assertion outside test context, in " + sourceFromStacktrace( 2 ) );
		}

		if ( currentTest.usedAsync === true && currentTest.semaphore === 0 ) {
			currentTest.pushFailure( "Assertion after the final `assert.async` was resolved",
				sourceFromStacktrace( 2 ) );

			// Allow this assertion to continue running anyway...
		}

		if ( !( assert instanceof Assert ) ) {
			assert = currentTest.assert;
		}
		return assert.test.push.apply( assert.test, arguments );
	},

	ok: function( result, message ) {
		message = message || ( result ? "okay" : "failed, expected argument to be truthy, was: " +
			QUnit.dump.parse( result ) );
		this.push( !!result, result, true, message );
	},

	notOk: function( result, message ) {
		message = message || ( !result ? "okay" : "failed, expected argument to be falsy, was: " +
			QUnit.dump.parse( result ) );
		this.push( !result, result, false, message );
	},

	equal: function( actual, expected, message ) {
		/*jshint eqeqeq:false */
		this.push( expected == actual, actual, expected, message );
	},

	notEqual: function( actual, expected, message ) {
		/*jshint eqeqeq:false */
		this.push( expected != actual, actual, expected, message );
	},

	propEqual: function( actual, expected, message ) {
		actual = objectValues( actual );
		expected = objectValues( expected );
		this.push( QUnit.equiv( actual, expected ), actual, expected, message );
	},

	notPropEqual: function( actual, expected, message ) {
		actual = objectValues( actual );
		expected = objectValues( expected );
		this.push( !QUnit.equiv( actual, expected ), actual, expected, message );
	},

	deepEqual: function( actual, expected, message ) {
		this.push( QUnit.equiv( actual, expected ), actual, expected, message );
	},

	notDeepEqual: function( actual, expected, message ) {
		this.push( !QUnit.equiv( actual, expected ), actual, expected, message );
	},

	strictEqual: function( actual, expected, message ) {
		this.push( expected === actual, actual, expected, message );
	},

	notStrictEqual: function( actual, expected, message ) {
		this.push( expected !== actual, actual, expected, message );
	},

	"throws": function( block, expected, message ) {
		var actual, expectedType,
			expectedOutput = expected,
			ok = false,
			currentTest = ( this instanceof Assert && this.test ) || QUnit.config.current;

		// 'expected' is optional unless doing string comparison
		if ( message == null && typeof expected === "string" ) {
			message = expected;
			expected = null;
		}

		currentTest.ignoreGlobalErrors = true;
		try {
			block.call( currentTest.testEnvironment );
		} catch (e) {
			actual = e;
		}
		currentTest.ignoreGlobalErrors = false;

		if ( actual ) {
			expectedType = QUnit.objectType( expected );

			// we don't want to validate thrown error
			if ( !expected ) {
				ok = true;
				expectedOutput = null;

			// expected is a regexp
			} else if ( expectedType === "regexp" ) {
				ok = expected.test( errorString( actual ) );

			// expected is a string
			} else if ( expectedType === "string" ) {
				ok = expected === errorString( actual );

			// expected is a constructor, maybe an Error constructor
			} else if ( expectedType === "function" && actual instanceof expected ) {
				ok = true;

			// expected is an Error object
			} else if ( expectedType === "object" ) {
				ok = actual instanceof expected.constructor &&
					actual.name === expected.name &&
					actual.message === expected.message;

			// expected is a validation function which returns true if validation passed
			} else if ( expectedType === "function" && expected.call( {}, actual ) === true ) {
				expectedOutput = null;
				ok = true;
			}
		}

		currentTest.assert.push( ok, actual, expectedOutput, message );
	}
};

// Provide an alternative to assert.throws(), for enviroments that consider throws a reserved word
// Known to us are: Closure Compiler, Narwhal
(function() {
	/*jshint sub:true */
	Assert.prototype.raises = Assert.prototype[ "throws" ];
}());

// Test for equality any JavaScript type.
// Author: Philippe Rathé <prathe@gmail.com>
QUnit.equiv = (function() {

	// Call the o related callback with the given arguments.
	function bindCallbacks( o, callbacks, args ) {
		var prop = QUnit.objectType( o );
		if ( prop ) {
			if ( QUnit.objectType( callbacks[ prop ] ) === "function" ) {
				return callbacks[ prop ].apply( callbacks, args );
			} else {
				return callbacks[ prop ]; // or undefined
			}
		}
	}

	// the real equiv function
	var innerEquiv,

		// stack to decide between skip/abort functions
		callers = [],

		// stack to avoiding loops from circular referencing
		parents = [],
		parentsB = [],

		getProto = Object.getPrototypeOf || function( obj ) {
			/* jshint camelcase: false, proto: true */
			return obj.__proto__;
		},
		callbacks = (function() {

			// for string, boolean, number and null
			function useStrictEquality( b, a ) {

				/*jshint eqeqeq:false */
				if ( b instanceof a.constructor || a instanceof b.constructor ) {

					// to catch short annotation VS 'new' annotation of a
					// declaration
					// e.g. var i = 1;
					// var j = new Number(1);
					return a == b;
				} else {
					return a === b;
				}
			}

			return {
				"string": useStrictEquality,
				"boolean": useStrictEquality,
				"number": useStrictEquality,
				"null": useStrictEquality,
				"undefined": useStrictEquality,

				"nan": function( b ) {
					return isNaN( b );
				},

				"date": function( b, a ) {
					return QUnit.objectType( b ) === "date" && a.valueOf() === b.valueOf();
				},

				"regexp": function( b, a ) {
					return QUnit.objectType( b ) === "regexp" &&

						// the regex itself
						a.source === b.source &&

						// and its modifiers
						a.global === b.global &&

						// (gmi) ...
						a.ignoreCase === b.ignoreCase &&
						a.multiline === b.multiline &&
						a.sticky === b.sticky;
				},

				// - skip when the property is a method of an instance (OOP)
				// - abort otherwise,
				// initial === would have catch identical references anyway
				"function": function() {
					var caller = callers[ callers.length - 1 ];
					return caller !== Object && typeof caller !== "undefined";
				},

				"array": function( b, a ) {
					var i, j, len, loop, aCircular, bCircular;

					// b could be an object literal here
					if ( QUnit.objectType( b ) !== "array" ) {
						return false;
					}

					len = a.length;
					if ( len !== b.length ) {
						// safe and faster
						return false;
					}

					// track reference to avoid circular references
					parents.push( a );
					parentsB.push( b );
					for ( i = 0; i < len; i++ ) {
						loop = false;
						for ( j = 0; j < parents.length; j++ ) {
							aCircular = parents[ j ] === a[ i ];
							bCircular = parentsB[ j ] === b[ i ];
							if ( aCircular || bCircular ) {
								if ( a[ i ] === b[ i ] || aCircular && bCircular ) {
									loop = true;
								} else {
									parents.pop();
									parentsB.pop();
									return false;
								}
							}
						}
						if ( !loop && !innerEquiv( a[ i ], b[ i ] ) ) {
							parents.pop();
							parentsB.pop();
							return false;
						}
					}
					parents.pop();
					parentsB.pop();
					return true;
				},

				"object": function( b, a ) {

					/*jshint forin:false */
					var i, j, loop, aCircular, bCircular,
						// Default to true
						eq = true,
						aProperties = [],
						bProperties = [];

					// comparing constructors is more strict than using
					// instanceof
					if ( a.constructor !== b.constructor ) {

						// Allow objects with no prototype to be equivalent to
						// objects with Object as their constructor.
						if ( !( ( getProto( a ) === null && getProto( b ) === Object.prototype ) ||
							( getProto( b ) === null && getProto( a ) === Object.prototype ) ) ) {
							return false;
						}
					}

					// stack constructor before traversing properties
					callers.push( a.constructor );

					// track reference to avoid circular references
					parents.push( a );
					parentsB.push( b );

					// be strict: don't ensure hasOwnProperty and go deep
					for ( i in a ) {
						loop = false;
						for ( j = 0; j < parents.length; j++ ) {
							aCircular = parents[ j ] === a[ i ];
							bCircular = parentsB[ j ] === b[ i ];
							if ( aCircular || bCircular ) {
								if ( a[ i ] === b[ i ] || aCircular && bCircular ) {
									loop = true;
								} else {
									eq = false;
									break;
								}
							}
						}
						aProperties.push( i );
						if ( !loop && !innerEquiv( a[ i ], b[ i ] ) ) {
							eq = false;
							break;
						}
					}

					parents.pop();
					parentsB.pop();
					callers.pop(); // unstack, we are done

					for ( i in b ) {
						bProperties.push( i ); // collect b's properties
					}

					// Ensures identical properties name
					return eq && innerEquiv( aProperties.sort(), bProperties.sort() );
				}
			};
		}());

	innerEquiv = function() { // can take multiple arguments
		var args = [].slice.apply( arguments );
		if ( args.length < 2 ) {
			return true; // end transition
		}

		return ( (function( a, b ) {
			if ( a === b ) {
				return true; // catch the most you can
			} else if ( a === null || b === null || typeof a === "undefined" ||
					typeof b === "undefined" ||
					QUnit.objectType( a ) !== QUnit.objectType( b ) ) {

				// don't lose time with error prone cases
				return false;
			} else {
				return bindCallbacks( a, callbacks, [ b, a ] );
			}

			// apply transition with (1..n) arguments
		}( args[ 0 ], args[ 1 ] ) ) &&
			innerEquiv.apply( this, args.splice( 1, args.length - 1 ) ) );
	};

	return innerEquiv;
}());

// Based on jsDump by Ariel Flesler
// http://flesler.blogspot.com/2008/05/jsdump-pretty-dump-of-any-javascript.html
QUnit.dump = (function() {
	function quote( str ) {
		return "\"" + str.toString().replace( /"/g, "\\\"" ) + "\"";
	}
	function literal( o ) {
		return o + "";
	}
	function join( pre, arr, post ) {
		var s = dump.separator(),
			base = dump.indent(),
			inner = dump.indent( 1 );
		if ( arr.join ) {
			arr = arr.join( "," + s + inner );
		}
		if ( !arr ) {
			return pre + post;
		}
		return [ pre, inner + arr, base + post ].join( s );
	}
	function array( arr, stack ) {
		var i = arr.length,
			ret = new Array( i );

		if ( dump.maxDepth && dump.depth > dump.maxDepth ) {
			return "[object Array]";
		}

		this.up();
		while ( i-- ) {
			ret[ i ] = this.parse( arr[ i ], undefined, stack );
		}
		this.down();
		return join( "[", ret, "]" );
	}

	var reName = /^function (\w+)/,
		dump = {

			// objType is used mostly internally, you can fix a (custom) type in advance
			parse: function( obj, objType, stack ) {
				stack = stack || [];
				var res, parser, parserType,
					inStack = inArray( obj, stack );

				if ( inStack !== -1 ) {
					return "recursion(" + ( inStack - stack.length ) + ")";
				}

				objType = objType || this.typeOf( obj  );
				parser = this.parsers[ objType ];
				parserType = typeof parser;

				if ( parserType === "function" ) {
					stack.push( obj );
					res = parser.call( this, obj, stack );
					stack.pop();
					return res;
				}
				return ( parserType === "string" ) ? parser : this.parsers.error;
			},
			typeOf: function( obj ) {
				var type;
				if ( obj === null ) {
					type = "null";
				} else if ( typeof obj === "undefined" ) {
					type = "undefined";
				} else if ( QUnit.is( "regexp", obj ) ) {
					type = "regexp";
				} else if ( QUnit.is( "date", obj ) ) {
					type = "date";
				} else if ( QUnit.is( "function", obj ) ) {
					type = "function";
				} else if ( obj.setInterval !== undefined &&
						obj.document !== undefined &&
						obj.nodeType === undefined ) {
					type = "window";
				} else if ( obj.nodeType === 9 ) {
					type = "document";
				} else if ( obj.nodeType ) {
					type = "node";
				} else if (

					// native arrays
					toString.call( obj ) === "[object Array]" ||

					// NodeList objects
					( typeof obj.length === "number" && obj.item !== undefined &&
					( obj.length ? obj.item( 0 ) === obj[ 0 ] : ( obj.item( 0 ) === null &&
					obj[ 0 ] === undefined ) ) )
				) {
					type = "array";
				} else if ( obj.constructor === Error.prototype.constructor ) {
					type = "error";
				} else {
					type = typeof obj;
				}
				return type;
			},
			separator: function() {
				return this.multiline ? this.HTML ? "<br />" : "\n" : this.HTML ? "&#160;" : " ";
			},
			// extra can be a number, shortcut for increasing-calling-decreasing
			indent: function( extra ) {
				if ( !this.multiline ) {
					return "";
				}
				var chr = this.indentChar;
				if ( this.HTML ) {
					chr = chr.replace( /\t/g, "   " ).replace( / /g, "&#160;" );
				}
				return new Array( this.depth + ( extra || 0 ) ).join( chr );
			},
			up: function( a ) {
				this.depth += a || 1;
			},
			down: function( a ) {
				this.depth -= a || 1;
			},
			setParser: function( name, parser ) {
				this.parsers[ name ] = parser;
			},
			// The next 3 are exposed so you can use them
			quote: quote,
			literal: literal,
			join: join,
			//
			depth: 1,
			maxDepth: QUnit.config.maxDepth,

			// This is the list of parsers, to modify them, use dump.setParser
			parsers: {
				window: "[Window]",
				document: "[Document]",
				error: function( error ) {
					return "Error(\"" + error.message + "\")";
				},
				unknown: "[Unknown]",
				"null": "null",
				"undefined": "undefined",
				"function": function( fn ) {
					var ret = "function",

						// functions never have name in IE
						name = "name" in fn ? fn.name : ( reName.exec( fn ) || [] )[ 1 ];

					if ( name ) {
						ret += " " + name;
					}
					ret += "( ";

					ret = [ ret, dump.parse( fn, "functionArgs" ), "){" ].join( "" );
					return join( ret, dump.parse( fn, "functionCode" ), "}" );
				},
				array: array,
				nodelist: array,
				"arguments": array,
				object: function( map, stack ) {
					var keys, key, val, i, nonEnumerableProperties,
						ret = [];

					if ( dump.maxDepth && dump.depth > dump.maxDepth ) {
						return "[object Object]";
					}

					dump.up();
					keys = [];
					for ( key in map ) {
						keys.push( key );
					}

					// Some properties are not always enumerable on Error objects.
					nonEnumerableProperties = [ "message", "name" ];
					for ( i in nonEnumerableProperties ) {
						key = nonEnumerableProperties[ i ];
						if ( key in map && inArray( key, keys ) < 0 ) {
							keys.push( key );
						}
					}
					keys.sort();
					for ( i = 0; i < keys.length; i++ ) {
						key = keys[ i ];
						val = map[ key ];
						ret.push( dump.parse( key, "key" ) + ": " +
							dump.parse( val, undefined, stack ) );
					}
					dump.down();
					return join( "{", ret, "}" );
				},
				node: function( node ) {
					var len, i, val,
						open = dump.HTML ? "&lt;" : "<",
						close = dump.HTML ? "&gt;" : ">",
						tag = node.nodeName.toLowerCase(),
						ret = open + tag,
						attrs = node.attributes;

					if ( attrs ) {
						for ( i = 0, len = attrs.length; i < len; i++ ) {
							val = attrs[ i ].nodeValue;

							// IE6 includes all attributes in .attributes, even ones not explicitly
							// set. Those have values like undefined, null, 0, false, "" or
							// "inherit".
							if ( val && val !== "inherit" ) {
								ret += " " + attrs[ i ].nodeName + "=" +
									dump.parse( val, "attribute" );
							}
						}
					}
					ret += close;

					// Show content of TextNode or CDATASection
					if ( node.nodeType === 3 || node.nodeType === 4 ) {
						ret += node.nodeValue;
					}

					return ret + open + "/" + tag + close;
				},

				// function calls it internally, it's the arguments part of the function
				functionArgs: function( fn ) {
					var args,
						l = fn.length;

					if ( !l ) {
						return "";
					}

					args = new Array( l );
					while ( l-- ) {

						// 97 is 'a'
						args[ l ] = String.fromCharCode( 97 + l );
					}
					return " " + args.join( ", " ) + " ";
				},
				// object calls it internally, the key part of an item in a map
				key: quote,
				// function calls it internally, it's the content of the function
				functionCode: "[code]",
				// node calls it internally, it's an html attribute value
				attribute: quote,
				string: quote,
				date: quote,
				regexp: literal,
				number: literal,
				"boolean": literal
			},
			// if true, entities are escaped ( <, >, \t, space and \n )
			HTML: false,
			// indentation unit
			indentChar: "  ",
			// if true, items in a collection, are separated by a \n, else just a space.
			multiline: true
		};

	return dump;
}());

// back compat
QUnit.jsDump = QUnit.dump;

// For browser, export only select globals
if ( typeof window !== "undefined" ) {

	// Deprecated
	// Extend assert methods to QUnit and Global scope through Backwards compatibility
	(function() {
		var i,
			assertions = Assert.prototype;

		function applyCurrent( current ) {
			return function() {
				var assert = new Assert( QUnit.config.current );
				current.apply( assert, arguments );
			};
		}

		for ( i in assertions ) {
			QUnit[ i ] = applyCurrent( assertions[ i ] );
		}
	})();

	(function() {
		var i, l,
			keys = [
				"test",
				"module",
				"expect",
				"asyncTest",
				"start",
				"stop",
				"ok",
				"notOk",
				"equal",
				"notEqual",
				"propEqual",
				"notPropEqual",
				"deepEqual",
				"notDeepEqual",
				"strictEqual",
				"notStrictEqual",
				"throws"
			];

		for ( i = 0, l = keys.length; i < l; i++ ) {
			window[ keys[ i ] ] = QUnit[ keys[ i ] ];
		}
	})();

	window.QUnit = QUnit;
}

// For nodejs
if ( typeof module !== "undefined" && module && module.exports ) {
	module.exports = QUnit;

	// For consistency with CommonJS environments' exports
	module.exports.QUnit = QUnit;
}

// For CommonJS with exports, but without module.exports, like Rhino
if ( typeof exports !== "undefined" && exports ) {
	exports.QUnit = QUnit;
}

if ( typeof define === "function" && define.amd ) {
	define( function() {
		return QUnit;
	} );
	QUnit.config.autostart = false;
}

// Get a reference to the global object, like window in browsers
}( (function() {
	return this;
})() ));

/*istanbul ignore next */
// jscs:disable maximumLineLength
/*
 * This file is a modified version of google-diff-match-patch's JavaScript implementation
 * (https://code.google.com/p/google-diff-match-patch/source/browse/trunk/javascript/diff_match_patch_uncompressed.js),
 * modifications are licensed as more fully set forth in LICENSE.txt.
 *
 * The original source of google-diff-match-patch is attributable and licensed as follows:
 *
 * Copyright 2006 Google Inc.
 * http://code.google.com/p/google-diff-match-patch/
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * More Info:
 *  https://code.google.com/p/google-diff-match-patch/
 *
 * Usage: QUnit.diff(expected, actual)
 *
 * QUnit.diff( "the quick brown fox jumped over", "the quick fox jumps over" ) === "the  quick <del>brown </del> fox jump<ins>s</ins><del>ed</del over"
 */
QUnit.diff = (function() {

    function DiffMatchPatch() {

        // Defaults.
        // Redefine these in your program to override the defaults.

        // Number of seconds to map a diff before giving up (0 for infinity).
        this.DiffTimeout = 1.0;
        // Cost of an empty edit operation in terms of edit characters.
        this.DiffEditCost = 4;
    }

    //  DIFF FUNCTIONS

    /**
     * The data structure representing a diff is an array of tuples:
     * [[DIFF_DELETE, 'Hello'], [DIFF_INSERT, 'Goodbye'], [DIFF_EQUAL, ' world.']]
     * which means: delete 'Hello', add 'Goodbye' and keep ' world.'
     */
    var DIFF_DELETE = -1,
		DIFF_INSERT = 1,
		DIFF_EQUAL = 0;

    /**
     * Find the differences between two texts.  Simplifies the problem by stripping
     * any common prefix or suffix off the texts before diffing.
     * @param {string} text1 Old string to be diffed.
     * @param {string} text2 New string to be diffed.
     * @param {boolean=} optChecklines Optional speedup flag. If present and false,
     *     then don't run a line-level diff first to identify the changed areas.
     *     Defaults to true, which does a faster, slightly less optimal diff.
     * @param {number} optDeadline Optional time when the diff should be complete
     *     by.  Used internally for recursive calls.  Users should set DiffTimeout
     *     instead.
     * @return {!Array.<!DiffMatchPatch.Diff>} Array of diff tuples.
     */
    DiffMatchPatch.prototype.DiffMain = function( text1, text2, optChecklines, optDeadline ) {
        var deadline, checklines, commonlength,
			commonprefix, commonsuffix, diffs;
        // Set a deadline by which time the diff must be complete.
        if ( typeof optDeadline === "undefined" ) {
            if ( this.DiffTimeout <= 0 ) {
                optDeadline = Number.MAX_VALUE;
            } else {
                optDeadline = ( new Date() ).getTime() + this.DiffTimeout * 1000;
            }
        }
        deadline = optDeadline;

        // Check for null inputs.
        if ( text1 === null || text2 === null ) {
            throw new Error( "Null input. (DiffMain)" );
        }

        // Check for equality (speedup).
        if ( text1 === text2 ) {
            if ( text1 ) {
                return [
                    [ DIFF_EQUAL, text1 ]
                ];
            }
            return [];
        }

        if ( typeof optChecklines === "undefined" ) {
            optChecklines = true;
        }

        checklines = optChecklines;

        // Trim off common prefix (speedup).
        commonlength = this.diffCommonPrefix( text1, text2 );
        commonprefix = text1.substring( 0, commonlength );
        text1 = text1.substring( commonlength );
        text2 = text2.substring( commonlength );

        // Trim off common suffix (speedup).
        /////////
        commonlength = this.diffCommonSuffix( text1, text2 );
        commonsuffix = text1.substring( text1.length - commonlength );
        text1 = text1.substring( 0, text1.length - commonlength );
        text2 = text2.substring( 0, text2.length - commonlength );

        // Compute the diff on the middle block.
        diffs = this.diffCompute( text1, text2, checklines, deadline );

        // Restore the prefix and suffix.
        if ( commonprefix ) {
            diffs.unshift( [ DIFF_EQUAL, commonprefix ] );
        }
        if ( commonsuffix ) {
            diffs.push( [ DIFF_EQUAL, commonsuffix ] );
        }
        this.diffCleanupMerge( diffs );
        return diffs;
    };

    /**
     * Reduce the number of edits by eliminating operationally trivial equalities.
     * @param {!Array.<!DiffMatchPatch.Diff>} diffs Array of diff tuples.
     */
    DiffMatchPatch.prototype.diffCleanupEfficiency = function( diffs ) {
        var changes, equalities, equalitiesLength, lastequality,
			pointer, preIns, preDel, postIns, postDel;
        changes = false;
        equalities = []; // Stack of indices where equalities are found.
        equalitiesLength = 0; // Keeping our own length var is faster in JS.
        /** @type {?string} */
        lastequality = null;
        // Always equal to diffs[equalities[equalitiesLength - 1]][1]
        pointer = 0; // Index of current position.
        // Is there an insertion operation before the last equality.
        preIns = false;
        // Is there a deletion operation before the last equality.
        preDel = false;
        // Is there an insertion operation after the last equality.
        postIns = false;
        // Is there a deletion operation after the last equality.
        postDel = false;
        while ( pointer < diffs.length ) {
            if ( diffs[ pointer ][ 0 ] === DIFF_EQUAL ) { // Equality found.
                if ( diffs[ pointer ][ 1 ].length < this.DiffEditCost && ( postIns || postDel ) ) {
                    // Candidate found.
                    equalities[ equalitiesLength++ ] = pointer;
                    preIns = postIns;
                    preDel = postDel;
                    lastequality = diffs[ pointer ][ 1 ];
                } else {
                    // Not a candidate, and can never become one.
                    equalitiesLength = 0;
                    lastequality = null;
                }
                postIns = postDel = false;
            } else { // An insertion or deletion.
                if ( diffs[ pointer ][ 0 ] === DIFF_DELETE ) {
                    postDel = true;
                } else {
                    postIns = true;
                }
                /*
                 * Five types to be split:
                 * <ins>A</ins><del>B</del>XY<ins>C</ins><del>D</del>
                 * <ins>A</ins>X<ins>C</ins><del>D</del>
                 * <ins>A</ins><del>B</del>X<ins>C</ins>
                 * <ins>A</del>X<ins>C</ins><del>D</del>
                 * <ins>A</ins><del>B</del>X<del>C</del>
                 */
                if ( lastequality && ( ( preIns && preDel && postIns && postDel ) ||
                        ( ( lastequality.length < this.DiffEditCost / 2 ) &&
                            ( preIns + preDel + postIns + postDel ) === 3 ) ) ) {
                    // Duplicate record.
                    diffs.splice( equalities[equalitiesLength - 1], 0, [ DIFF_DELETE, lastequality ] );
                    // Change second copy to insert.
                    diffs[ equalities[ equalitiesLength - 1 ] + 1 ][ 0 ] = DIFF_INSERT;
                    equalitiesLength--; // Throw away the equality we just deleted;
                    lastequality = null;
                    if (preIns && preDel) {
                        // No changes made which could affect previous entry, keep going.
                        postIns = postDel = true;
                        equalitiesLength = 0;
                    } else {
                        equalitiesLength--; // Throw away the previous equality.
                        pointer = equalitiesLength > 0 ? equalities[ equalitiesLength - 1 ] : -1;
                        postIns = postDel = false;
                    }
                    changes = true;
                }
            }
            pointer++;
        }

        if ( changes ) {
            this.diffCleanupMerge( diffs );
        }
    };

    /**
     * Convert a diff array into a pretty HTML report.
     * @param {!Array.<!DiffMatchPatch.Diff>} diffs Array of diff tuples.
     * @param {integer} string to be beautified.
     * @return {string} HTML representation.
     */
    DiffMatchPatch.prototype.diffPrettyHtml = function( diffs ) {
        var op, data, x, html = [];
        for ( x = 0; x < diffs.length; x++ ) {
            op = diffs[x][0]; // Operation (insert, delete, equal)
            data = diffs[x][1]; // Text of change.
            switch ( op ) {
                case DIFF_INSERT:
                    html[x] = "<ins>" + data + "</ins>";
                    break;
                case DIFF_DELETE:
                    html[x] = "<del>" + data + "</del>";
                    break;
                case DIFF_EQUAL:
                    html[x] = "<span>" + data + "</span>";
                    break;
            }
        }
        return html.join("");
    };

    /**
     * Determine the common prefix of two strings.
     * @param {string} text1 First string.
     * @param {string} text2 Second string.
     * @return {number} The number of characters common to the start of each
     *     string.
     */
    DiffMatchPatch.prototype.diffCommonPrefix = function( text1, text2 ) {
        var pointermid, pointermax, pointermin, pointerstart;
        // Quick check for common null cases.
        if ( !text1 || !text2 || text1.charAt(0) !== text2.charAt(0) ) {
            return 0;
        }
        // Binary search.
        // Performance analysis: http://neil.fraser.name/news/2007/10/09/
        pointermin = 0;
        pointermax = Math.min( text1.length, text2.length );
        pointermid = pointermax;
        pointerstart = 0;
        while ( pointermin < pointermid ) {
            if ( text1.substring( pointerstart, pointermid ) === text2.substring( pointerstart, pointermid ) ) {
                pointermin = pointermid;
                pointerstart = pointermin;
            } else {
                pointermax = pointermid;
            }
            pointermid = Math.floor( ( pointermax - pointermin ) / 2 + pointermin );
        }
        return pointermid;
    };

    /**
     * Determine the common suffix of two strings.
     * @param {string} text1 First string.
     * @param {string} text2 Second string.
     * @return {number} The number of characters common to the end of each string.
     */
    DiffMatchPatch.prototype.diffCommonSuffix = function( text1, text2 ) {
        var pointermid, pointermax, pointermin, pointerend;
        // Quick check for common null cases.
        if (!text1 || !text2 || text1.charAt(text1.length - 1) !== text2.charAt(text2.length - 1)) {
            return 0;
        }
        // Binary search.
        // Performance analysis: http://neil.fraser.name/news/2007/10/09/
        pointermin = 0;
        pointermax = Math.min(text1.length, text2.length);
        pointermid = pointermax;
        pointerend = 0;
        while ( pointermin < pointermid ) {
            if (text1.substring( text1.length - pointermid, text1.length - pointerend ) ===
                text2.substring( text2.length - pointermid, text2.length - pointerend ) ) {
                pointermin = pointermid;
                pointerend = pointermin;
            } else {
                pointermax = pointermid;
            }
            pointermid = Math.floor( ( pointermax - pointermin ) / 2 + pointermin );
        }
        return pointermid;
    };

    /**
     * Find the differences between two texts.  Assumes that the texts do not
     * have any common prefix or suffix.
     * @param {string} text1 Old string to be diffed.
     * @param {string} text2 New string to be diffed.
     * @param {boolean} checklines Speedup flag.  If false, then don't run a
     *     line-level diff first to identify the changed areas.
     *     If true, then run a faster, slightly less optimal diff.
     * @param {number} deadline Time when the diff should be complete by.
     * @return {!Array.<!DiffMatchPatch.Diff>} Array of diff tuples.
     * @private
     */
    DiffMatchPatch.prototype.diffCompute = function( text1, text2, checklines, deadline ) {
        var diffs, longtext, shorttext, i, hm,
			text1A, text2A, text1B, text2B,
			midCommon, diffsA, diffsB;

        if ( !text1 ) {
            // Just add some text (speedup).
            return [
                [ DIFF_INSERT, text2 ]
            ];
        }

        if (!text2) {
            // Just delete some text (speedup).
            return [
                [ DIFF_DELETE, text1 ]
            ];
        }

        longtext = text1.length > text2.length ? text1 : text2;
        shorttext = text1.length > text2.length ? text2 : text1;
        i = longtext.indexOf( shorttext );
        if ( i !== -1 ) {
            // Shorter text is inside the longer text (speedup).
            diffs = [
                [ DIFF_INSERT, longtext.substring( 0, i ) ],
                [ DIFF_EQUAL, shorttext ],
                [ DIFF_INSERT, longtext.substring( i + shorttext.length ) ]
            ];
            // Swap insertions for deletions if diff is reversed.
            if ( text1.length > text2.length ) {
                diffs[0][0] = diffs[2][0] = DIFF_DELETE;
            }
            return diffs;
        }

        if ( shorttext.length === 1 ) {
            // Single character string.
            // After the previous speedup, the character can't be an equality.
            return [
                [ DIFF_DELETE, text1 ],
                [ DIFF_INSERT, text2 ]
            ];
        }

        // Check to see if the problem can be split in two.
        hm = this.diffHalfMatch(text1, text2);
        if (hm) {
            // A half-match was found, sort out the return data.
            text1A = hm[0];
            text1B = hm[1];
            text2A = hm[2];
            text2B = hm[3];
            midCommon = hm[4];
            // Send both pairs off for separate processing.
            diffsA = this.DiffMain(text1A, text2A, checklines, deadline);
            diffsB = this.DiffMain(text1B, text2B, checklines, deadline);
            // Merge the results.
            return diffsA.concat([
                [ DIFF_EQUAL, midCommon ]
            ], diffsB);
        }

        if (checklines && text1.length > 100 && text2.length > 100) {
            return this.diffLineMode(text1, text2, deadline);
        }

        return this.diffBisect(text1, text2, deadline);
    };

    /**
     * Do the two texts share a substring which is at least half the length of the
     * longer text?
     * This speedup can produce non-minimal diffs.
     * @param {string} text1 First string.
     * @param {string} text2 Second string.
     * @return {Array.<string>} Five element Array, containing the prefix of
     *     text1, the suffix of text1, the prefix of text2, the suffix of
     *     text2 and the common middle.  Or null if there was no match.
     * @private
     */
    DiffMatchPatch.prototype.diffHalfMatch = function(text1, text2) {
        var longtext, shorttext, dmp,
			text1A, text2B, text2A, text1B, midCommon,
			hm1, hm2, hm;
        if (this.DiffTimeout <= 0) {
            // Don't risk returning a non-optimal diff if we have unlimited time.
            return null;
        }
        longtext = text1.length > text2.length ? text1 : text2;
        shorttext = text1.length > text2.length ? text2 : text1;
        if (longtext.length < 4 || shorttext.length * 2 < longtext.length) {
            return null; // Pointless.
        }
        dmp = this; // 'this' becomes 'window' in a closure.

        /**
         * Does a substring of shorttext exist within longtext such that the substring
         * is at least half the length of longtext?
         * Closure, but does not reference any external variables.
         * @param {string} longtext Longer string.
         * @param {string} shorttext Shorter string.
         * @param {number} i Start index of quarter length substring within longtext.
         * @return {Array.<string>} Five element Array, containing the prefix of
         *     longtext, the suffix of longtext, the prefix of shorttext, the suffix
         *     of shorttext and the common middle.  Or null if there was no match.
         * @private
         */
        function diffHalfMatchI(longtext, shorttext, i) {
            var seed, j, bestCommon, prefixLength, suffixLength,
				bestLongtextA, bestLongtextB, bestShorttextA, bestShorttextB;
            // Start with a 1/4 length substring at position i as a seed.
            seed = longtext.substring(i, i + Math.floor(longtext.length / 4));
            j = -1;
            bestCommon = "";
            while ((j = shorttext.indexOf(seed, j + 1)) !== -1) {
                prefixLength = dmp.diffCommonPrefix(longtext.substring(i),
                    shorttext.substring(j));
                suffixLength = dmp.diffCommonSuffix(longtext.substring(0, i),
                    shorttext.substring(0, j));
                if (bestCommon.length < suffixLength + prefixLength) {
                    bestCommon = shorttext.substring(j - suffixLength, j) +
                        shorttext.substring(j, j + prefixLength);
                    bestLongtextA = longtext.substring(0, i - suffixLength);
                    bestLongtextB = longtext.substring(i + prefixLength);
                    bestShorttextA = shorttext.substring(0, j - suffixLength);
                    bestShorttextB = shorttext.substring(j + prefixLength);
                }
            }
            if (bestCommon.length * 2 >= longtext.length) {
                return [ bestLongtextA, bestLongtextB,
                    bestShorttextA, bestShorttextB, bestCommon
                ];
            } else {
                return null;
            }
        }

        // First check if the second quarter is the seed for a half-match.
        hm1 = diffHalfMatchI(longtext, shorttext,
            Math.ceil(longtext.length / 4));
        // Check again based on the third quarter.
        hm2 = diffHalfMatchI(longtext, shorttext,
            Math.ceil(longtext.length / 2));
        if (!hm1 && !hm2) {
            return null;
        } else if (!hm2) {
            hm = hm1;
        } else if (!hm1) {
            hm = hm2;
        } else {
            // Both matched.  Select the longest.
            hm = hm1[4].length > hm2[4].length ? hm1 : hm2;
        }

        // A half-match was found, sort out the return data.
        text1A, text1B, text2A, text2B;
        if (text1.length > text2.length) {
            text1A = hm[0];
            text1B = hm[1];
            text2A = hm[2];
            text2B = hm[3];
        } else {
            text2A = hm[0];
            text2B = hm[1];
            text1A = hm[2];
            text1B = hm[3];
        }
        midCommon = hm[4];
        return [ text1A, text1B, text2A, text2B, midCommon ];
    };

    /**
     * Do a quick line-level diff on both strings, then rediff the parts for
     * greater accuracy.
     * This speedup can produce non-minimal diffs.
     * @param {string} text1 Old string to be diffed.
     * @param {string} text2 New string to be diffed.
     * @param {number} deadline Time when the diff should be complete by.
     * @return {!Array.<!DiffMatchPatch.Diff>} Array of diff tuples.
     * @private
     */
    DiffMatchPatch.prototype.diffLineMode = function(text1, text2, deadline) {
        var a, diffs, linearray, pointer, countInsert,
			countDelete, textInsert, textDelete, j;
        // Scan the text on a line-by-line basis first.
        a = this.diffLinesToChars(text1, text2);
        text1 = a.chars1;
        text2 = a.chars2;
        linearray = a.lineArray;

        diffs = this.DiffMain(text1, text2, false, deadline);

        // Convert the diff back to original text.
        this.diffCharsToLines(diffs, linearray);
        // Eliminate freak matches (e.g. blank lines)
        this.diffCleanupSemantic(diffs);

        // Rediff any replacement blocks, this time character-by-character.
        // Add a dummy entry at the end.
        diffs.push( [ DIFF_EQUAL, "" ] );
        pointer = 0;
        countDelete = 0;
        countInsert = 0;
        textDelete = "";
        textInsert = "";
        while (pointer < diffs.length) {
            switch ( diffs[pointer][0] ) {
                case DIFF_INSERT:
                    countInsert++;
                    textInsert += diffs[pointer][1];
                    break;
                case DIFF_DELETE:
                    countDelete++;
                    textDelete += diffs[pointer][1];
                    break;
                case DIFF_EQUAL:
                    // Upon reaching an equality, check for prior redundancies.
                    if (countDelete >= 1 && countInsert >= 1) {
                        // Delete the offending records and add the merged ones.
                        diffs.splice(pointer - countDelete - countInsert,
                            countDelete + countInsert);
                        pointer = pointer - countDelete - countInsert;
                        a = this.DiffMain(textDelete, textInsert, false, deadline);
                        for (j = a.length - 1; j >= 0; j--) {
                            diffs.splice( pointer, 0, a[j] );
                        }
                        pointer = pointer + a.length;
                    }
                    countInsert = 0;
                    countDelete = 0;
                    textDelete = "";
                    textInsert = "";
                    break;
            }
            pointer++;
        }
        diffs.pop(); // Remove the dummy entry at the end.

        return diffs;
    };

    /**
     * Find the 'middle snake' of a diff, split the problem in two
     * and return the recursively constructed diff.
     * See Myers 1986 paper: An O(ND) Difference Algorithm and Its Variations.
     * @param {string} text1 Old string to be diffed.
     * @param {string} text2 New string to be diffed.
     * @param {number} deadline Time at which to bail if not yet complete.
     * @return {!Array.<!DiffMatchPatch.Diff>} Array of diff tuples.
     * @private
     */
    DiffMatchPatch.prototype.diffBisect = function(text1, text2, deadline) {
        var text1Length, text2Length, maxD, vOffset, vLength,
			v1, v2, x, delta, front, k1start, k1end, k2start,
			k2end, k2Offset, k1Offset, x1, x2, y1, y2, d, k1, k2;
        // Cache the text lengths to prevent multiple calls.
        text1Length = text1.length;
        text2Length = text2.length;
        maxD = Math.ceil((text1Length + text2Length) / 2);
        vOffset = maxD;
        vLength = 2 * maxD;
        v1 = new Array(vLength);
        v2 = new Array(vLength);
        // Setting all elements to -1 is faster in Chrome & Firefox than mixing
        // integers and undefined.
        for (x = 0; x < vLength; x++) {
            v1[x] = -1;
            v2[x] = -1;
        }
        v1[vOffset + 1] = 0;
        v2[vOffset + 1] = 0;
        delta = text1Length - text2Length;
        // If the total number of characters is odd, then the front path will collide
        // with the reverse path.
        front = (delta % 2 !== 0);
        // Offsets for start and end of k loop.
        // Prevents mapping of space beyond the grid.
        k1start = 0;
        k1end = 0;
        k2start = 0;
        k2end = 0;
        for (d = 0; d < maxD; d++) {
            // Bail out if deadline is reached.
            if ((new Date()).getTime() > deadline) {
                break;
            }

            // Walk the front path one step.
            for (k1 = -d + k1start; k1 <= d - k1end; k1 += 2) {
                k1Offset = vOffset + k1;
                if ( k1 === -d || ( k1 !== d && v1[ k1Offset - 1 ] < v1[ k1Offset + 1 ] ) ) {
                    x1 = v1[k1Offset + 1];
                } else {
                    x1 = v1[k1Offset - 1] + 1;
                }
                y1 = x1 - k1;
                while (x1 < text1Length && y1 < text2Length &&
                    text1.charAt(x1) === text2.charAt(y1)) {
                    x1++;
                    y1++;
                }
                v1[k1Offset] = x1;
                if (x1 > text1Length) {
                    // Ran off the right of the graph.
                    k1end += 2;
                } else if (y1 > text2Length) {
                    // Ran off the bottom of the graph.
                    k1start += 2;
                } else if (front) {
                    k2Offset = vOffset + delta - k1;
                    if (k2Offset >= 0 && k2Offset < vLength && v2[k2Offset] !== -1) {
                        // Mirror x2 onto top-left coordinate system.
                        x2 = text1Length - v2[k2Offset];
                        if (x1 >= x2) {
                            // Overlap detected.
                            return this.diffBisectSplit(text1, text2, x1, y1, deadline);
                        }
                    }
                }
            }

            // Walk the reverse path one step.
            for (k2 = -d + k2start; k2 <= d - k2end; k2 += 2) {
                k2Offset = vOffset + k2;
                if ( k2 === -d || (k2 !== d && v2[ k2Offset - 1 ] < v2[ k2Offset + 1 ] ) ) {
                    x2 = v2[k2Offset + 1];
                } else {
                    x2 = v2[k2Offset - 1] + 1;
                }
                y2 = x2 - k2;
                while (x2 < text1Length && y2 < text2Length &&
                    text1.charAt(text1Length - x2 - 1) ===
                    text2.charAt(text2Length - y2 - 1)) {
                    x2++;
                    y2++;
                }
                v2[k2Offset] = x2;
                if (x2 > text1Length) {
                    // Ran off the left of the graph.
                    k2end += 2;
                } else if (y2 > text2Length) {
                    // Ran off the top of the graph.
                    k2start += 2;
                } else if (!front) {
                    k1Offset = vOffset + delta - k2;
                    if (k1Offset >= 0 && k1Offset < vLength && v1[k1Offset] !== -1) {
                        x1 = v1[k1Offset];
                        y1 = vOffset + x1 - k1Offset;
                        // Mirror x2 onto top-left coordinate system.
                        x2 = text1Length - x2;
                        if (x1 >= x2) {
                            // Overlap detected.
                            return this.diffBisectSplit(text1, text2, x1, y1, deadline);
                        }
                    }
                }
            }
        }
        // Diff took too long and hit the deadline or
        // number of diffs equals number of characters, no commonality at all.
        return [
            [ DIFF_DELETE, text1 ],
            [ DIFF_INSERT, text2 ]
        ];
    };

    /**
     * Given the location of the 'middle snake', split the diff in two parts
     * and recurse.
     * @param {string} text1 Old string to be diffed.
     * @param {string} text2 New string to be diffed.
     * @param {number} x Index of split point in text1.
     * @param {number} y Index of split point in text2.
     * @param {number} deadline Time at which to bail if not yet complete.
     * @return {!Array.<!DiffMatchPatch.Diff>} Array of diff tuples.
     * @private
     */
    DiffMatchPatch.prototype.diffBisectSplit = function( text1, text2, x, y, deadline ) {
        var text1a, text1b, text2a, text2b, diffs, diffsb;
        text1a = text1.substring(0, x);
        text2a = text2.substring(0, y);
        text1b = text1.substring(x);
        text2b = text2.substring(y);

        // Compute both diffs serially.
        diffs = this.DiffMain(text1a, text2a, false, deadline);
        diffsb = this.DiffMain(text1b, text2b, false, deadline);

        return diffs.concat(diffsb);
    };

    /**
     * Reduce the number of edits by eliminating semantically trivial equalities.
     * @param {!Array.<!DiffMatchPatch.Diff>} diffs Array of diff tuples.
     */
    DiffMatchPatch.prototype.diffCleanupSemantic = function(diffs) {
        var changes, equalities, equalitiesLength, lastequality,
			pointer, lengthInsertions2, lengthDeletions2, lengthInsertions1,
			lengthDeletions1, deletion, insertion, overlapLength1, overlapLength2;
        changes = false;
        equalities = []; // Stack of indices where equalities are found.
        equalitiesLength = 0; // Keeping our own length var is faster in JS.
        /** @type {?string} */
        lastequality = null;
        // Always equal to diffs[equalities[equalitiesLength - 1]][1]
        pointer = 0; // Index of current position.
        // Number of characters that changed prior to the equality.
        lengthInsertions1 = 0;
        lengthDeletions1 = 0;
        // Number of characters that changed after the equality.
        lengthInsertions2 = 0;
        lengthDeletions2 = 0;
        while (pointer < diffs.length) {
            if (diffs[pointer][0] === DIFF_EQUAL) { // Equality found.
                equalities[equalitiesLength++] = pointer;
                lengthInsertions1 = lengthInsertions2;
                lengthDeletions1 = lengthDeletions2;
                lengthInsertions2 = 0;
                lengthDeletions2 = 0;
                lastequality = diffs[pointer][1];
            } else { // An insertion or deletion.
                if (diffs[pointer][0] === DIFF_INSERT) {
                    lengthInsertions2 += diffs[pointer][1].length;
                } else {
                    lengthDeletions2 += diffs[pointer][1].length;
                }
                // Eliminate an equality that is smaller or equal to the edits on both
                // sides of it.
                if (lastequality && (lastequality.length <=
                        Math.max(lengthInsertions1, lengthDeletions1)) &&
                    (lastequality.length <= Math.max(lengthInsertions2,
                        lengthDeletions2))) {
                    // Duplicate record.
                    diffs.splice( equalities[ equalitiesLength - 1 ], 0, [ DIFF_DELETE, lastequality ] );
                    // Change second copy to insert.
                    diffs[equalities[equalitiesLength - 1] + 1][0] = DIFF_INSERT;
                    // Throw away the equality we just deleted.
                    equalitiesLength--;
                    // Throw away the previous equality (it needs to be reevaluated).
                    equalitiesLength--;
                    pointer = equalitiesLength > 0 ? equalities[equalitiesLength - 1] : -1;
                    lengthInsertions1 = 0; // Reset the counters.
                    lengthDeletions1 = 0;
                    lengthInsertions2 = 0;
                    lengthDeletions2 = 0;
                    lastequality = null;
                    changes = true;
                }
            }
            pointer++;
        }

        // Normalize the diff.
        if (changes) {
            this.diffCleanupMerge(diffs);
        }

        // Find any overlaps between deletions and insertions.
        // e.g: <del>abcxxx</del><ins>xxxdef</ins>
        //   -> <del>abc</del>xxx<ins>def</ins>
        // e.g: <del>xxxabc</del><ins>defxxx</ins>
        //   -> <ins>def</ins>xxx<del>abc</del>
        // Only extract an overlap if it is as big as the edit ahead or behind it.
        pointer = 1;
        while (pointer < diffs.length) {
            if (diffs[pointer - 1][0] === DIFF_DELETE &&
                diffs[pointer][0] === DIFF_INSERT) {
                deletion = diffs[pointer - 1][1];
                insertion = diffs[pointer][1];
                overlapLength1 = this.diffCommonOverlap(deletion, insertion);
                overlapLength2 = this.diffCommonOverlap(insertion, deletion);
                if (overlapLength1 >= overlapLength2) {
                    if (overlapLength1 >= deletion.length / 2 ||
                        overlapLength1 >= insertion.length / 2) {
                        // Overlap found.  Insert an equality and trim the surrounding edits.
                        diffs.splice( pointer, 0, [ DIFF_EQUAL, insertion.substring( 0, overlapLength1 ) ] );
                        diffs[pointer - 1][1] =
                            deletion.substring(0, deletion.length - overlapLength1);
                        diffs[pointer + 1][1] = insertion.substring(overlapLength1);
                        pointer++;
                    }
                } else {
                    if (overlapLength2 >= deletion.length / 2 ||
                        overlapLength2 >= insertion.length / 2) {
                        // Reverse overlap found.
                        // Insert an equality and swap and trim the surrounding edits.
                        diffs.splice( pointer, 0, [ DIFF_EQUAL, deletion.substring( 0, overlapLength2 ) ] );
                        diffs[pointer - 1][0] = DIFF_INSERT;
                        diffs[pointer - 1][1] =
                            insertion.substring(0, insertion.length - overlapLength2);
                        diffs[pointer + 1][0] = DIFF_DELETE;
                        diffs[pointer + 1][1] =
                            deletion.substring(overlapLength2);
                        pointer++;
                    }
                }
                pointer++;
            }
            pointer++;
        }
    };

    /**
     * Determine if the suffix of one string is the prefix of another.
     * @param {string} text1 First string.
     * @param {string} text2 Second string.
     * @return {number} The number of characters common to the end of the first
     *     string and the start of the second string.
     * @private
     */
    DiffMatchPatch.prototype.diffCommonOverlap = function(text1, text2) {
        var text1Length, text2Length, textLength,
			best, length, pattern, found;
        // Cache the text lengths to prevent multiple calls.
        text1Length = text1.length;
        text2Length = text2.length;
        // Eliminate the null case.
        if (text1Length === 0 || text2Length === 0) {
            return 0;
        }
        // Truncate the longer string.
        if (text1Length > text2Length) {
            text1 = text1.substring(text1Length - text2Length);
        } else if (text1Length < text2Length) {
            text2 = text2.substring(0, text1Length);
        }
        textLength = Math.min(text1Length, text2Length);
        // Quick check for the worst case.
        if (text1 === text2) {
            return textLength;
        }

        // Start by looking for a single character match
        // and increase length until no match is found.
        // Performance analysis: http://neil.fraser.name/news/2010/11/04/
        best = 0;
        length = 1;
        while (true) {
            pattern = text1.substring(textLength - length);
            found = text2.indexOf(pattern);
            if (found === -1) {
                return best;
            }
            length += found;
            if (found === 0 || text1.substring(textLength - length) ===
                text2.substring(0, length)) {
                best = length;
                length++;
            }
        }
    };

    /**
     * Split two texts into an array of strings.  Reduce the texts to a string of
     * hashes where each Unicode character represents one line.
     * @param {string} text1 First string.
     * @param {string} text2 Second string.
     * @return {{chars1: string, chars2: string, lineArray: !Array.<string>}}
     *     An object containing the encoded text1, the encoded text2 and
     *     the array of unique strings.
     *     The zeroth element of the array of unique strings is intentionally blank.
     * @private
     */
    DiffMatchPatch.prototype.diffLinesToChars = function(text1, text2) {
        var lineArray, lineHash, chars1, chars2;
        lineArray = []; // e.g. lineArray[4] === 'Hello\n'
        lineHash = {}; // e.g. lineHash['Hello\n'] === 4

        // '\x00' is a valid character, but various debuggers don't like it.
        // So we'll insert a junk entry to avoid generating a null character.
        lineArray[0] = "";

        /**
         * Split a text into an array of strings.  Reduce the texts to a string of
         * hashes where each Unicode character represents one line.
         * Modifies linearray and linehash through being a closure.
         * @param {string} text String to encode.
         * @return {string} Encoded string.
         * @private
         */
        function diffLinesToCharsMunge(text) {
            var chars, lineStart, lineEnd, lineArrayLength, line;
            chars = "";
            // Walk the text, pulling out a substring for each line.
            // text.split('\n') would would temporarily double our memory footprint.
            // Modifying text would create many large strings to garbage collect.
            lineStart = 0;
            lineEnd = -1;
            // Keeping our own length variable is faster than looking it up.
            lineArrayLength = lineArray.length;
            while (lineEnd < text.length - 1) {
                lineEnd = text.indexOf("\n", lineStart);
                if (lineEnd === -1) {
                    lineEnd = text.length - 1;
                }
                line = text.substring(lineStart, lineEnd + 1);
                lineStart = lineEnd + 1;

                if (lineHash.hasOwnProperty ? lineHash.hasOwnProperty(line) :
                    (lineHash[line] !== undefined)) {
                    chars += String.fromCharCode( lineHash[ line ] );
                } else {
                    chars += String.fromCharCode(lineArrayLength);
                    lineHash[line] = lineArrayLength;
                    lineArray[lineArrayLength++] = line;
                }
            }
            return chars;
        }

        chars1 = diffLinesToCharsMunge(text1);
        chars2 = diffLinesToCharsMunge(text2);
        return {
            chars1: chars1,
            chars2: chars2,
            lineArray: lineArray
        };
    };

    /**
     * Rehydrate the text in a diff from a string of line hashes to real lines of
     * text.
     * @param {!Array.<!DiffMatchPatch.Diff>} diffs Array of diff tuples.
     * @param {!Array.<string>} lineArray Array of unique strings.
     * @private
     */
    DiffMatchPatch.prototype.diffCharsToLines = function( diffs, lineArray ) {
        var x, chars, text, y;
        for ( x = 0; x < diffs.length; x++ ) {
            chars = diffs[x][1];
            text = [];
            for ( y = 0; y < chars.length; y++ ) {
                text[y] = lineArray[chars.charCodeAt(y)];
            }
            diffs[x][1] = text.join("");
        }
    };

    /**
     * Reorder and merge like edit sections.  Merge equalities.
     * Any edit section can move as long as it doesn't cross an equality.
     * @param {!Array.<!DiffMatchPatch.Diff>} diffs Array of diff tuples.
     */
    DiffMatchPatch.prototype.diffCleanupMerge = function(diffs) {
        var pointer, countDelete, countInsert, textInsert, textDelete,
			commonlength, changes;
        diffs.push( [ DIFF_EQUAL, "" ] ); // Add a dummy entry at the end.
        pointer = 0;
        countDelete = 0;
        countInsert = 0;
        textDelete = "";
        textInsert = "";
        commonlength;
        while (pointer < diffs.length) {
            switch ( diffs[ pointer ][ 0 ] ) {
                case DIFF_INSERT:
                    countInsert++;
                    textInsert += diffs[pointer][1];
                    pointer++;
                    break;
                case DIFF_DELETE:
                    countDelete++;
                    textDelete += diffs[pointer][1];
                    pointer++;
                    break;
                case DIFF_EQUAL:
                    // Upon reaching an equality, check for prior redundancies.
                    if (countDelete + countInsert > 1) {
                        if (countDelete !== 0 && countInsert !== 0) {
                            // Factor out any common prefixies.
                            commonlength = this.diffCommonPrefix(textInsert, textDelete);
                            if (commonlength !== 0) {
                                if ((pointer - countDelete - countInsert) > 0 &&
                                    diffs[pointer - countDelete - countInsert - 1][0] ===
                                    DIFF_EQUAL) {
                                    diffs[pointer - countDelete - countInsert - 1][1] +=
                                        textInsert.substring(0, commonlength);
                                } else {
                                    diffs.splice( 0, 0, [ DIFF_EQUAL,
                                        textInsert.substring( 0, commonlength )
                                     ] );
                                    pointer++;
                                }
                                textInsert = textInsert.substring(commonlength);
                                textDelete = textDelete.substring(commonlength);
                            }
                            // Factor out any common suffixies.
                            commonlength = this.diffCommonSuffix(textInsert, textDelete);
                            if (commonlength !== 0) {
                                diffs[pointer][1] = textInsert.substring(textInsert.length -
                                    commonlength) + diffs[pointer][1];
                                textInsert = textInsert.substring(0, textInsert.length -
                                    commonlength);
                                textDelete = textDelete.substring(0, textDelete.length -
                                    commonlength);
                            }
                        }
                        // Delete the offending records and add the merged ones.
                        if (countDelete === 0) {
                            diffs.splice( pointer - countInsert,
                                countDelete + countInsert, [ DIFF_INSERT, textInsert ] );
                        } else if (countInsert === 0) {
                            diffs.splice( pointer - countDelete,
                                countDelete + countInsert, [ DIFF_DELETE, textDelete ] );
                        } else {
                            diffs.splice( pointer - countDelete - countInsert,
                                countDelete + countInsert, [ DIFF_DELETE, textDelete ], [ DIFF_INSERT, textInsert ] );
                        }
                        pointer = pointer - countDelete - countInsert +
                            (countDelete ? 1 : 0) + (countInsert ? 1 : 0) + 1;
                    } else if (pointer !== 0 && diffs[pointer - 1][0] === DIFF_EQUAL) {
                        // Merge this equality with the previous one.
                        diffs[pointer - 1][1] += diffs[pointer][1];
                        diffs.splice(pointer, 1);
                    } else {
                        pointer++;
                    }
                    countInsert = 0;
                    countDelete = 0;
                    textDelete = "";
                    textInsert = "";
                    break;
            }
        }
        if (diffs[diffs.length - 1][1] === "") {
            diffs.pop(); // Remove the dummy entry at the end.
        }

        // Second pass: look for single edits surrounded on both sides by equalities
        // which can be shifted sideways to eliminate an equality.
        // e.g: A<ins>BA</ins>C -> <ins>AB</ins>AC
        changes = false;
        pointer = 1;
        // Intentionally ignore the first and last element (don't need checking).
        while (pointer < diffs.length - 1) {
            if (diffs[pointer - 1][0] === DIFF_EQUAL &&
                diffs[pointer + 1][0] === DIFF_EQUAL) {
                // This is a single edit surrounded by equalities.
                if ( diffs[ pointer ][ 1 ].substring( diffs[ pointer ][ 1 ].length -
                        diffs[ pointer - 1 ][ 1 ].length ) === diffs[ pointer - 1 ][ 1 ] ) {
                    // Shift the edit over the previous equality.
                    diffs[pointer][1] = diffs[pointer - 1][1] +
                        diffs[pointer][1].substring(0, diffs[pointer][1].length -
                            diffs[pointer - 1][1].length);
                    diffs[pointer + 1][1] = diffs[pointer - 1][1] + diffs[pointer + 1][1];
                    diffs.splice(pointer - 1, 1);
                    changes = true;
                } else if ( diffs[ pointer ][ 1 ].substring( 0, diffs[ pointer + 1 ][ 1 ].length ) ===
                    diffs[ pointer + 1 ][ 1 ] ) {
                    // Shift the edit over the next equality.
                    diffs[pointer - 1][1] += diffs[pointer + 1][1];
                    diffs[pointer][1] =
                        diffs[pointer][1].substring(diffs[pointer + 1][1].length) +
                        diffs[pointer + 1][1];
                    diffs.splice(pointer + 1, 1);
                    changes = true;
                }
            }
            pointer++;
        }
        // If shifts were made, the diff needs reordering and another shift sweep.
        if (changes) {
            this.diffCleanupMerge(diffs);
        }
    };

    return function(o, n) {
		var diff, output, text;
        diff = new DiffMatchPatch();
        output = diff.DiffMain(o, n);
        //console.log(output);
        diff.diffCleanupEfficiency(output);
        text = diff.diffPrettyHtml(output);

        return text;
    };
}());
// jscs:enable

(function() {

// Deprecated QUnit.init - Ref #530
// Re-initialize the configuration options
QUnit.init = function() {
	var tests, banner, result, qunit,
		config = QUnit.config;

	config.stats = { all: 0, bad: 0 };
	config.moduleStats = { all: 0, bad: 0 };
	config.started = 0;
	config.updateRate = 1000;
	config.blocking = false;
	config.autostart = true;
	config.autorun = false;
	config.filter = "";
	config.queue = [];

	// Return on non-browser environments
	// This is necessary to not break on node tests
	if ( typeof window === "undefined" ) {
		return;
	}

	qunit = id( "qunit" );
	if ( qunit ) {
		qunit.innerHTML =
			"<h1 id='qunit-header'>" + escapeText( document.title ) + "</h1>" +
			"<h2 id='qunit-banner'></h2>" +
			"<div id='qunit-testrunner-toolbar'></div>" +
			"<h2 id='qunit-userAgent'></h2>" +
			"<ol id='qunit-tests'></ol>";
	}

	tests = id( "qunit-tests" );
	banner = id( "qunit-banner" );
	result = id( "qunit-testresult" );

	if ( tests ) {
		tests.innerHTML = "";
	}

	if ( banner ) {
		banner.className = "";
	}

	if ( result ) {
		result.parentNode.removeChild( result );
	}

	if ( tests ) {
		result = document.createElement( "p" );
		result.id = "qunit-testresult";
		result.className = "result";
		tests.parentNode.insertBefore( result, tests );
		result.innerHTML = "Running...<br />&#160;";
	}
};

// Don't load the HTML Reporter on non-Browser environments
if ( typeof window === "undefined" ) {
	return;
}

var config = QUnit.config,
	hasOwn = Object.prototype.hasOwnProperty,
	defined = {
		document: window.document !== undefined,
		sessionStorage: (function() {
			var x = "qunit-test-string";
			try {
				sessionStorage.setItem( x, x );
				sessionStorage.removeItem( x );
				return true;
			} catch ( e ) {
				return false;
			}
		}())
	},
	modulesList = [];

/**
* Escape text for attribute or text content.
*/
function escapeText( s ) {
	if ( !s ) {
		return "";
	}
	s = s + "";

	// Both single quotes and double quotes (for attributes)
	return s.replace( /['"<>&]/g, function( s ) {
		switch ( s ) {
		case "'":
			return "&#039;";
		case "\"":
			return "&quot;";
		case "<":
			return "&lt;";
		case ">":
			return "&gt;";
		case "&":
			return "&amp;";
		}
	});
}

/**
 * @param {HTMLElement} elem
 * @param {string} type
 * @param {Function} fn
 */
function addEvent( elem, type, fn ) {
	if ( elem.addEventListener ) {

		// Standards-based browsers
		elem.addEventListener( type, fn, false );
	} else if ( elem.attachEvent ) {

		// support: IE <9
		elem.attachEvent( "on" + type, function() {
			var event = window.event;
			if ( !event.target ) {
				event.target = event.srcElement || document;
			}

			fn.call( elem, event );
		});
	}
}

/**
 * @param {Array|NodeList} elems
 * @param {string} type
 * @param {Function} fn
 */
function addEvents( elems, type, fn ) {
	var i = elems.length;
	while ( i-- ) {
		addEvent( elems[ i ], type, fn );
	}
}

function hasClass( elem, name ) {
	return ( " " + elem.className + " " ).indexOf( " " + name + " " ) >= 0;
}

function addClass( elem, name ) {
	if ( !hasClass( elem, name ) ) {
		elem.className += ( elem.className ? " " : "" ) + name;
	}
}

function toggleClass( elem, name ) {
	if ( hasClass( elem, name ) ) {
		removeClass( elem, name );
	} else {
		addClass( elem, name );
	}
}

function removeClass( elem, name ) {
	var set = " " + elem.className + " ";

	// Class name may appear multiple times
	while ( set.indexOf( " " + name + " " ) >= 0 ) {
		set = set.replace( " " + name + " ", " " );
	}

	// trim for prettiness
	elem.className = typeof set.trim === "function" ? set.trim() : set.replace( /^\s+|\s+$/g, "" );
}

function id( name ) {
	return defined.document && document.getElementById && document.getElementById( name );
}

function getUrlConfigHtml() {
	var i, j, val,
		escaped, escapedTooltip,
		selection = false,
		len = config.urlConfig.length,
		urlConfigHtml = "";

	for ( i = 0; i < len; i++ ) {
		val = config.urlConfig[ i ];
		if ( typeof val === "string" ) {
			val = {
				id: val,
				label: val
			};
		}

		escaped = escapeText( val.id );
		escapedTooltip = escapeText( val.tooltip );

		if ( config[ val.id ] === undefined ) {
			config[ val.id ] = QUnit.urlParams[ val.id ];
		}

		if ( !val.value || typeof val.value === "string" ) {
			urlConfigHtml += "<input id='qunit-urlconfig-" + escaped +
				"' name='" + escaped + "' type='checkbox'" +
				( val.value ? " value='" + escapeText( val.value ) + "'" : "" ) +
				( config[ val.id ] ? " checked='checked'" : "" ) +
				" title='" + escapedTooltip + "' /><label for='qunit-urlconfig-" + escaped +
				"' title='" + escapedTooltip + "'>" + val.label + "</label>";
		} else {
			urlConfigHtml += "<label for='qunit-urlconfig-" + escaped +
				"' title='" + escapedTooltip + "'>" + val.label +
				": </label><select id='qunit-urlconfig-" + escaped +
				"' name='" + escaped + "' title='" + escapedTooltip + "'><option></option>";

			if ( QUnit.is( "array", val.value ) ) {
				for ( j = 0; j < val.value.length; j++ ) {
					escaped = escapeText( val.value[ j ] );
					urlConfigHtml += "<option value='" + escaped + "'" +
						( config[ val.id ] === val.value[ j ] ?
							( selection = true ) && " selected='selected'" : "" ) +
						">" + escaped + "</option>";
				}
			} else {
				for ( j in val.value ) {
					if ( hasOwn.call( val.value, j ) ) {
						urlConfigHtml += "<option value='" + escapeText( j ) + "'" +
							( config[ val.id ] === j ?
								( selection = true ) && " selected='selected'" : "" ) +
							">" + escapeText( val.value[ j ] ) + "</option>";
					}
				}
			}
			if ( config[ val.id ] && !selection ) {
				escaped = escapeText( config[ val.id ] );
				urlConfigHtml += "<option value='" + escaped +
					"' selected='selected' disabled='disabled'>" + escaped + "</option>";
			}
			urlConfigHtml += "</select>";
		}
	}

	return urlConfigHtml;
}

// Handle "click" events on toolbar checkboxes and "change" for select menus.
// Updates the URL with the new state of `config.urlConfig` values.
function toolbarChanged() {
	var updatedUrl, value,
		field = this,
		params = {};

	// Detect if field is a select menu or a checkbox
	if ( "selectedIndex" in field ) {
		value = field.options[ field.selectedIndex ].value || undefined;
	} else {
		value = field.checked ? ( field.defaultValue || true ) : undefined;
	}

	params[ field.name ] = value;
	updatedUrl = setUrl( params );

	if ( "hidepassed" === field.name && "replaceState" in window.history ) {
		config[ field.name ] = value || false;
		if ( value ) {
			addClass( id( "qunit-tests" ), "hidepass" );
		} else {
			removeClass( id( "qunit-tests" ), "hidepass" );
		}

		// It is not necessary to refresh the whole page
		window.history.replaceState( null, "", updatedUrl );
	} else {
		window.location = updatedUrl;
	}
}

function setUrl( params ) {
	var key,
		querystring = "?";

	params = QUnit.extend( QUnit.extend( {}, QUnit.urlParams ), params );

	for ( key in params ) {
		if ( hasOwn.call( params, key ) ) {
			if ( params[ key ] === undefined ) {
				continue;
			}
			querystring += encodeURIComponent( key );
			if ( params[ key ] !== true ) {
				querystring += "=" + encodeURIComponent( params[ key ] );
			}
			querystring += "&";
		}
	}
	return location.protocol + "//" + location.host +
		location.pathname + querystring.slice( 0, -1 );
}

function applyUrlParams() {
	var selectedModule,
		modulesList = id( "qunit-modulefilter" ),
		filter = id( "qunit-filter-input" ).value;

	selectedModule = modulesList ?
		decodeURIComponent( modulesList.options[ modulesList.selectedIndex ].value ) :
		undefined;

	window.location = setUrl({
		module: ( selectedModule === "" ) ? undefined : selectedModule,
		filter: ( filter === "" ) ? undefined : filter,

		// Remove testId filter
		testId: undefined
	});
}

function toolbarUrlConfigContainer() {
	var urlConfigContainer = document.createElement( "span" );

	urlConfigContainer.innerHTML = getUrlConfigHtml();
	addClass( urlConfigContainer, "qunit-url-config" );

	// For oldIE support:
	// * Add handlers to the individual elements instead of the container
	// * Use "click" instead of "change" for checkboxes
	addEvents( urlConfigContainer.getElementsByTagName( "input" ), "click", toolbarChanged );
	addEvents( urlConfigContainer.getElementsByTagName( "select" ), "change", toolbarChanged );

	return urlConfigContainer;
}

function toolbarLooseFilter() {
	var filter = document.createElement( "form" ),
		label = document.createElement( "label" ),
		input = document.createElement( "input" ),
		button = document.createElement( "button" );

	addClass( filter, "qunit-filter" );

	label.innerHTML = "Filter: ";

	input.type = "text";
	input.value = config.filter || "";
	input.name = "filter";
	input.id = "qunit-filter-input";

	button.innerHTML = "Go";

	label.appendChild( input );

	filter.appendChild( label );
	filter.appendChild( button );
	addEvent( filter, "submit", function( ev ) {
		applyUrlParams();

		if ( ev && ev.preventDefault ) {
			ev.preventDefault();
		}

		return false;
	});

	return filter;
}

function toolbarModuleFilterHtml() {
	var i,
		moduleFilterHtml = "";

	if ( !modulesList.length ) {
		return false;
	}

	modulesList.sort(function( a, b ) {
		return a.localeCompare( b );
	});

	moduleFilterHtml += "<label for='qunit-modulefilter'>Module: </label>" +
		"<select id='qunit-modulefilter' name='modulefilter'><option value='' " +
		( QUnit.urlParams.module === undefined ? "selected='selected'" : "" ) +
		">< All Modules ></option>";

	for ( i = 0; i < modulesList.length; i++ ) {
		moduleFilterHtml += "<option value='" +
			escapeText( encodeURIComponent( modulesList[ i ] ) ) + "' " +
			( QUnit.urlParams.module === modulesList[ i ] ? "selected='selected'" : "" ) +
			">" + escapeText( modulesList[ i ] ) + "</option>";
	}
	moduleFilterHtml += "</select>";

	return moduleFilterHtml;
}

function toolbarModuleFilter() {
	var toolbar = id( "qunit-testrunner-toolbar" ),
		moduleFilter = document.createElement( "span" ),
		moduleFilterHtml = toolbarModuleFilterHtml();

	if ( !toolbar || !moduleFilterHtml ) {
		return false;
	}

	moduleFilter.setAttribute( "id", "qunit-modulefilter-container" );
	moduleFilter.innerHTML = moduleFilterHtml;

	addEvent( moduleFilter.lastChild, "change", applyUrlParams );

	toolbar.appendChild( moduleFilter );
}

function appendToolbar() {
	var toolbar = id( "qunit-testrunner-toolbar" );

	if ( toolbar ) {
		toolbar.appendChild( toolbarUrlConfigContainer() );
		toolbar.appendChild( toolbarLooseFilter() );
	}
}

function appendHeader() {
	var header = id( "qunit-header" );

	if ( header ) {
		header.innerHTML = "<a href='" +
			setUrl({ filter: undefined, module: undefined, testId: undefined }) +
			"'>" + header.innerHTML + "</a> ";
	}
}

function appendBanner() {
	var banner = id( "qunit-banner" );

	if ( banner ) {
		banner.className = "";
	}
}

function appendTestResults() {
	var tests = id( "qunit-tests" ),
		result = id( "qunit-testresult" );

	if ( result ) {
		result.parentNode.removeChild( result );
	}

	if ( tests ) {
		tests.innerHTML = "";
		result = document.createElement( "p" );
		result.id = "qunit-testresult";
		result.className = "result";
		tests.parentNode.insertBefore( result, tests );
		result.innerHTML = "Running...<br />&#160;";
	}
}

function storeFixture() {
	var fixture = id( "qunit-fixture" );
	if ( fixture ) {
		config.fixture = fixture.innerHTML;
	}
}

function appendUserAgent() {
	var userAgent = id( "qunit-userAgent" );

	if ( userAgent ) {
		userAgent.innerHTML = "";
		userAgent.appendChild(
			document.createTextNode(
				"QUnit " + QUnit.version  + "; " + navigator.userAgent
			)
		);
	}
}

function appendTestsList( modules ) {
	var i, l, x, z, test, moduleObj;

	for ( i = 0, l = modules.length; i < l; i++ ) {
		moduleObj = modules[ i ];

		if ( moduleObj.name ) {
			modulesList.push( moduleObj.name );
		}

		for ( x = 0, z = moduleObj.tests.length; x < z; x++ ) {
			test = moduleObj.tests[ x ];

			appendTest( test.name, test.testId, moduleObj.name );
		}
	}
}

function appendTest( name, testId, moduleName ) {
	var title, rerunTrigger, testBlock, assertList,
		tests = id( "qunit-tests" );

	if ( !tests ) {
		return;
	}

	title = document.createElement( "strong" );
	title.innerHTML = getNameHtml( name, moduleName );

	rerunTrigger = document.createElement( "a" );
	rerunTrigger.innerHTML = "Rerun";
	rerunTrigger.href = setUrl({ testId: testId });

	testBlock = document.createElement( "li" );
	testBlock.appendChild( title );
	testBlock.appendChild( rerunTrigger );
	testBlock.id = "qunit-test-output-" + testId;

	assertList = document.createElement( "ol" );
	assertList.className = "qunit-assert-list";

	testBlock.appendChild( assertList );

	tests.appendChild( testBlock );
}

// HTML Reporter initialization and load
QUnit.begin(function( details ) {
	var qunit = id( "qunit" );

	// Fixture is the only one necessary to run without the #qunit element
	storeFixture();

	if ( qunit ) {
		qunit.innerHTML =
			"<h1 id='qunit-header'>" + escapeText( document.title ) + "</h1>" +
			"<h2 id='qunit-banner'></h2>" +
			"<div id='qunit-testrunner-toolbar'></div>" +
			"<h2 id='qunit-userAgent'></h2>" +
			"<ol id='qunit-tests'></ol>";
	}

	appendHeader();
	appendBanner();
	appendTestResults();
	appendUserAgent();
	appendToolbar();
	appendTestsList( details.modules );
	toolbarModuleFilter();

	if ( qunit && config.hidepassed ) {
		addClass( qunit.lastChild, "hidepass" );
	}
});

QUnit.done(function( details ) {
	var i, key,
		banner = id( "qunit-banner" ),
		tests = id( "qunit-tests" ),
		html = [
			"Tests completed in ",
			details.runtime,
			" milliseconds.<br />",
			"<span class='passed'>",
			details.passed,
			"</span> assertions of <span class='total'>",
			details.total,
			"</span> passed, <span class='failed'>",
			details.failed,
			"</span> failed."
		].join( "" );

	if ( banner ) {
		banner.className = details.failed ? "qunit-fail" : "qunit-pass";
	}

	if ( tests ) {
		id( "qunit-testresult" ).innerHTML = html;
	}

	if ( config.altertitle && defined.document && document.title ) {

		// show ✖ for good, ✔ for bad suite result in title
		// use escape sequences in case file gets loaded with non-utf-8-charset
		document.title = [
			( details.failed ? "\u2716" : "\u2714" ),
			document.title.replace( /^[\u2714\u2716] /i, "" )
		].join( " " );
	}

	// clear own sessionStorage items if all tests passed
	if ( config.reorder && defined.sessionStorage && details.failed === 0 ) {
		for ( i = 0; i < sessionStorage.length; i++ ) {
			key = sessionStorage.key( i++ );
			if ( key.indexOf( "qunit-test-" ) === 0 ) {
				sessionStorage.removeItem( key );
			}
		}
	}

	// scroll back to top to show results
	if ( config.scrolltop && window.scrollTo ) {
		window.scrollTo( 0, 0 );
	}
});

function getNameHtml( name, module ) {
	var nameHtml = "";

	if ( module ) {
		nameHtml = "<span class='module-name'>" + escapeText( module ) + "</span>: ";
	}

	nameHtml += "<span class='test-name'>" + escapeText( name ) + "</span>";

	return nameHtml;
}

QUnit.testStart(function( details ) {
	var running, testBlock, bad;

	testBlock = id( "qunit-test-output-" + details.testId );
	if ( testBlock ) {
		testBlock.className = "running";
	} else {

		// Report later registered tests
		appendTest( details.name, details.testId, details.module );
	}

	running = id( "qunit-testresult" );
	if ( running ) {
		bad = QUnit.config.reorder && defined.sessionStorage &&
			+sessionStorage.getItem( "qunit-test-" + details.module + "-" + details.name );

		running.innerHTML = ( bad ?
			"Rerunning previously failed test: <br />" :
			"Running: <br />" ) +
			getNameHtml( details.name, details.module );
	}

});

QUnit.log(function( details ) {
	var assertList, assertLi,
		message, expected, actual,
		testItem = id( "qunit-test-output-" + details.testId );

	if ( !testItem ) {
		return;
	}

	message = escapeText( details.message ) || ( details.result ? "okay" : "failed" );
	message = "<span class='test-message'>" + message + "</span>";
	message += "<span class='runtime'>@ " + details.runtime + " ms</span>";

	// pushFailure doesn't provide details.expected
	// when it calls, it's implicit to also not show expected and diff stuff
	// Also, we need to check details.expected existence, as it can exist and be undefined
	if ( !details.result && hasOwn.call( details, "expected" ) ) {
		expected = escapeText( QUnit.dump.parse( details.expected ) );
		actual = escapeText( QUnit.dump.parse( details.actual ) );
		message += "<table><tr class='test-expected'><th>Expected: </th><td><pre>" +
			expected +
			"</pre></td></tr>";

		if ( actual !== expected ) {
			message += "<tr class='test-actual'><th>Result: </th><td><pre>" +
				actual + "</pre></td></tr>" +
				"<tr class='test-diff'><th>Diff: </th><td><pre>" +
				QUnit.diff( expected, actual ) + "</pre></td></tr>";
		} else {
			if ( expected.indexOf( "[object Array]" ) !== -1 ||
					expected.indexOf( "[object Object]" ) !== -1 ) {
				message += "<tr class='test-message'><th>Message: </th><td>" +
					"Diff suppressed as the depth of object is more than current max depth (" +
					QUnit.config.maxDepth + ").<p>Hint: Use <code>QUnit.dump.maxDepth</code> to " +
					" run with a higher max depth or <a href='" + setUrl({ maxDepth: -1 }) + "'>" +
					"Rerun</a> without max depth.</p></td></tr>";
			}
		}

		if ( details.source ) {
			message += "<tr class='test-source'><th>Source: </th><td><pre>" +
				escapeText( details.source ) + "</pre></td></tr>";
		}

		message += "</table>";

	// this occours when pushFailure is set and we have an extracted stack trace
	} else if ( !details.result && details.source ) {
		message += "<table>" +
			"<tr class='test-source'><th>Source: </th><td><pre>" +
			escapeText( details.source ) + "</pre></td></tr>" +
			"</table>";
	}

	assertList = testItem.getElementsByTagName( "ol" )[ 0 ];

	assertLi = document.createElement( "li" );
	assertLi.className = details.result ? "pass" : "fail";
	assertLi.innerHTML = message;
	assertList.appendChild( assertLi );
});

QUnit.testDone(function( details ) {
	var testTitle, time, testItem, assertList,
		good, bad, testCounts, skipped,
		tests = id( "qunit-tests" );

	if ( !tests ) {
		return;
	}

	testItem = id( "qunit-test-output-" + details.testId );

	assertList = testItem.getElementsByTagName( "ol" )[ 0 ];

	good = details.passed;
	bad = details.failed;

	// store result when possible
	if ( config.reorder && defined.sessionStorage ) {
		if ( bad ) {
			sessionStorage.setItem( "qunit-test-" + details.module + "-" + details.name, bad );
		} else {
			sessionStorage.removeItem( "qunit-test-" + details.module + "-" + details.name );
		}
	}

	if ( bad === 0 ) {
		addClass( assertList, "qunit-collapsed" );
	}

	// testItem.firstChild is the test name
	testTitle = testItem.firstChild;

	testCounts = bad ?
		"<b class='failed'>" + bad + "</b>, " + "<b class='passed'>" + good + "</b>, " :
		"";

	testTitle.innerHTML += " <b class='counts'>(" + testCounts +
		details.assertions.length + ")</b>";

	if ( details.skipped ) {
		testItem.className = "skipped";
		skipped = document.createElement( "em" );
		skipped.className = "qunit-skipped-label";
		skipped.innerHTML = "skipped";
		testItem.insertBefore( skipped, testTitle );
	} else {
		addEvent( testTitle, "click", function() {
			toggleClass( assertList, "qunit-collapsed" );
		});

		testItem.className = bad ? "fail" : "pass";

		time = document.createElement( "span" );
		time.className = "runtime";
		time.innerHTML = details.runtime + " ms";
		testItem.insertBefore( time, assertList );
	}
});

if ( defined.document ) {
	if ( document.readyState === "complete" ) {
		QUnit.load();
	} else {
		addEvent( window, "load", QUnit.load );
	}
} else {
	config.pageLoaded = true;
	config.autorun = true;
}

})();

QUnit.notifications = function(options) {
  "use strict";

  options         = options         || {};
  options.icons   = options.icons   || {};
  options.timeout = options.timeout || 4000;
  options.titles  = options.titles  || { passed: "Passed!", failed: "Failed!" };
  options.bodies  = options.bodies  || {
    passed: "{{passed}} of {{total}} passed",
    failed: "{{passed}} passed. {{failed}} failed."
  };

  var renderBody = function(body, details) {
    [ "passed", "failed", "total", "runtime" ].forEach(function(type) {
      body = body.replace("{{" + type + "}}", details[ type ]);
    });

    return body;
  };

  function generateQueryString(params) {
    var key,
      querystring = "?";

    params = QUnit.extend(QUnit.extend({}, QUnit.urlParams), params);

    for (key in params) {
      if (params.hasOwnProperty(key)) {
        if (params[ key ] === undefined) {
          continue;
        }
        querystring += encodeURIComponent(key);
        if (params[ key ] !== true) {
          querystring += "=" + encodeURIComponent(params[ key ]);
        }
        querystring += "&";
      }
    }
    return location.protocol + "//" + location.host +
      location.pathname + querystring.slice(0, -1);
  }

  if (window.Notification) {
    QUnit.done(function(details) {
      var title,
          _options = {},
          notification;

      if (window.Notification && QUnit.urlParams.notifications) {
        if (details.failed === 0) {
          title = options.titles.passed;
          _options.body = renderBody(options.bodies.passed, details);

          if (options.icons.passed) {
            _options.icon = options.icons.passed;
          }
        } else {
          title = options.titles.failed;
          _options.body = renderBody(options.bodies.failed, details);

          if (options.icons.failed) {
            _options.icon = options.icons.failed;
          }
        }

        notification = new window.Notification(title, _options);

        setTimeout(function() {
          notification.close();
        }, options.timeout);
      }
    });

    QUnit.begin(function() {
      var toolbar      = document.getElementById( "qunit-testrunner-toolbar" ),
          notification = document.createElement( "input" ),
          label        = document.createElement("label");

      notification.type = "checkbox";
      notification.id   = "qunit-notifications";

      if (QUnit.urlParams.notifications) {
        notification.checked = true;
      }

      notification.addEventListener("click", function(event) {
        if (event.target.checked) {
          window.Notification.requestPermission(function() {
            window.location = generateQueryString({ notifications: true });
          });
        } else {
          window.location = generateQueryString({ notifications: undefined });
        }
      }, false);
      toolbar.appendChild(notification);

      label.innerHTML = "Notifications";
      label.setAttribute( "for", "qunit-notifications" );
      label.setAttribute( "title", "Show notifications." );
      toolbar.appendChild(label);
    });
  }
};

/* globals jQuery,QUnit */

QUnit.config.urlConfig.push({ id: 'nocontainer', label: 'Hide container'});
QUnit.config.urlConfig.push({ id: 'nojshint', label: 'Disable JSHint'});
QUnit.config.urlConfig.push({ id: 'dockcontainer', label: 'Dock container'});
QUnit.config.testTimeout = 60000; //Default Test Timeout 60 Seconds

if (QUnit.notifications) {
  QUnit.notifications({
    icons: {
      passed: '/assets/passed.png',
      failed: '/assets/failed.png'
    }
  });
}

jQuery(document).ready(function() {
  var containerVisibility = QUnit.urlParams.nocontainer ? 'hidden' : 'visible';
  var containerPosition = QUnit.urlParams.dockcontainer ? 'absolute' : 'relative';
  document.getElementById('ember-testing-container').style.visibility = containerVisibility;
  document.getElementById('ember-testing-container').style.position = containerPosition;
});

/* globals jQuery,QUnit */

jQuery(document).ready(function() {
  var TestLoader = require('ember-cli/test-loader')['default'];
  TestLoader.prototype.shouldLoadModule = function(moduleName) {
    return moduleName.match(/\/.*[-_]test$/) || (!QUnit.urlParams.nojshint && moduleName.match(/\.jshint$/));
  };

  TestLoader.prototype.moduleLoadFailure = function(moduleName, error) {
    QUnit.module('TestLoader Failures');
    QUnit.test(moduleName + ': could not be loaded', function() {
      throw error;
    });
  };

  var autostart = QUnit.config.autostart !== false;
  QUnit.config.autostart = false;

  setTimeout(function() {
    TestLoader.load();

    if (autostart) {
      QUnit.start();
    }
  }, 250);
});

/* jshint ignore:start */

runningTests = true;



/* jshint ignore:end */
//# sourceMappingURL=test-support.map