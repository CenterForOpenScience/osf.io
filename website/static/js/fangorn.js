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
            global.Fangorn = factory(jQuery, global.Treebeard);
            $script.done('fangorn');
    }else {
        global.Fangorn = factory(jQuery, global.Treebeard);
    }
}(this, function($, Treebeard){

 /// Domething else 
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
                folderIcons : true,
                sort : true
            },
            {
                title: "Downloads",
                width : "20%",
                data : "downloads",
                sort : true
            },
            {
                title: "Size",
                width : "20%",
                sort : false,
                data : "size"
            }
        ],
        deletecheck : function(){  // When user attempts to delete a row, allows for checking permissions etc. NOT YET IMPLEMENTED
            // this = Item to be deleted.
        },
        ondelete : function(){  // When row is deleted successfully
            // this = parent of deleted row
            console.log("ondelete", this);
        },
        movecheck : function(to, from){
            // This method gives the users an option to do checks and define their return

            console.log("movecheck: to", to, "from", from);
            return true;
        },
        onmove : function(to, from){  // After move happens
            // to = actual tree object we are moving to
            // from = actual tree object we are moving
            console.log("onmove: to", to, "from", from);
        },
        addcheck : function(item, file){
            // item = item to be added to
            // info about the file being added
            return true;
        },
        onadd : function(item, response){
            // item = item that just received the added content
            // response : what's returned from the server
        },
        onselectrow : function(){
            // this = row
            console.log("onselectrow", this);
        },
        ontogglefolder : function(){
            // this = toggled folder
            console.log("ontogglefolder", this);
        },
        dropzone : {            // All dropzone options.
            url: "http://www.torrentplease.com/dropzone.php",  // Users provide single URL, if they need to generate url dynamicaly they can use the events.
            dropend : function(item, event){     // An example dropzone event to override.
                // this = dropzone object
                // item = item in the tree
                // event = event
            }
        }
    };

    function Fangorn(options) {
        console.log("hi");
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
            this.grid = Treebeard.run(this.options);
            //console.log(this.options);
            return this;
        }
    };

    return Fangorn;
}));