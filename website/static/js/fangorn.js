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

    // TODO: OSF does icons differently. write custom resolve icons. 
    function _fangornResolveIcon(item){
        // this = treebeard object;
        // Item = item acted on
        if (item.kind === "folder") {
            if (item.open) { 
                return m("i.icon-folder-open-alt", " ");
            }
            return m("i.icon-folder-close-alt", " ");
        }
        if (item.data.icon) {
            return m("i.fa." + item.data.icon, " ");
        }
        return m("i.icon-file-alt");
    }

    // TODO Action buttons; 
    function _fangornActionColumn (){
        var buttons = [ 
                { title: "Download", "css" : 'btn btn-danger'},
                { title : "View"}
                ];
       return buttons.map(function(btn){ 
                    // return [ m('i', btn.title )]
        }); 
    } 

    // OSF-specific Treebeard options common to all addons
    tbOptions = {
            rowHeight : 35,         // user can override or get from .tb-row height
            showTotal : 15,         // Actually this is calculated with div height, not needed. NEEDS CHECKING
            paginate : false,       // Whether the applet starts with pagination or not.
            paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
            uploads : true,         // Turns dropzone on/off.
            columns : [            // Defines columns based on data
                {
                    title: "Name",
                    width : "100%",
                    data : "name",  // Data field name
                    sort : true,
                    sortType : "text",
                    folderIcons : true
                }
            ],
            showFilter : true,     // Gives the option to filter by showing the filter box.
            title : false,          // Title of the grid, boolean, string OR function that returns a string.
            allowMove : false,       // Turn moving on or off.
            onfilter : function (filterText) {   // Fires on keyup when filter text is changed.
                // this = treebeard object;
                // filterText = the value of the filtertext input box.
                window.console.log("on filter: this", this, 'filterText', filterText);
            },
            onfilterreset : function (filterText) {   // Fires when filter text is cleared.
                // this = treebeard object;
                // filterText = the value of the filtertext input box.
                window.console.log("on filter reset: this", this, 'filterText', filterText);
            },
            createcheck : function (item, parent) {
                // this = treebeard object;
                // item = Item to be added.  raw item, not _item object
                // parent = parent to be added to = _item object
                window.console.log("createcheck", this, item, parent);
                return true;
            },
            oncreate : function (item, parent) {  // When row is deleted successfully
                // this = treebeard object;
                // item = Item to be added.  = _item object
                // parent = parent to be added to = _item object
                window.console.log("oncreate", this, item, parent);
            },
            deletecheck : function (item) {  // When user attempts to delete a row, allows for checking permissions etc.
                // this = treebeard object;
                // item = Item to be deleted.
                window.console.log("deletecheck", this, item);
                return true;
            },
            ondelete : function () {  // When row is deleted successfully
                // this = treebeard object;
                // item = a shallow copy of the item deleted, not a reference to the actual item
                window.console.log("ondelete", this);
            },
            movecheck : function (to, from) { //This method gives the users an option to do checks and define their return
                // this = treebeard object;
                // from = item that is being moved
                // to = the target location
                window.console.log("movecheck: to", to, "from", from);
                return true;
            },
            onmove : function (to, from) {  // After move happens
                // this = treebeard object;
                // to = actual tree object we are moving to
                // from = actual tree object we are moving
                window.console.log("onmove: to", to, "from", from);
            },
            movefail : function (to, from) { //This method gives the users an option to do checks and define their return
                // this = treebeard object;
                // from = item that is being moved
                // to = the target location
                window.console.log("moovefail: to", to, "from", from);
                return true;
            },
            addcheck : function (treebeard, item, file) {
                // this = dropzone object
                // treebeard = treebeard object
                // item = item to be added to
                // file = info about the file being added
                window.console.log("Add check", this, treebeard, item, file);
                return true;
            },
            onadd : function (treebeard, item, file, response) {
                // this = dropzone object;
                // item = item the file was added to
                // file = file that was added
                // response = what's returned from the server
                window.console.log("On add", this, treebeard, item, file, response);
            },
            onselectrow : function (row, event) {
                // this = treebeard object
                // row = item selected
                // event = mouse click event object
                window.console.log("onselectrow", this, row, event);
            },
            ontogglefolder : function (item, event) {
                // this = treebeard object
                // item = toggled folder item
                // event = mouse click event object
                window.console.log("ontogglefolder", this, item, event);
            },
            dropzone : {                                           // All dropzone options.
                url: "/api/v1/project/",  // When users provide single URL for all uploads
                dragstart : function (treebeard, event) {     // An example dropzone event to override.
                    // this = dropzone object
                    // treebeard = treebeard object
                    // event = event passed in
                    window.console.log("dragstart", this, treebeard, event);
                }
            },
            resolveIcon : _fangornResolveIcon,
            resolveUploadUrl : function (item) {  // Allows the user to calculate the url of each individual row
                // this = treebeard object;
                // Item = item acted on return item.data.ursl.upload
                window.console.log("resolveUploadUrl", this, item);
                return item.data.urls.upload;
            },
            resolveLazyloadUrl : false
            // function (item) {
            //     // this = treebeard object;
            //     // Item = item acted on
            //     window.console.log("resolveLazyloadUrl", this, item);
            //     return "small.json";
            // }


    };

    function Fangorn(options) {
        this.options = $.extend({}, tbOptions, options);
        console.log("Final options", this.options);
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