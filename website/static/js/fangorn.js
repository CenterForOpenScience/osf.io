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

    // Returns custom icons for OSF 
    function _fangornResolveIcon(item){
        if (item.kind === 'folder') {
            if (item.open) { 
                return m('i.icon-folder-open-alt', ' ');
            }
            return m('i.icon-folder-close-alt', ' ');
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

    function _fangornResolveUploadUrl (item) {  
        return item.data.urls.upload;
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

    function _fangornSuccess (treebeard, file, response) {
        console.log("Success", arguments);
        m.redraw.strategy("all");
        var element = $( ".tb-row:contains('"+file.name+"')" );
        var id  = element.attr('data-id');
        var item = treebeard.find(id);
        item.data = response;
        m.render(element.find('.action-col').get(0), _fangornActionColumn.call(treebeard, item, _fangornColumns[1]));
        treebeard.redraw();
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
                window.location = item.data.urls.view;
            }}, 
            item.data.name);
    }

    var _fangornColumns = [            // Defines columns based on data
        {
            title: 'Name',
            width : '60%',
            data : 'name',  // Data field name
            sort : true,
            sortType : 'text',
            filter : true,
            folderIcons : true, 
            custom : _fangornTitleColumn
        },
        {
            title : 'Actions',
            width : '20%',
            sort : false,
            filter : false,
            css : 'action-col',
            custom : _fangornActionColumn
        },
        {
            title : 'Downloads',
            width : '20%',
            data  : 'downloads',
            sort : false,
            filter : false,
            css : ''
        }
    ]; 

    // OSF-specific Treebeard options common to all addons
    tbOptions = {
            rowHeight : 35,         // user can override or get from .tb-row height
            showTotal : 15,         // Actually this is calculated with div height, not needed. NEEDS CHECKING
            paginate : false,       // Whether the applet starts with pagination or not.
            paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
            uploads : true,         // Turns dropzone on/off.
            columns : _fangornColumns,
            showFilter : true,     // Gives the option to filter by showing the filter box.
            title : false,          // Title of the grid, boolean, string OR function that returns a string.
            allowMove : false,       // Turn moving on or off.
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
            resolveLazyloadUrl : false,
            dropzoneEvents : {
                uploadprogress : _fangornUploadProgress,
                sending : _fangornSending,
                complete : _fangornComplete,
                success : _fangornSuccess
            }
    };

    function Fangorn(options) {
        this.options = $.extend({}, tbOptions, options);
        console.log('Final options', this.options);
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
            return this;
        }
    };

    return Fangorn;
}));