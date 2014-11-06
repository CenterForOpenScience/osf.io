/**
 * Created by faye on 10/15/14.
 */
/**
 *  Defining Treebeard options for OSF.
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
    //Clear path to defining the module value. Either use 'return value;' or the CommonJS 'exports' idiom,
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

    // Shows an alert in the space of the row
    function _fangornRowAlert (item, type, message, method) {
        var dismiss;
        if(method === 'overlay'  ) {
            dismiss = ' ';
        } else {
            dismiss = '<span class="fangorn-dismiss" data-id="'+item.id+'">&times;</span>'
        }
        var alertHTML = '<div class="alert-'+type+' text-center" style="padding: 8px; margin-top: -5px;"> ' + message + dismiss + '</div>'; 
        var row = $('.tb-row[data-id="'+ item.id+ '"]'); 
        // Get row content

        if(method === "overlay"){
            var cache  = row.html(); 
            row.animate({ opacity : 0 }, "fast")
                .html(alertHTML)
                .animate({ opacity : 1 }, "fast")
                .delay(2000)
                .animate({ opacity : 0 }, "fast")
                .queue(function() {
                    $(this)
                        .html(cache)
                        .animate({ opacity : 1 }, "fast");
                    $(this).dequeue();
                });
        }
        if(method === "replace" ) {
            row.animate({ opacity : 0 }, "fast")
                .replaceWith(alertHTML)
                .animate({ opacity : 1 }, "fast");
            item.removeSelf();

        }

          
    }

    function _fangornViewEvents () {
        console.log("View events this", this);
    }

    // Returns custom icons for OSF 
    function _fangornResolveIcon(item){
        var privateFolder = m('img', { src : "/static/img/hgrid/fatcowicons/folder_delete.png" }),
            pointerFolder = m('i.icon-hand-right', ' '),
            openFolder  = m('i.icon-folder-open-alt', ' '),
            closedFolder = m('i.icon-folder-close-alt', ' '),
            cfgOption = resolveCfgOption.call(this, item, 'folderIcon', [item]);

        if (item.kind === 'folder') {
            if (!item.data.permissions.view) {
                return privateFolder; 
            }
            if (item.data.isPointer){
                return pointerFolder; 
            }
            if (item.open) {
                return cfgOption || openFolder;
            }
            return cfgOption || closedFolder;
        }
        if (item.data.icon) {
            return m('i.fa.' + item.data.icon, ' ');
        }

        var ext = item.data.name.split('.').pop().toLowerCase(),
            extensions = ['3gp', '7z', 'ace', 'ai', 'aif', 'aiff', 'amr', 'asf', 'asx', 'bat', 'bin', 'bmp', 'bup',
        'cab', 'cbr', 'cda', 'cdl', 'cdr', 'chm', 'dat', 'divx', 'dll', 'dmg', 'doc', 'docx', 'dss', 'dvf', 'dwg',
        'eml', 'eps', 'exe', 'fla', 'flv', 'gif', 'gz', 'hqx', 'htm', 'html', 'ifo', 'indd', 'iso', 'jar',
        'jpeg', 'jpg', 'lnk', 'log', 'm4a', 'm4b', 'm4p', 'm4v', 'mcd', 'mdb', 'mid', 'mov', 'mp2', 'mp3', 'mp4',
        'mpeg', 'mpg', 'msi', 'mswmm', 'ogg', 'pdf', 'png', 'pps', 'ps', 'psd', 'pst', 'ptb', 'pub', 'qbb',
        'qbw', 'qxd', 'ram', 'rar', 'rm', 'rmvb', 'rtf', 'sea', 'ses', 'sit', 'sitx', 'ss', 'swf', 'tgz', 'thm',
        'tif', 'tmp', 'torrent', 'ttf', 'txt', 'vcd', 'vob', 'wav', 'wma', 'wmv', 'wps', 'xls', 'xpi', 'zip',
        'xlsx', 'py'];

        if(extensions.indexOf(ext) !== -1){
            return m('img', { src : '/static/img/hgrid/fatcowicons/file_extension_'+ext+'.png'});
        }
        return m('i.icon-file-alt');
    }
    // Addon config registry
    Fangorn.cfg = {};

    function getCfg(item, key) {
        if (item && item.data.addon && Fangorn.cfg[item.data.addon]) {
            return Fangorn.cfg[item.data.addon][key];
        }
        return undefined;
    }

    // Gets a Fangorn config option if it is defined by an addon dev.
    // Calls it with `args` if it's a function otherwise returns the value.
    // If the config option is not defined, return null
    function resolveCfgOption(item, option, args) {
        var self = this;
        var prop = getCfg(item, option);
        if (prop) {
            return typeof prop === 'function' ? prop.apply(self, args) : prop;
        } else {
            return null;
        }
    }





    // Returns custom toggle icons for OSF
    function _fangornResolveToggle(item){
        var toggleMinus = m('i.icon-minus', ' '),
            togglePlus = m('i.icon-plus', ' ');
        if (item.kind === 'folder') {
            if (item.open) {
                return toggleMinus;
            }
            return togglePlus;
        }
        return '';
    }

    function _fangornToggleCheck (item) {
        if (item.data.permissions.view) {
            return true;
        }
        _fangornRowAlert (item, "warning", "You don't have permission to view the contents of this folder.", "overlay");
        return false;
    }
    function _fangornResolveUploadUrl (item) {
        var cfgOption = resolveCfgOption.call(this, item, 'uploadUrl', [item]);
        return cfgOption || item.data.urls.upload;
    }  

    function _fangornMouseOverRow (item, event) {
        $('.fg-hover-hide').hide(); 
        $(event.target).closest('.tb-row').find('.fg-hover-hide').show();
    }

    function _fangornUploadProgress (treebeard, file, progress, bytesSent){
        console.log("File Progress", this, arguments);
        var itemID = treebeard.dropzoneItemCache.id; 
        // Find the row of the file being uploaded
        $( ".tb-row:contains('"+file.name+"')" ).find('.action-col').text('Uploaded ' + Math.floor(progress) + '%');
        // $('.tb-row[data-id="'+itemID+'"]').find('.action-col').text('Uploaded ' + progress + '%');
    }

    function _fangornSending (treebeard, file, xhr, formData) {
        console.log("Sending", arguments);
        var parentID = treebeard.dropzoneItemCache.id; 
        // create a blank item that will refill when upload is finished. 
        var blankItem = {
            name : file.name,
            kind : 'item',
            children : []
        }; 
        treebeard.createItem(blankItem, parentID); 
    }

    function _fangornComplete (treebeard, file) {
        console.log("Complete", arguments);
    }

    function _fangornDropzoneSuccess (treebeard, file, response) {
        console.log("Success", arguments);
        var element = $( ".tb-row:contains('"+file.name+"')" );
        var id  = element.attr('data-id');
        var item = treebeard.find(id);
        item.data = response;
        m.render(element.find('.action-col').get(0), _fangornActionColumn.call(treebeard, item, _fangornColumns[1]));
        m.redraw();
    }

    function _fangornDropzoneError (treebeard, file, message, xhr) {
        console.log("Error", arguments);
        var element = $( ".tb-row:contains('"+file.name+"')" );
        var id  = element.attr('data-id');
        var item = treebeard.find(id);
        _fangornRowAlert.call(treebeard, item, 'danger', file.name + " did't upload: " + message.message_short, "replace");
        //treebeard.deleteNode(item.parentID, item.id);
    }

    function _uploadEvent (event, item, col){
        event.stopPropagation();
        this.dropzone.hiddenFileInput.click();
        this.dropzoneItemCache = item; 
        console.log('Upload Event triggered', this, event,  item, col);
    }

    function _downloadEvent (event, item, col) {
        event.stopPropagation();
        console.log('Download Event triggered', this, event, item, col);
        item.data.downloads++; 
        window.location = item.data.urls.download;

    }

    function _removeEvent (event, item, col) {
        event.stopPropagation();
        console.log('Remove Event triggered', this, event, item, col);
        var tb = this; 
        if(item.data.permissions.edit){
            // delete from server, if successful delete from view
            $.ajax({ 
              url: item.data.urls.delete,
              type : 'DELETE'
            })
            .done(function(data) {
                // delete view
                tb.deleteNode(item.parentID, item.id);                 
                console.log('Delete success: ', data); 
            })
            .fail(function(data){
                console.log('Delete failed: ', data); 
            }); 
        }
    }

    function _fangornResolveLazyLoad(tree, item){
        var cfgOption = resolveCfgOption.call(this, item, 'lazyload', [item]);
        return cfgOption || false;
    }

    // Action buttons; 
    function _fangornActionColumn (item, col){
        var self = this; 
        var buttons = [];

        // Upload button if this is a folder
        if (item.kind === 'folder') {
            buttons.push({ 
                'name' : '',
                'icon' : 'icon-upload-alt',
                'css' : 'fangorn-clickable btn btn-default btn-xs',
                'onclick' : _uploadEvent
            });
        }

        //Download button if this is an item
        if (item.kind === 'item') {
            buttons.push({ 
                'name' : '',
                'icon' : 'icon-download-alt',
                'css' : 'btn btn-info btn-xs',
                'onclick' : _downloadEvent
            },
            { 
                'name' : '',
                'icon' : 'icon-remove',
                'css' : 'm-l-lg text-danger fg-hover-hide',
                'style' : 'display:none',
                'onclick' : _removeEvent
            }
            );
        }

        // Build the template for icons
        return buttons.map(function(btn){ 
            return m('span', { 'data-col' : item.id }, [ m('i', 
                { 'class' : btn.css, style : btn.style, 'onclick' : function(){ btn.onclick.call(self, event, item, col); } },
                [ m('span', { 'class' : btn.icon}, btn.name) ])
            ]);
        }); 
    } 

    function _fangornTitleColumn (item, col) {
        return m('span', 
            { onclick : function(){ 
                if (item.kind === "item") {
                    window.location = item.data.urls.view;                    
                } 
            }}, 
            item.data.name);
    }

    function _fangornResolveRows(item){
        // this = treebeard;
        var default_columns = [            // Defines columns based on data
            {
                data : "name",  // Data field name
                folderIcons : true,
                filter : true,
                custom : _fangornTitleColumn
            },
            {
                sortInclude : false,
                custom : _fangornActionColumn
            },
            {
                data : "downloads",
                sortInclude : false,
                filter : false
            }
        ];
        var cfgOption = resolveCfgOption.call(this, item, 'column', [item]);
        return cfgOption || default_columns;
    }

    var _fangornColumnTitles = [
                {
                    title: 'Name',
                    width : '60%',
                    sort : true,
                    sortType : 'text'
                },
                {
                    title : 'Actions',
                    width : '20%',
                    sort : false
                },
                {
                    title : 'Downloads',
                    width : '20%',
                    sort : false
                }
            ];
    // OSF-specific Treebeard options common to all addons
    tbOptions = {
            rowHeight : 35,         // user can override or get from .tb-row height
            showTotal : 15,         // Actually this is calculated with div height, not needed. NEEDS CHECKING
            paginate : false,       // Whether the applet starts with pagination or not.
            paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
            uploads : true,         // Turns dropzone on/off.
            columnTitles : _fangornColumnTitles,
            resolveRows : _fangornResolveRows,
            showFilter : true,     // Gives the option to filter by showing the filter box.
            title : false,          // Title of the grid, boolean, string OR function that returns a string.
            allowMove : false,       // Turn moving on or off.
            hoverClass : "fangorn-hover",
            toggleCheck : _fangornToggleCheck,
            sortButtonSelector : { 
                up : 'i.icon-chevron-up',
                down : 'i.icon-chevron-down'
            },
            onload : function (){
                var tb = this; 
                $(document).on('click', '.fangorn-dismiss', function(){
                     tb.redraw();
                 });
            },
            createcheck : function (item, parent) {
                window.console.log('createcheck', this, item, parent);
                return true;
            },
            deletecheck : function (item) {  // When user attempts to delete a row, allows for checking permissions etc.
                window.console.log('deletecheck', this, item);
                return true;
            },
            movecheck : function (to, from) { //This method gives the users an option to do checks and define their return
                window.console.log('movecheck: to', to, 'from', from);
                return true;
            },
            movefail : function (to, from) { //This method gives the users an option to do checks and define their return
                window.console.log('moovefail: to', to, 'from', from);
                return true;
            },
            addcheck : function (treebeard, item, file) {
                window.console.log('Add check', this, treebeard, item, file);
                if (item.data.permissions.edit){
                    return true;
                }
                _fangornRowAlert (item, "warning", "You don't have permission to edit this folder.", "overlay");
                return false;
            },
            onselectrow : function (item) {
                console.log('Row: ', item);
            },
            onmouseoverrow : _fangornMouseOverRow,
            dropzone : {                                           // All dropzone options.
                url: '/api/v1/project/',  // When users provide single URL for all uploads
                //previewTemplate : '<div class='dz-preview dz-file-preview'>     <div class='dz-details'>        <div class='dz-size' data-dz-size></div>    </div>      <div class='dz-progress'>       <span class='dz-upload' data-dz-uploadprogress></span>  </div>      <div class='dz-error-message'>      <span data-dz-errormessage></span>  </div></div>',
                clickable : '#treeGrid',
                addRemoveLinks: false,
                previewTemplate: '<div></div>'
            },
            resolveIcon : _fangornResolveIcon,
            resolveToggle : _fangornResolveToggle,
            resolveUploadUrl : _fangornResolveUploadUrl,
            resolveLazyloadUrl : _fangornResolveLazyLoad,
            dropzoneEvents : {
                uploadprogress : _fangornUploadProgress,
                sending : _fangornSending,
                complete : _fangornComplete,
                success : _fangornDropzoneSuccess,
                error : _fangornDropzoneError
            }
    };

    function Fangorn(options) {
        this.options = $.extend({}, tbOptions, options);
        console.log('Options', this.options);
        this.grid = null; // Set by _initGrid
        this.init();
    }

    Fangorn.prototype = {
        constructor: Fangorn,
        init: function() {
            var self = this;
            this._initGrid();
        },
        // Create the Treebeard once all addons have been configured
        _initGrid: function() {
            this.grid = Treebeard.run(this.options);
            return this.grid;
        }

    };

    return Fangorn;
}));