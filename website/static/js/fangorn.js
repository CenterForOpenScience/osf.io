/**
 *  Fangorn: Defining Treebeard options for OSF.
 *
 */

var $ = require('jquery');
// Required for uploads
require('dropzone-patch');
var m = require('mithril');
var Treebeard = require('treebeard');
var $osf = require('osf-helpers');
var bootbox = require('bootbox');

    // Returns custom icons for OSF 
    function _fangornResolveIcon(item){
        var privateFolder = m('img', { src : '/static/img/hgrid/fatcowicons/folder_delete.png' }),
            pointerFolder = m('i.icon-hand-right', ' '),
            openFolder  = m('i.icon-folder-open-alt', ' '),
            closedFolder = m('i.icon-folder-close-alt', ' '),
            configOption = item.data.addon ? resolveconfigOption.call(this, item, 'folderIcon', [item]) : undefined;                

        if (item.kind === 'folder') {
            if (item.data.iconUrl){
                return m('img', { src : item.data.iconUrl, style:{width:"16px", height:"auto"} });
            }
            if (!item.data.permissions.view) {
                return privateFolder; 
            }
            if (item.data.isPointer){
                return pointerFolder; 
            }
            if (item.open) {
                return configOption || openFolder;
            }
            return configOption || closedFolder;
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
    Fangorn.config = {};

    function getconfig(item, key) {
        if (item && item.data.addon && Fangorn.config[item.data.addon]) {
            return Fangorn.config[item.data.addon][key];
        }
        return undefined;
    }

    // Gets a Fangorn config option if it is defined by an addon dev.
    // Calls it with `args` if it's a function otherwise returns the value.
    // If the config option is not defined, return null
    function resolveconfigOption(item, option, args) {
        var self = this;
        var prop = getconfig(item, option);
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
        if (item.kind === 'folder' && (item.children.length > 0 || item.data.addon ) ) {
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
        item.notify.update('Not allowed: Private folder', 'warning', 1, undefined);
        return false;
    }
    
    function _fangornResolveUploadUrl (item) {
        var configOption = resolveconfigOption.call(this, item, 'uploadUrl', [item]);
        return configOption || item.data.urls.upload;
    }  

    function _fangornMouseOverRow (item, event) {
        $('.fg-hover-hide').hide(); 
        $(event.target).closest('.tb-row').find('.fg-hover-hide').show();
    }

    function _fangornUploadProgress (treebeard, file, progress){
        window.console.log('File Progress', this, arguments);
        var item = treebeard.dropzoneItemCache.children[0];
        var msgText = 'Uploaded ' + Math.floor(progress) + '%'; 
        if(progress < 100) {
            item.notify.update(msgText, 'success', 1, 0);
        } else {
            item.notify.update(msgText, 'success', 1, 2000);
        }

    }

    function _fangornSending (treebeard, file, xhr, formData) {
        var parentID = treebeard.dropzoneItemCache.id;
        var parent = treebeard.dropzoneItemCache;
        // create a blank item that will refill when upload is finished. 
        var blankItem = {
            name : file.name,
            kind : 'item',
            addon : parent.data.addon,
            children : [],
            data : { permissions : parent.data.permissions }
        };
        var newItem = treebeard.createItem(blankItem, parentID);
        var configOption = resolveconfigOption.call(treebeard, parent, 'uploadSending', [file, xhr, formData]);
        return configOption || null;
    }

    function _fangornAddedFile(treebeard, file){
        //this == dropzone
        var item = treebeard.dropzoneItemCache;
        var configOption = resolveconfigOption.call(treebeard, item, 'uploadAdd', [file, item]);
        return configOption || null;
    }

    function _fangornDragOver (treebeard, event) {
        var dropzoneHoverClass = "fangorn-dz-hover"; 
        $('.tb-row').removeClass(dropzoneHoverClass);

        var closestTarget = $(event.target).closest('.tb-row');
        var itemID =  closestTarget.context.dataset.id;
        var item = treebeard.find(itemID); 
        if(itemID != undefined) {
            if (item.data.urls) {
                if (item.data.urls.upload != null && item.kind === 'folder') { 
                    $(event.target).closest('.tb-row').addClass(dropzoneHoverClass);
                }  
            }
        }
    }

    function _fangornComplete (treebeard, file) {
        var item = treebeard.dropzoneItemCache; 
        var configOption = resolveconfigOption.call(treebeard, item, 'onUploadComplete', [item]);

        window.console.log("Complete", configOption);
    }

    function _fangornDropzoneSuccess (treebeard, file, response) {
        window.console.log("Success", arguments);
        var item = treebeard.dropzoneItemCache.children[0];
        window.console.log("RESPONSE: ", response);
        // RESPONSES
        // OSF : Object with actionTake : "file_added"
        // DROPBOX : Object; addon : 'dropbox'
        // S3 : Nothing
        // GITHUB : Object; addon : 'github'
        //Dataverse : Object, actionTaken : file_uploaded
        var revisedItem = resolveconfigOption.call(treebeard, item.parent(), 'uploadSuccess', [file, item, response]);         
        if(!revisedItem && response){
            if(response.actionTaken === 'file_added' || response.addon === 'dropbox' || response.addon === 'github' || response.addon === 'dataverse'){ // Base OSF response
                item.data = response;
            }
        }
        //item.notify = false;
        treebeard.redraw();
    }

    function _fangornDropzoneError (treebeard, file, message) {
        window.console.log('Error', arguments);
        var item = treebeard.dropzoneItemCache.children[0];
        item.notify.type = 'danger';
        var msgText = message.message_short ? message.message_short : message; 
        item.notify.message = msgText; 
        item.notify.col = 1; 
        item.notify.selfDestruct(treebeard, item); 
    }

    function _uploadEvent (event, item, col){
        window.console.log(item);
        try {
            event.stopPropagation();
        }
        catch (e) {
            window.event.cancelBubble = true;
        } 
        this.dropzone.hiddenFileInput.click();
        this.dropzoneItemCache = item;
        this.updateFolder(null, item); 
        window.console.log('Upload Event triggered', this, event,  item, col);
    }

    function _downloadEvent (event, item, col) {
        try {
            event.stopPropagation();
        }
        catch (e) {
            window.event.cancelBubble = true;
        }        
        window.console.log('Download Event triggered', this, event, item, col);
        if(item.data.addon === 'osfstorage'){
            item.data.downloads++;    
        }
        window.location = item.data.urls.download;
    }

    function _removeEvent (event, item, col) {
        try {
            event.stopPropagation();
        }
        catch (e) {
            window.event.cancelBubble = true;
        } 
        window.console.log('Remove Event triggered', this, event, item, col);
        var tb = this;
        item.notify.update('Deleting...', 'deleting', undefined, 3000); 
        if(item.data.permissions.edit){
            // delete from server, if successful delete from view
            $.ajax({ 
              url: item.data.urls.delete,
              type : 'DELETE'
            })
            .done(function(data) {
                // delete view
                tb.deleteNode(item.parentID, item.id);                 
                window.console.log('Delete success: ', data); 
            })
            .fail(function(data){
                window.console.log('Delete failed: ', data); 
                item.notify.update('Delete failed.', 'danger', undefined, 3000); 
            }); 
        }
    }

    function _fangornResolveLazyLoad(tree, item){
        var configOption = resolveconfigOption.call(this, item, 'lazyload', [item]);
        if(configOption){
            return configOption;
        }
        return item.data.urls.fetch || false;
    }

    function _fangornFileExists (item, file) {
        var i,
            child;
        for(i = 0; i < item.children.length; i++){
            child = item.children[i];
            if(child.kind === 'item' && child.data.name === file.name) {
                return true;
            }
        }
        return false; 
    }

    function _fangornLazyLoadError (item) {
        // this = treebeard; 
        var self= this; 
        var configOption = resolveconfigOption.call(this, item, 'lazyLoadError', [item]);
        if(!configOption) {
            tree.notify.update('Files couldn\'t load, please try again later.', 'deleting', undefined, 3000); 
        }
    }

    function _fangornUploadMethod(item){
        var configOption = resolveconfigOption.call(this, item, 'uploadMethod', [item]);
        return configOption || 'POST';
    }

    // Action buttons; 
    function _fangornActionColumn (item, col){
        var self = this; 
        var buttons = [];

        // Upload button if this is a folder
        if (item.kind === 'folder' && item.data.addon && item.data.permissions.edit) {
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
                { 'class' : btn.css, style : btn.style, 'onclick' : function(event){ btn.onclick.call(self, event, item, col); } },
                [ m('span', { 'class' : btn.icon}, btn.name) ])
            ]);
        }); 
    } 

    function _fangornTitleColumn (item, col) {
        return m('span', 
            { onclick : function(){ 
                if (item.kind === 'item') {
                    window.location = item.data.urls.view;                    
                } 
            }}, 
            item.data.name);
    }

    function _fangornResolveRows(item){
        // this = treebeard;
        item.css = '';
        var default_columns = [];             // Defines columns based on data
        default_columns.push({
            data : 'name',  // Data field name
            folderIcons : true,
            filter : true,
            custom : _fangornTitleColumn
        });

        default_columns.push(
            {
            sortInclude : false,
            custom : _fangornActionColumn
        }); 
        if(item.data.addon === 'osfstorage'){
           default_columns.push({
                data : 'downloads',
                sortInclude : false,
                filter : false
            }); 
        } else {
           default_columns.push({
                data : 'downloads',
                sortInclude : false,
                filter : false,
                custom : function(){ return m(''); }
            });             
        }
        var checkConfig = false;
        if(item.data.addon || item.data.permissions) { // Workaround for figshare, TODO : Create issue
            checkConfig = true;
        }
        var configOption = checkConfig ? resolveconfigOption.call(this, item, 'resolveRows', [item]) : undefined;
        return configOption || default_columns;
    }

    function _fangornColumnTitles () {
        var columns = [];
        columns.push({
                title: 'Name',
                width : '50%',
                sort : true,
                sortType : 'text'
            },
            {
                title : 'Actions',
                width : '25%',
                sort : false
            }, 
            {
                title : 'Downloads',
                width : '25%',
                sort : false
            });
        return columns;  
    }

    function _loadTopLevelChildren () {
        for (var i = 0; i < this.treeData.children.length; i++) {
            this.updateFolder(null, this.treeData.children[i]);
        }
    }

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
            filterStyle : { 'float' : 'right', 'width' : '50%'},
            title : false,          // Title of the grid, boolean, string OR function that returns a string.
            allowMove : false,       // Turn moving on or off.
            hoverClass : 'fangorn-hover',
            togglecheck : _fangornToggleCheck,
            sortButtonSelector : { 
                up : 'i.icon-chevron-up',
                down : 'i.icon-chevron-down'
            },
            onload : function (){
                var tb = this;
                _loadTopLevelChildren.call(tb);  
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
                //window.console.log('Add check', this, treebeard, item, file);
                if(item.data.addon && item.kind === 'folder') {
                    if (item.data.permissions.edit){
                       if(!_fangornFileExists.call(treebeard, item, file)){
                            if(item.data.accept && item.data.accept.maxSize){
                                var size = Math.round(file.size/10000)/100;
                                var maxSize = item.data.accept.maxSize;  
                                if(maxSize >= size && size !== 0){
                                    return true;
                                }
                                if(maxSize < size )  {
                                    var msgText = 'One of the files is too large (' + size + ' MB). Max file size is ' + item.data.accept.maxSize + ' MB.' ; 
                                    item.notify.update(msgText, 'warning', undefined, 3000);   
                                }
                                if(size === 0)  {
                                    var msgText = 'Some files were ignored because they were empty.' ; 
                                    item.notify.update(msgText, 'warning', undefined, 3000);   
                                }
                                return false;
                            }
                            return true;    
                        } else {
                            var msgText = 'File already exists.'; 
                            item.notify.update(msgText, 'warning', 1, 3000);
                        }
                        
                    } else {
                        var msgText = 'You don\'t have permission to upload here'; 
                        item.notify.update(msgText, 'warning', 1, 3000, 'animated flipInX');                    
                    }
                }
                
                return false;
            },
            onselectrow : function (item) {
                window.console.log('Row: ', item);
            },
            onmouseoverrow : _fangornMouseOverRow,
            dropzone : {                                           // All dropzone options.
                url: '/api/v1/project/',  // When users provide single URL for all uploads
                clickable : '#treeGrid',
                addRemoveLinks: false,
                previewTemplate: '<div></div>',
                parallelUploads: 1
                
            },
            resolveIcon : _fangornResolveIcon,
            resolveToggle : _fangornResolveToggle,
            resolveUploadUrl : _fangornResolveUploadUrl,
            resolveLazyloadUrl : _fangornResolveLazyLoad,
            lazyLoadError : _fangornLazyLoadError,
            resolveUploadMethod :_fangornUploadMethod,
            dropzoneEvents : {
                uploadprogress : _fangornUploadProgress,
                sending : _fangornSending,
                complete : _fangornComplete,
                success : _fangornDropzoneSuccess,
                error : _fangornDropzoneError,
                dragover : _fangornDragOver,
                addedfile : _fangornAddedFile
            }
    };

    function Fangorn(options) {
        this.options = $.extend({}, tbOptions, options);
        window.console.log('Options', this.options);
        this.grid = null; // Set by _initGrid
        this.init();
    }

    Fangorn.prototype = {
        constructor: Fangorn,
        init: function() {
            this._initGrid();
        },
        // Create the Treebeard once all addons have been configured
        _initGrid: function() {
            this.grid = Treebeard(this.options);
            return this.grid;
        }

    };

module.exports = Fangorn;