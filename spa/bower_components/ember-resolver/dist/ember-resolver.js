// ==========================================================================
// Project:   Ember - JavaScript Application Framework
// Copyright: Copyright 2013 Stefan Penner and Ember App Kit Contributors
// License:   Licensed under MIT license
//            See https://raw.github.com/ember-cli/ember-resolver/master/LICENSE
// ==========================================================================


 // Version: 0.1.17

(function() {
/*globals define registry requirejs */

define("ember/resolver",
  [],
  function() {
    "use strict";

    if (typeof requirejs.entries === 'undefined') {
      requirejs.entries = requirejs._eak_seen;
    }

  /*
   * This module defines a subclass of Ember.DefaultResolver that adds two
   * important features:
   *
   *  1) The resolver makes the container aware of es6 modules via the AMD
   *     output. The loader's _moduleEntries is consulted so that classes can be
   *     resolved directly via the module loader, without needing a manual
   *     `import`.
   *  2) is able to provide injections to classes that implement `extend`
   *     (as is typical with Ember).
   */

  function classFactory(klass) {
    return {
      create: function (injections) {
        if (typeof klass.extend === 'function') {
          return klass.extend(injections);
        } else {
          return klass;
        }
      }
    };
  }

  var create = (Object.create || Ember.create);
  if (!(create && !create(null).hasOwnProperty)) {
    throw new Error("This browser does not support Object.create(null), please polyfil with es5-sham: http://git.io/yBU2rg");
  }

  function makeDictionary() {
    var cache = create(null);
    cache['_dict'] = null;
    delete cache['_dict'];
    return cache;
  }

  var underscore = Ember.String.underscore;
  var classify = Ember.String.classify;
  var get = Ember.get;

  function parseName(fullName) {
    /*jshint validthis:true */

    if (fullName.parsedName === true) { return fullName; }

    var prefixParts = fullName.split('@');
    var prefix;

    if (prefixParts.length === 2) {
      if (prefixParts[0].split(':')[0] === 'view') {
        prefixParts[0] = prefixParts[0].split(':')[1];
        prefixParts[1] = 'view:' + prefixParts[1];
      }

      prefix = prefixParts[0];
    }

    var nameParts = prefixParts[prefixParts.length - 1].split(":");
    var type = nameParts[0], fullNameWithoutType = nameParts[1];
    var name = fullNameWithoutType;
    var namespace = get(this, 'namespace');
    var root = namespace;

    return {
      parsedName: true,
      fullName: fullName,
      prefix: prefix || this.prefix({type: type}),
      type: type,
      fullNameWithoutType: fullNameWithoutType,
      name: name,
      root: root,
      resolveMethodName: "resolve" + classify(type)
    };
  }

  function resolveOther(parsedName) {
    /*jshint validthis:true */

    // Temporarily disabling podModulePrefix deprecation
    /*
    if (!this._deprecatedPodModulePrefix) {
      var podModulePrefix = this.namespace.podModulePrefix || '';
      var podPath = podModulePrefix.substr(podModulePrefix.lastIndexOf('/') + 1);

      Ember.deprecate('`podModulePrefix` is deprecated and will be removed '+
        'from future versions of ember-cli. Please move existing pods from '+
        '\'app/' + podPath + '/\' to \'app/\'.', !this.namespace.podModulePrefix);

      this._deprecatedPodModulePrefix = true;
    }
    */
    Ember.assert('`modulePrefix` must be defined', this.namespace.modulePrefix);

    var normalizedModuleName = this.findModuleName(parsedName);

    if (normalizedModuleName) {
      var defaultExport = this._extractDefaultExport(normalizedModuleName, parsedName);

      if (defaultExport === undefined) {
        throw new Error(" Expected to find: '" + parsedName.fullName + "' within '" + normalizedModuleName + "' but got 'undefined'. Did you forget to `export default` within '" + normalizedModuleName + "'?");
      }

      if (this.shouldWrapInClassFactory(defaultExport, parsedName)) {
        defaultExport = classFactory(defaultExport);
      }

      return defaultExport;
    } else {
      return this._super(parsedName);
    }
  }

  // Ember.DefaultResolver docs:
  //   https://github.com/emberjs/ember.js/blob/master/packages/ember-application/lib/system/resolver.js
  var Resolver = Ember.DefaultResolver.extend({
    resolveOther: resolveOther,
    resolveTemplate: resolveOther,
    pluralizedTypes: null,

    makeToString: function(factory, fullName) {
      return '' + this.namespace.modulePrefix + '@' + fullName + ':';
    },
    parseName: parseName,
    shouldWrapInClassFactory: function(module, parsedName){
      return false;
    },
    init: function() {
      this._super();
      this.moduleBasedResolver = true;
      this._normalizeCache = makeDictionary();

      this.pluralizedTypes = this.pluralizedTypes || makeDictionary();

      if (!this.pluralizedTypes.config) {
        this.pluralizedTypes.config = 'config';
      }

      this._deprecatedPodModulePrefix = false;
    },
    normalize: function(fullName) {
      return this._normalizeCache[fullName] || (this._normalizeCache[fullName] = this._normalize(fullName));
    },
    _normalize: function(fullName) {
      // replace `.` with `/` in order to make nested controllers work in the following cases
      // 1. `needs: ['posts/post']`
      // 2. `{{render "posts/post"}}`
      // 3. `this.render('posts/post')` from Route
      var split = fullName.split(':');
      if (split.length > 1) {
        return split[0] + ':' + Ember.String.dasherize(split[1].replace(/\./g, '/'));
      } else {
        return fullName;
      }
    },

    pluralize: function(type) {
      return this.pluralizedTypes[type] || (this.pluralizedTypes[type] = type + 's');
    },

    podBasedLookupWithPrefix: function(podPrefix, parsedName) {
      var fullNameWithoutType = parsedName.fullNameWithoutType;

      if (parsedName.type === 'template') {
        fullNameWithoutType = fullNameWithoutType.replace(/^components\//, '');
      }

        return podPrefix + '/' + fullNameWithoutType + '/' + parsedName.type;
    },

    podBasedModuleName: function(parsedName) {
      var podPrefix = this.namespace.podModulePrefix || this.namespace.modulePrefix;

      return this.podBasedLookupWithPrefix(podPrefix, parsedName);
    },

    podBasedComponentsInSubdir: function(parsedName) {
      var podPrefix = this.namespace.podModulePrefix || this.namespace.modulePrefix;
      podPrefix = podPrefix + '/components';

      if (parsedName.type === 'component' || parsedName.fullNameWithoutType.match(/^components/)) {
        return this.podBasedLookupWithPrefix(podPrefix, parsedName);
      }
    },

    mainModuleName: function(parsedName) {
      // if router:main or adapter:main look for a module with just the type first
      var tmpModuleName = parsedName.prefix + '/' + parsedName.type;

      if (parsedName.fullNameWithoutType === 'main') {
        return tmpModuleName;
      }
    },

    defaultModuleName: function(parsedName) {
      return parsedName.prefix + '/' +  this.pluralize(parsedName.type) + '/' + parsedName.fullNameWithoutType;
    },

    prefix: function(parsedName) {
      var tmpPrefix = this.namespace.modulePrefix;

      if (this.namespace[parsedName.type + 'Prefix']) {
        tmpPrefix = this.namespace[parsedName.type + 'Prefix'];
      }

      return tmpPrefix;
    },

    /**

      A listing of functions to test for moduleName's based on the provided
      `parsedName`. This allows easy customization of additional module based
      lookup patterns.

      @property moduleNameLookupPatterns
      @returns {Ember.Array}
    */
    moduleNameLookupPatterns: Ember.computed(function(){
      return Ember.A([
        this.podBasedModuleName,
        this.podBasedComponentsInSubdir,
        this.mainModuleName,
        this.defaultModuleName
      ]);
    }),

    findModuleName: function(parsedName, loggingDisabled){
      var self = this;
      var moduleName;

      this.get('moduleNameLookupPatterns').find(function(item) {
        var moduleEntries = requirejs.entries;
        var tmpModuleName = item.call(self, parsedName);

        // allow treat all dashed and all underscored as the same thing
        // supports components with dashes and other stuff with underscores.
        if (tmpModuleName) {
          tmpModuleName = self.chooseModuleName(moduleEntries, tmpModuleName);
        }

        if (tmpModuleName && moduleEntries[tmpModuleName]) {
          if (!loggingDisabled) {
            self._logLookup(true, parsedName, tmpModuleName);
          }

          moduleName = tmpModuleName;
        }

        if (!loggingDisabled) {
          self._logLookup(moduleName, parsedName, tmpModuleName);
        }

        return moduleName;
      });

      return moduleName;
    },

    chooseModuleName: function(moduleEntries, moduleName) {
      var underscoredModuleName = Ember.String.underscore(moduleName);

      if (moduleName !== underscoredModuleName && moduleEntries[moduleName] && moduleEntries[underscoredModuleName]) {
        throw new TypeError("Ambiguous module names: `" + moduleName + "` and `" + underscoredModuleName + "`");
      }

      if (moduleEntries[moduleName]) {
        return moduleName;
      } else if (moduleEntries[underscoredModuleName]) {
        return underscoredModuleName;
      } else {
        // workaround for dasherized partials:
        // something/something/-something => something/something/_something
        var partializedModuleName = moduleName.replace(/\/-([^\/]*)$/, '/_$1');

        if (moduleEntries[partializedModuleName]) {
          Ember.deprecate('Modules should not contain underscores. ' +
                          'Attempted to lookup "'+moduleName+'" which ' +
                          'was not found. Please rename "'+partializedModuleName+'" '+
                          'to "'+moduleName+'" instead.', false);

          return partializedModuleName;
        } else {
          return moduleName;
        }
      }
    },

    // used by Ember.DefaultResolver.prototype._logLookup
    lookupDescription: function(fullName) {
      var parsedName = this.parseName(fullName);

      var moduleName = this.findModuleName(parsedName, true);

      return moduleName;
    },

    // only needed until 1.6.0-beta.2 can be required
    _logLookup: function(found, parsedName, description) {
      if (!Ember.ENV.LOG_MODULE_RESOLVER && !parsedName.root.LOG_RESOLVER) {
        return;
      }

      var symbol, padding;

      if (found) { symbol = '[✓]'; }
      else       { symbol = '[ ]'; }

      if (parsedName.fullName.length > 60) {
        padding = '.';
      } else {
        padding = new Array(60 - parsedName.fullName.length).join('.');
      }

      if (!description) {
        description = this.lookupDescription(parsedName);
      }

      Ember.Logger.info(symbol, parsedName.fullName, padding, description);
    },

    knownForType: function(type) {
      var moduleEntries = requirejs.entries;
      var moduleKeys = (Object.keys || Ember.keys)(moduleEntries);

      var items = makeDictionary();
      for (var index = 0, length = moduleKeys.length; index < length; index++) {
        var moduleName = moduleKeys[index];
        var fullname = this.translateToContainerFullname(type, moduleName);

        if (fullname) {
          items[fullname] = true;
        }
      }

      return items;
    },

    translateToContainerFullname: function(type, moduleName) {
      var prefix = this.prefix({ type: type });
      var pluralizedType = this.pluralize(type);
      var nonPodRegExp = new RegExp('^' + prefix + '/' + pluralizedType + '/(.+)$');
      var podRegExp = new RegExp('^' + prefix + '/(.+)/' + type + '$');
      var matches;


      if ((matches = moduleName.match(podRegExp))) {
        return type + ':' + matches[1];
      }

      if ((matches = moduleName.match(nonPodRegExp))) {
        return type + ':' + matches[1];
      }
    },

    _extractDefaultExport: function(normalizedModuleName) {
      var module = require(normalizedModuleName, null, null, true /* force sync */);

      if (module && module['default']) {
        module = module['default'];
      }

      return module;
    }
  });

  Resolver.moduleBasedResolver = true;
  Resolver['default'] = Resolver;
  return Resolver;
});

define("resolver",
  ["ember/resolver"],
  function (Resolver) {
    Ember.deprecate('Importing/requiring Ember Resolver as "resolver" is deprecated, please use "ember/resolver" instead');
    return Resolver;
  });

})();



(function() {
/*globals define registry requirejs */

define("ember/container-debug-adapter",
  [],
  function() {
    "use strict";

  // Support Ember < 1.5-beta.4
  // TODO: Remove this after 1.5.0 is released
  if (typeof Ember.ContainerDebugAdapter === 'undefined') {
    return null;
  }
  /*
   * This module defines a subclass of Ember.ContainerDebugAdapter that adds two
   * important features:
   *
   *  1) is able provide injections to classes that implement `extend`
   *     (as is typical with Ember).
   */

  var ContainerDebugAdapter = Ember.ContainerDebugAdapter.extend({
    /**
      The container of the application being debugged.
      This property will be injected
      on creation.

      @property container
      @default null
    */
    // container: null, LIVES IN PARENT

    /**
      The resolver instance of the application
      being debugged. This property will be injected
      on creation.

      @property resolver
      @default null
    */
    // resolver: null,  LIVES IN PARENT
    /**
      Returns true if it is possible to catalog a list of available
      classes in the resolver for a given type.

      @method canCatalogEntriesByType
      @param {string} type The type. e.g. "model", "controller", "route"
      @return {boolean} whether a list is available for this type.
    */
    canCatalogEntriesByType: function(type) {
      return true;
    },

    /**
     * Get all defined modules.
     *
     * @method _getEntries
     * @return {Array} the list of registered modules.
     * @private
     */
    _getEntries: function() {
      return requirejs.entries;
    },

    /**
      Returns the available classes a given type.

      @method catalogEntriesByType
      @param {string} type The type. e.g. "model", "controller", "route"
      @return {Array} An array of classes.
    */
    catalogEntriesByType: function(type) {
      var entries = this._getEntries(),
          module,
          types = Ember.A();

      var makeToString = function(){
        return this.shortname;
      };

      var prefix = this.namespace.modulePrefix;

      for(var key in entries) {
        if(entries.hasOwnProperty(key) && key.indexOf(type) !== -1) {
          // Check if it's a pod module
          var name = getPod(type, key, this.namespace.podModulePrefix || prefix);
          if (!name) {
            // Not pod
            name = key.split(type + 's/').pop();

            // Support for different prefix (such as ember-cli addons).
            // Uncomment the code below when
            // https://github.com/ember-cli/ember-resolver/pull/80 is merged.

            //var match = key.match('^/?(.+)/' + type);
            //if (match && match[1] !== prefix) {
              // Different prefix such as an addon
              //name = match[1] + '@' + name;
            //}
          }
          types.addObject(name);
        }
      }
      return types;
    }
  });

  function getPod(type, key, prefix) {
    var match = key.match(new RegExp('^/?' + prefix + '/(.+)/' + type + '$'));
    if (match) {
      return match[1];
    }
  }

  ContainerDebugAdapter['default'] = ContainerDebugAdapter;
  return ContainerDebugAdapter;
});

})();



(function() {
(function() {
  "use strict";

  Ember.Application.initializer({
    name: 'container-debug-adapter',

    initialize: function(container, app) {
      var ContainerDebugAdapter = require('ember/container-debug-adapter');
      var Resolver = require('ember/resolver');

      container.register('container-debug-adapter:main', ContainerDebugAdapter);
      app.inject('container-debug-adapter:main', 'namespace', 'application:main');
    }
  });
}());

})();



(function() {

})();

