(function() {
define("ember/load-initializers",
  [],
  function() {
    "use strict";

    return {
      'default': function(app, prefix) {
        var regex = new RegExp('^' + prefix + '\/((?:instance-)?initializers)\/');
        var getKeys = (Object.keys || Ember.keys);

        getKeys(requirejs._eak_seen).map(function (moduleName) {
            return {
              moduleName: moduleName,
              matches: regex.exec(moduleName)
            };
          })
          .filter(function(dep) {
            return dep.matches && dep.matches.length === 2;
          })
          .forEach(function(dep) {
            var moduleName = dep.moduleName;

            var module = require(moduleName, null, null, true);
            if (!module) { throw new Error(moduleName + ' must export an initializer.'); }

            var initializerType = Ember.String.camelize(dep.matches[1].substring(0, dep.matches[1].length - 1));
            var initializer = module['default'];
            if (!initializer.name) {
              var initializerName = moduleName.match(/[^\/]+\/?$/)[0];
              initializer.name = initializerName;
            }

            app[initializerType](initializer);
          });
      }
    }
  }
);
})();
