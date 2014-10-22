/**
 * Created by faye on 10/15/14.
 */
/**
 * An OSF-flavored wrapper around Treebeard.
 *
 * Module to render the consolidated files view. Reads addon configurations and
 * initializes a Treebeard.
 */

//Unnamed function that attaches fangorn to the global namespace (which will usually be window)
(function (global, factory) {
    //AMD Uses the CommonJS practice of string IDs for dependencies.
    //  Clear declaration of dependencies and avoids the use of globals.
    //IDs can be mapped to different paths. This allows swapping out implementation.
    // This is great for creating mocks for unit testing.
    //Encapsulates the module definition. Gives you the tools to avoid polluting the global namespace.
    //Clear path to defining the module value. Either use "return value;" or the CommonJS "exports" idiom,
    //  which can be useful for circular dependencies.
    if (typeof define === 'function' && define.amd) {
        //asynconously calls these js files before calling the function (factory)
        define(['jquery', 'js/treebeard', 'bootstrap'], factory);
    } else if (typeof $script === 'function' ){
        //A less robust way of calling js files, once it is done call fangorn
        $script.ready(['treebeard'], function() {
            global.Fangorn = factory(jQuery, global.Treebeard);
            $script.done('fangorn');
        });
    }else {
        global.Fangorn = factory(jQuery, global.Treebeard);
    }
}(this, function($, Treebeard){

    // OSF-specific Treebeard options common to all addons
    baseOptions = {
        rowHeight : 35,
        showTotal : 15,
        paginate : false,
        lazyLoad : false,
        useDropzone : false,
        uploadURL : "",
        columns : [
            {
                title: "Title",
                width : "60%",
                data : "name",
                sort : true
            },
            {
                title: "Author",
                width : "30%",
                data : "name",
                sort : true
            },
            {
                title: "Actions",
                width : "10%",
                sort : false,
                data : "name"
            }
        ]
    };

    function Fangorn(selector, options) {
        console.log("hi");
        this.selector = selector;
        this.options = $.extend({}, baseOptions, options);
        this.grid = null; // Set by _initGrid
        this.init();
    }

    Fangorn.prototype = {
        constructor: Fangorn,
        init: function() {
            var self = this;
//            this._registerListeners()
                this._initGrid();
        },
//        _registerListeners: function() {
//            for (var addon in Fangorn.cfg) {
//                var listeners = Fangorn.cfg[addon].listeners;
//                if (listeners) {
//                    // Add each listener to the Treebeard options
//                    for (var i = 0, listener; listener = listeners[i]; i++) {
//                        this.options.listeners.push(listener);
//                    }
//                }
//            }
//            return this;
//        },
        // Create the Treebeard once all addons have been configured
        _initGrid: function() {
            this.grid = Treebeard.run(this.selector, this.options);
            //console.log(this.options);
            return this;
        }
    };

    return Fangorn;
}));
