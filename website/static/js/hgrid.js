/**
 * Prototype for creating a Hierarchical Grid Structure
 *
 * @class HGrid
 * @author Jake Rosenberg
 * @author Alexander Ferguson
 */
var HGrid = {
    //Gives each div a class based on type (folder or file)
    /**
    Default options for HGrid

    @property defaultOptions
    @type {Object}
    @param defaultOptions.container null
    @param defaultOptions.url null
    @param defaultOptions.info null
    @param defaultOptions.columns Uid and Name columns
    @param defaultOptions.editable false
    @param defaultOptions.enableCellNavigation false
    @param defaultOptions.asyncEditorLoading false
    @param defaultOptions.enableColumnReorder true
    @param defaultOptions.sortAsc true
    @param defaultOptions.dragDrop true
    @param defaultOptions.dropZone true
    @param defaultOptions.dropZonePreviewsContainer null
    @param defaultOptions.navLevel null
    @param defaultOptions.breadcrumbBox null
    @param defaultOptions.largeGuide true
    @param defaultOptions.clickUploadElement true
    @param defaultOptions.topCrumb true
    @param defaultOptions.forceFitColumns true
    @param defaultOptions.autoHeight true
    @param defaultOptions.navigation true
    **/
    defaultOptions: {
        container: null,
        url: null,
        info: null,
        columns: [
            {id: "uid", name: "uid", width: 40, field: "uid"},
            {id: "name", name: "Name", field: "name", width: 450, cssClass: "cell-title", sortable: true, defaultSortAsc: true}
        ],
        editable: false,
        enableCellNavigation: false,
        asyncEditorLoading: false,
        enableColumnReorder: true,
        sortAsc: true,
        dragDrop: true,
        dropZone: true,
        dropZonePreviewsContainer: null,
        navLevel: "null",
        breadcrumbBox: null,
        largeGuide: true,
        clickUploadElement: true,
        topCrumb: true,
        forceFitColumns: true,
        autoHeight: true,
        navigation: true
    },

    Slick: {
    },

    /**
    Data for the HGrid

    @property data
    @type Array
    @default null
    **/
    data: null,
    /**
    Currently rendered rows

    @property currentlyRendered
    @type Array
    @default []
    **/
    currentlyRendered: [],
    /**
    Current indent shift

    @property currentIndentShift
    @type int
    @default 0
    **/
    currentIndentShift: 0,
    /**
    Dropzone Object

    @property dropZoneObj
    @type {Object}
    @default null
    **/
    dropZoneObj: null,

    /**
     * This function creates a new HGrid object and calls initialize()
     * @constructor
     * @method create
     *
     * @param {Object} options Data to be passed to grid
     *   @param {String} options.url Url to post to
     *   @param {Object} options.info Information dictionary
     *     @param options.info.parent_uid Parent unique ID
     *     @param options.info.uid Unique ID
     *     @param options.info.name Name
     *     @param {String} options.info.type Folder or file
     *   @param {String} options.container Div ID of container for HGrid
     * @return {HGrid} Returns a new HGrid object.
     */
    create: function(options) {
        var _this = this;
        var self = Object.create(_this);
        self.options = $.extend({}, self.defaultOptions, options);
        var urls = ['urlAdd','urlMove','urlEdit','urlDelete'];
        for (var i = 0; i<urls.length; i++) {
            if (!self.options[urls[i]]) {
                self.options[urls[i]] = self.options['url'];
            }
            if (typeof self.options[urls[i]] === "function") {
                self.options[urls[i]] = self.options[urls[i]]();
            }
        }
        self.initialize();
        $.extend(this, {

            hGridOnMouseEnter: new self.Slick.Event(),
            hGridOnMouseLeave: new self.Slick.Event(),
            hGridOnClick: new self.Slick.Event(),
            /**
             Fired before a move occurs

             @event hGridBeforeMove
             @param {Object} e Event object
             @param {Object} args
                @param args.rows Array of unique IDs of rows moving
                @param args.insertBefore Row ID of destination row to insert before
             **/
            hGridBeforeMove: new self.Slick.Event(),
            /**
             Fired after a move occurs

             @event hGridAfterMove
             @param {Object} e Event object
             @param {Object} args
                @param args.rows Array of unique IDs of rows moving
                @param args.insertBefore Row ID of destination row to insert before
             **/
            hGridAfterMove: new self.Slick.Event(),
            /**
             Fired before an edit occurs

             @event hGridBeforeEdit
             @param {Object} e Event object
             @param {Object} args
                @param args.item Item being changed
                @param args.name New name
             **/
            hGridBeforeEdit: new self.Slick.Event(),
            /**
             Fired after an edit occurs

             @event hGridAfterEdit
             @param {Object} e Event object
             @param {Object} args
                @param args.item Item being changed
                @param args.name New name
                @param args.success Boolean, whether or not the edit succeeded
             **/
            hGridAfterEdit: new self.Slick.Event(),
            /**
             Fired before a delete occurs

             @event hGridBeforeDelete
             @param {Object} e Event object
             @param {Object} args
                @param args.items Array of unique IDs to be deleted
             **/
            hGridBeforeDelete: new self.Slick.Event(),
            /**
             Fired after a delete occurs

             @event hGridAfterDelete
             @param {Object} e Event object
             @param {Object} args
                @param args.items Array of unique IDs to be deleted
                @param args.success Boolean, whether or not the delete succeeded
             **/
            hGridAfterDelete: new self.Slick.Event(),
            /**
             Fired before an add occurs

             @event hGridBeforeAdd
             @param {Object} e Event object
             @param {Object} args
                @param args.item Item to be added
                @param args.parent Parent item for new item
             **/
            hGridBeforeAdd: new self.Slick.Event(),
            /**
             Fired after an add occurs

             @event hGridAfterAdd
             @param {Object} e Event object
             @param {Object} args
                @param args.item Item to be added
                @param args.parent Parent item for new item
                @param args.success Boolean, whether or not the add succeeded
             **/
            hGridAfterAdd: new self.Slick.Event(),
            /**
             Fired before an upload occurs

             @event hGridBeforeUpload
             @param {Object} e Event object
             @param {Object} args
                @param args.item File object being added
                @param args.parent Parent item for new file
             **/
            hGridBeforeUpload: new self.Slick.Event(),
            /**
             Fired after an upload occurs

             @event hGridAfterUpload
             @param {Object} e Event object
             @param {Object} args
                @param args.item File object being added
                @param args.success Boolean, whether or not the upload succeeded
             **/
            hGridAfterUpload: new self.Slick.Event(),
            /**
             Fired on success response from server on upload

             @event hGridOnUpload
             @param {Object} e Event object
             @param {Object} args File object response
             **/
            hGridOnUpload: new self.Slick.Event(),
             /**
             Fired on success response from server on upload

             @event hGridAfterNav
             @param {Object} e Event object
             @param {Object} args nav level
             **/
            hGridAfterNav: new self.Slick.Event()
        });
        return self;
    },

    initialize: function() {
        var hGridContainer = this.options.container;
        var hGridInfo = this.options.info;
        var hGridColumns = this.options.columns;
        this.data = this.prep(hGridInfo);
        this.Slick = $.extend({}, Slick);
        this.Slick.dataView = new this.Slick.Data.DataView({ inlineFilters: true });
//        this.Slick.dataView = $.extend({}, Slick.Data.DataView({ inlineFilters: true }));
//        this.Slick.dataView = new Slick.Data.DataView({ inlineFilters: true });
        this.Slick.dataView.beginUpdate();
        this.Slick.dataView.setItems(this.data);
        var data = this.data;
        var dataView = this.Slick.dataView;
        this.Slick.dataView.setFilterArgs([data, this]);
        this.Slick.dataView.setFilter(this.myFilter);
        this.Slick.dataView.endUpdate();
        if(this.options.dragDrop){
            hGridColumns.unshift({id: "#", name: "", width: 40, behavior: "selectAndMove", selectable: false, resizable: false, cssClass: "cell-reorder dnd"});
        }
        this.Slick.grid = new this.Slick.Grid(hGridContainer, this.Slick.dataView, hGridColumns, this.options);

        var _this = this;
        $.each(this.options.columns, function(idx, elm) {
            if (elm['primary']==true && !elm.formatter){
                elm.formatter = _this.defaultTaskNameFormatter;
            }
        });
        if(this.options.columns===this.defaultOptions.columns) {
            this.options.columns[this.Slick.grid.getColumnIndex('name')].formatter = this.defaultTaskNameFormatter;
        }
        this.options.columns[this.Slick.grid.getColumnIndex('name')].validator = this.requiredFieldValidator;
        this.Slick.grid.invalidate();
        this.Slick.grid.render();
        if(this.options.topCrumb) {
            this.updateBreadcrumbsBox();
        }
        this.setupListeners();
        if(this.options.dropZone){
            this.dropZoneInit(this);
        }
        else{
            if(typeof Dropzone !== 'undefined'){
                Dropzone.autoDiscover = false;
            }
        }
    },

    defaultTaskNameFormatter: function(row, cell, value, columnDef, dataContext) {
        value = value.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
        var spacer = "<span style='display:inline-block;height:1px;width:" + (15 * dataContext["indent"]) + "px'></span>";
        if (dataContext['type']=='folder') {
            if (dataContext._collapsed) {
                return spacer + " <span class='toggle expand nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span><span class='folder'></span>&nbsp;" + value + "</a>";
            } else {
                return spacer + " <span class='toggle collapse nav-filter-item' data-hgrid-nav=" + dataContext['uid'] + "></span><span class='folder'></span>&nbsp;" + value + "</a>";
            }
        } else {
            return spacer + " <span class='toggle'></span><span class='file'></span>&nbsp;" + value;
        }
    },

    requiredFieldValidator: function (value) {
        if (value == null || value == undefined || !value.length) {
            return {valid: false, msg: "This is a required field"};
        } else {
            return {valid: true, msg: null};
        }
    },

    myFilter: function (item, args) {
        var data = args[0];
        var _this = args[1];
        if (_this.options.navLevel != "null") {
//            if (item["sortpath"].indexOf(_this.options.navLevel) != 0) {
            if ( item["sortpath"].indexOf(_this.options.navLevel) != 0 ) {
                return false;
            }
            if ( (item["sortpath"] != _this.options.navLevel) && (item.parent == null) ) {
                return false;
            }
            var navLevelChecker = _this.getItemByValue(data, _this.options.navLevel, 'sortpath')
            if ( (item['uid'] != navLevelChecker['uid']) && (item['parent_uid'] == navLevelChecker['parent_uid'])){
                return false;
            }
        }
        if (item.parent != null) {
            var parent = _this.getItemByValue(data, item.parent_uid, 'uid');
            while (parent) {
                if (parent._collapsed) {
                    return false;
                }
                parent = _this.getItemByValue(data, parent.parent_uid, 'uid');
            }

            item['indent'] = item['absoluteIndent'] - _this.currentIndentShift;
            _this.currentlyRendered.push(item);
            return true;
        } else {
            item['indent'] = item['absoluteIndent'] - _this.currentIndentShift;
            _this.currentlyRendered.push(item);
            return true;
        }
    },

    updateNav: function(){
        var _this = this;
        var nav = _this.options.navLevel;
        nav = nav.split("/");
        nav = nav.pop();
        this.navLevelFilter(nav);
    },

    navLevelFilter: function(itemUid) {
        var _this = this;
        var item = _this.getItemByValue(_this.data, itemUid, "uid");
        var navReset = _this.options.navLevel;
        _this.currentlyRendered = [];
        if (item && itemUid!=="") {
            _this.currentIndentShift = item['absoluteIndent'];
            try {
                if(!item["sortpath"]) throw "This item has no sort path";
                _this.options.navLevel = item["sortpath"];
            } catch(e) {
                console.error(e);
                console.log("This is not a valid item");
                _this.options.navLevel = navReset;
            }
        } else {
            _this.options.navLevel = "null";
            _this.currentIndentShift = 0;
            _this.Slick.grid.invalidate();
            _this.updateBreadcrumbsBox(itemUid);
            _this.Slick.dataView.setFilterArgs([_this.data, this])
            _this.Slick.dataView.setFilter(_this.myFilter);
            return;
        }

        _this.Slick.dataView.setFilterArgs([_this.data, this])
        _this.Slick.dataView.setFilter(_this.myFilter);
        _this.Slick.grid.invalidate();
        _this.updateBreadcrumbsBox(itemUid);
        _this.hGridAfterNav.notify(item);
    },

     /**
     * This function updates the breadcrumbs element on the page during navigation of directories
     * @method updateBreadcrumbsBox
     *
     * @param {String} itemUid uid of the new item to display as breadcrumbs parent
    */
    updateBreadcrumbsBox: function(itemUid) {
        var _this = this;
        var item = _this.getItemByValue(_this.data, itemUid, "uid");
        var bcb = _this.options.breadcrumbBox;
        $(bcb).addClass("breadcrumb");
        var spacer = " / ";
        var crumbs = [];
        $(bcb).empty();
        var levels = [];
        if (item && itemUid!=="" && itemUid!==false) {
            try {
                levels = item["path"].slice();
                if(!item["path"]) throw "This item has no path";
            } catch(e) {
                console.error(e);
                console.log("This is not a valid item");
                levels = [];
            }
        }
        if (_this.options.topCrumb){
            var topCrumb = '<span class="hgrid-breadcrumb"><a href="#" data-hgrid-nav="">' + "HGrid" + '</a></span>';
            crumbs.push(topCrumb);
        }
        for (var i = 0; i<levels.length; i++) {
            var crumb = '<span class="hgrid-breadcrumb"><a href="#" data-hgrid-nav="' + levels[i] + '">' + _this.getItemByValue(_this.data, levels[i], 'uid')['name'] + '</a></span>';
            crumbs.push(crumb);
        }
        for (var i = 0; i<crumbs.length; i++) {
            $(bcb).append(crumbs[i]);
            $(bcb).append(spacer);
        }
    },


    dropZoneInit: function (hGrid){// Turn off the discover option so the URL error is not thrown with custom configuration
        var Dropzone = window.Dropzone;
        Dropzone.autoDiscover = false;
        var url;
        var bool = false;
// Instantiate this Dropzone
        if(typeof hGrid.options['urlAdd'] === "string"){
            url = hGrid.options['urlAdd'];
        }
        else {
            url = hGrid.options['url'];
            bool = true;
        }
        var myDropzone = new Dropzone(hGrid.options.container, {
            url: url,
            clickable: hGrid.options.clickUploadElement,
            previewsContainer: hGrid.options.dropZonePreviewsContainer,
            addRemoveLinks: true,
            dropDestination: null
        } );

        hGrid.dropZoneObj = myDropzone;
// Get the SlickGrid Row under the dragged file
        myDropzone.on("dragover", function(e){
            currentDropCell = hGrid.Slick.grid.getCellFromEvent(e);
            if(currentDropCell===null){
                dropHighlight = null;
                myDropzone.options.dropDestination = null;
                hGrid.draggerGuide(dropHighlight);
            }
            else{
                currentDropCell.insertBefore = currentDropCell['row'];

                if(hGrid.Slick.dataView.getItem(currentDropCell['row'])['type']=='folder'){
                    dropHighlight = hGrid.Slick.dataView.getItem(currentDropCell['row']);
                    myDropzone.options.dropDestination = dropHighlight['uid'];
                }
                else{
                    var childDropHighlight = hGrid.Slick.dataView.getItem(currentDropCell['row']);
                    dropHighlight = hGrid.getItemByValue(hGrid.data, childDropHighlight['parent_uid'], 'uid');
                    myDropzone.options.dropDestination = dropHighlight['uid'];
                }
                if(dropHighlight['permission']=="true" || typeof dropHighlight['permission'] == 'undefined')
                    hGrid.draggerGuide(dropHighlight);
            }
            if(bool){
                myDropzone.options.url = hGrid.options['urlAdd'][myDropzone.options.dropDestination];
            }

        });

        myDropzone.on("addedfile", function(file){
            $('.bar').css('width', "0%");
            var parent;
            if (myDropzone.options.dropDestination===null){
                parent = hGrid.getItemByValue(hGrid.data, myDropzone.options.dropDestination, 'parent');
            }
            else{
                parent = hGrid.getItemByValue(hGrid.data, myDropzone.options.dropDestination, 'uid');
            }
            var value = {item: file, parent: parent};
            var promise = $.when(hGrid.hGridBeforeUpload.notify(value));
            promise.done(function(event_status){
                if(event_status===false){
                    myDropzone.removeFile(file);
                    value['success'] = false;
                    hGrid.updateNav();
                    hGrid.hGridAfterUpload.notify(value);
                }
            });
        });

        myDropzone.on("dragleave", function(e){
            hGrid.removeDraggerGuide();
        });
// Pass the destination folder to the server
        myDropzone.on("sending", function(file, xhr, formData){
            hGrid.updateNav();
            $('#totalProgressActive').addClass('active progress-striped progress');
            $('#totalProgress').addClass('progress-bar progress-bar-success');
            formData.append("destination", myDropzone.options.dropDestination);
        });

        myDropzone.on("uploadprogress", function(file, progress, bytesSent){
            var ins = "#" + file.name.replace(/[\s\.#\'\"]/g, '');
            $(ins).css('width', progress + "%");
        });

        myDropzone.on("totaluploadprogress", function(progress, totalBytes, totalBytesSent){
            $('#totalProgress').css('width', progress + "%");
            if (progress==100){
                setTimeout(function(){
                    $('#totalProgressActive').removeClass('active progress-striped progress');
                },(1*1000));
            }
        })
// Hook the drop success to the grid view update
        myDropzone.on("success", function(file) {
            var value;
            var promise = $.when(hGrid.hGridOnUpload.notify(file));
            promise.done(function(event_status){
                if (event_status || typeof(event_status)=='undefined'){
                    value = {item: JSON.parse(file.xhr.response)[0], success: true};
                    value['item']['name'] = file.name;
                    hGrid.updateNav();
                    hGrid.hGridAfterUpload.notify(value);
                }
                else{
                    value = {item: file, success: false};
                    hGrid.updateNav();
                    hGrid.hGridAfterUpload.notify(value);
                }
            });
        });
    },

    /**
     * Allows the user to add a new column to the grid
     * @method addColumn
     *
     * @param {Object} column New column to be added
     *  @param item.id ID of column
     *  @param item.name Name of column
     *  @param item.field Field of items to be put in the columns
     * @return {Boolean} True if setting columns works
     */
    addColumn: function(column) {
        var _this = this;
        var old_columns = _this.Slick.grid.getColumns();
        old_columns.push(column);
        _this.Slick.grid.setColumns(old_columns);
        return true;
    },

    /**
     * Allows the user to add a new item to the grid
     * @method addItem
     *
     * @param {Object} item New item to be added
     *  @param item.parent_uid Parent unique ID
     *  @param item.uid Unique ID
     *  @param item.name Name
     *  @param {String} item.type Folder or file
     * @return {Boolean}
     */
    addItem: function(item) {
        var _this = this;
//        if (!item['parent_uid'] || !item['uid'] || !item['name'] || !item['type'] || _this.getItemByValue(_this.data, item['uid'], 'uid')){
//            alert("This is an invalid item.")
//            return;
//        }
        var parent= _this.getItemByValue(_this.data, item['parent_uid'], 'uid');
        var value = {'item': item, 'parent':parent};
        var valueAfter = {'item': item, 'parent':parent};
        var promise = $.when(_this.hGridBeforeAdd.notify(value));
        promise.done(function(event_status){
            if(event_status || typeof(event_status)==='undefined'){
                if(item['parent_uid']!="null" && !item['uploadBar']){
                    var parent_path = parent['path'];
                    item['path']=[];
                    item['path']=item['path'].concat(parent_path, item['uid']);
                    item['sortpath']=item['path'].join('/');
                    if(!item['type']) item['type']='file';
                }
                var sortCol = _this.Slick.grid.getSortColumns()[0];
                var sortId = sortCol['columnId'];
                var asc = sortCol['sortAsc'];
                var spliceId = null;
                var searchData = _this.getItemsByValue(_this.data, parent['uid'], "parent_uid");

                if(searchData.length != 0){
                    var comp = null;
                    var compValue = null;
                    var itemValue = typeof(item[sortId]) == 'string' ? item[sortId].toLowerCase() : item[sortId];
                    itemValue = sortId == 'size' ? parseInt(itemValue) : itemValue;
                    for(var i=0; i<searchData.length; i++){
                        comp = searchData[i];
                        compValue = typeof(comp[sortId]) == 'string' ? comp[sortId].toLowerCase() : comp[sortId];
                        compValue = sortId == 'size' ? parseInt(compValue) : compValue;
                        spliceId = comp['id']+1;
                        if(asc){
                            if(compValue > itemValue){
                                spliceId = comp['id'];
                                break;
                            }
                        }
                        else{
                            if(compValue < itemValue){
                                spliceId = comp['id'];
                                break;
                            }
                        }
                    }
                }
                else{
                    spliceId = parent['id']+1;
                }

//            if(_this.data[parent['id']+1]){
//                var comp = _this.data[parent['id']+1];
//                var compValue = typeof(comp[sortCol]) == 'string' ? comp[sortCol].toLowerCase() : comp[sortCol];
//                var itemValue = typeof(item[sortCol]) == 'string' ? item[sortCol].toLowerCase() : item[sortCol];
//                while(compValue < itemValue && comp['indent']>parent['indent']){
//                    if(typeof(_this.data[comp['id']+1])==='undefined'){
//                        spliceId = comp['id']+1;
//                        break;
//                    }
//                    comp = _this.data[comp['id']+1];
//                    while(typeof(comp)!=='undefined' && comp['parent_uid']!=parent['uid']){
//                        comp = _this.data[comp['id']+1];
//                    }
//                    if(typeof(_this.data[comp['id']+1])==='undefined'){
//                        spliceId = comp['id']+1;
//                        break;
//                    }
//                    compValue = typeof(comp[sortCol]) == 'string' ? comp[sortCol].toLowerCase() : comp[sortCol];
//                    spliceId = comp['id'];
//                }
//            }
//            else{
//                spliceId = parent['id']+1;
//            }
                _this.data.splice(spliceId, 0,item);
                _this.prepJava(_this.data);
                _this.Slick.dataView.setItems(_this.data);
                _this.Slick.grid.setSelectedRows([]);
                _this.currentlyRendered=[];
                valueAfter['success'] = true;
                _this.hGridAfterAdd.notify(value);
                return true;
            }
            else{
                valueAfter['success'] = false;
                _this.updateNav();
                _this.hGridAfterAdd.notify(value);
                return false;
            }
        });
    },

    /**
     * Allows the user to add a new item to the grid
     * @method uploadItem
     *
     * @param {Object} item New item to be added
     *  @param item.parent_uid Parent unique ID
     *  @param item.uid Unique ID
     *  @param item.name Name
     *  @param {String} item.type Folder or file
     * @return {Boolean}
     */
    uploadItem: function(item) {
        var _this = this;
//        if (!item['parent_uid'] || !item['uid'] || !item['name'] || !item['type'] || _this.getItemByValue(_this.data, item['uid'], 'uid')){
//            alert("This is an invalid item.");
//            return;
//        }
        var parent= _this.getItemByValue(_this.data, item['parent_uid'], 'uid');
        if(item['parent_uid']!="null"){
            var parent_path = parent['path'].slice();
            parent_path.push(item['uid']);
            item['path'] = parent_path;
//                item['path'].concat(parent_path, item['uid']);
            item['sortpath']=item['path'].join('/');
        }
        _this.data.splice(parent['id']+1, 0,item);
        _this.prepJava(_this.data);
        _this.Slick.dataView.setItems(_this.data);
        _this.Slick.grid.invalidate();
        _this.Slick.grid.setSelectedRows([]);
        _this.currentlyRendered=[];
        _this.Slick.grid.render();
        return true;
    },

    hasChildren: function(itemUid) {
        var _this = this;
        if(_this.getItemByValue(_this.data, itemUid, "parent_uid")!=false)
            return true;
        return false;
    },

    /**
     * Allows the user to move items and all of their children to another place on the grid
     * @method moveItems
     *
     * @param {Array} src_uid Unique IDs of each item that should move
     * @param {int} dest Unique ID of the destination parent
     *
     * @return {Boolean}  True if success, false if failure
     */
    moveItems: function(src_uid, dest) {
        var _this = this;
        var src_id = [];
        var destination = _this.getItemByValue(_this.data, dest, 'uid');
        var dest_path = destination['path'];
        var url = _this.options.url;

        var value = {};
        value['rows']=[];
        for(var i=0; i<src_uid.length; i++){
            if ($.inArray(src_uid[i], dest_path)!=-1){
                return false;
            }
            value['rows'].push(src_uid[i]);
        }

        value['insertBefore']=destination['id']+1;
        var promise = $.when(_this.hGridBeforeMove.notify(value));
        promise.done(function(event_status){
            if(event_status || typeof(event_status)==='undefined'){
                if(_this.itemMover(value, url, src_id, dest_path)){
                    value['success']=true;
                    _this.updateNav();
                    _this.hGridAfterMove.notify(value);
                    return true;
                }
                else {
                    value['success']="There was an error with the grid";
                    _this.updateNav();
                    _this.hGridAfterMove.notify(value);
                    return false;
                }
            }
            else{
                value['success']=false;
                _this.updateNav();
                _this.hGridAfterMove.notify(value);
                return false;
            }
        });
    },

    /**
     * Allows the user to delete items and all of their children
     * @method deleteItems
     *
     * @param {Array} rowsToDelete Array of unique IDs of rows to delete
     * @return {Boolean}
     */
    deleteItems: function(rowsToDelete) {
        var _this = this;
        var value = {'items': []};
        var valueAfter = {'items':[]};
        for (var j=0; j<rowsToDelete.length; j++){
            value['items'].push(_this.getItemByValue(_this.data, rowsToDelete[j], 'uid'));
            valueAfter['items'].push(_this.getItemByValue(_this.data, rowsToDelete[j], 'uid'));
        }
        var promise = $.when(_this.hGridBeforeDelete.notify(value));
        promise.done(function(event_status) {
            if(event_status || typeof(event_status)==='undefined'){
                for(var i=0; i<rowsToDelete.length; i++){
                    var rows=[];
                    var check = _this.getItemByValue(_this.data, rowsToDelete[i], 'uid')['id'];
                    var j = check;
                    do{
                        rows.push(j);
                        j+=1;
                    }while(_this.data[j] && _this.data[j]['indent']>_this.data[check]['indent']);

                    _this.data.splice(rows[0], rows.length);
                    _this.Slick.dataView.setItems(_this.data);
                }
                _this.prepJava(_this.data);
                _this.Slick.dataView.setItems(_this.data);
                _this.Slick.grid.invalidate();
                _this.Slick.grid.setSelectedRows([]);
                _this.currentlyRendered=[];
                _this.Slick.grid.render();
                valueAfter['success']=true;
                _this.updateNav();
                _this.hGridAfterDelete.notify(valueAfter);
                return true;
            }
            else{
                valueAfter['success']=false;
                _this.updateNav();
                _this.hGridAfterDelete.notify(valueAfter);
                return false;
            }
        });
    },

    /**
     * Allows the user to edit the name of the item passed
     * @method editItem
     *
     * @param src_uid Unique ID of the item to change
     * @param {String} name New name for the item being changed
     *
     * @return {Boolean}
     */
    editItem: function(src_uid, name) {
        var _this = this;
        var src = _this.getItemByValue(_this.data, src_uid, 'uid');
        var value = {'item': src, 'name': name};
        var valueAfter = {'item': src, 'name': name};
        var promise = $.when(_this.hGridBeforeEdit.notify(value));
        promise.done(function(event_status){
            if(event_status || typeof(event_status)==='undefined'){
                src['name']=name;
                _this.Slick.dataView.updateItem(src['id'], src);
                valueAfter['success']=true;
                _this.hGridAfterEdit.notify(valueAfter);
                return true;
            }
            else{
                valueAfter['success']=false;
                _this.hGridAfterEdit.notify(valueAfter);
                return false;
            }
        });
    },

    /**
     * This function searches through the data and returns the first object with the correct value
     * @method getItemByValue
     *
     * @param {Array} data Dataset to loop through
     * @param {Object} searchVal Value to search for
     * @param {String} searchProp Property of target value
     *
     * @return {Object} Item with searchValue or false if not in dataset
    */
    getItemByValue: function(data, searchVal, searchProp) {
        var ans;
        for(var i =0; i<data.length; i++){
            if(data[i][searchProp]==searchVal){
                ans=data[i];
                return ans;
            }
        }
        return false;
    },

    /**
     * This function searches through the data and returns a list of objects with the correct value
     * @method getItemsByValue
     *
     * @param {Array} data Dataset to loop through
     * @param {Object} searchVal Value to search for
     * @param {String} searchProp Property of target value
     *
     * @return {Object} Array of items with searchValue
    */
    getItemsByValue: function(data, searchVal, searchProp) {
        var propArray = [];
        for(var i =0; i<data.length; i++){
            if(data[i][searchProp]==searchVal){
                propArray.push(data[i]);
            }
        }
        return propArray;
    },

    prep: function(info){
        var indent = 0;
        var checker = {};
        var i = 0;
        var data_counter=0;
        var output = [];
        var _this = this;
        while (info.length>=1){

            var d = info[i];
            if (info[i]['parent_uid']=="null"){
                d['parent']=null;
                d['indent']=0;
                d['id']=data_counter;
                checker[d['uid']]=[d['indent'], data_counter];
                output[data_counter]=d;
                data_counter++;
                info.splice(i, 1);
            }
            else if(info[i]['parent_uid'] in checker){
                d['parent']=checker[d['parent_uid']][1];
                d['indent']=checker[d['parent_uid']][0]+1;
                d['id']=data_counter;
                checker[d['uid']]=[d['indent'], data_counter];
                output[data_counter]=d;
                data_counter++;
                info.splice(i, 1);
            }
            else{
                i++;
            }
            if(i>=info.length){
                i=0;
            }
            if(d['name']=="null"){
                d['name']+=i;
            }
        }

        for(var l=0; l<output.length; l++){
            var path = [];
            var namePath = [];
            path.push(output[l]['uid']);
            if(output[l]['parent_uid']!="null"){
                for(var m=0; m<l; m++){
                    if(output[m]['uid']==output[l]['parent_uid']){
//                        var x = m;
                        while(output[m]['parent_uid']!="null"){
                            path.push(output[m]['uid']);
                            m = output[m]['parent'];
                        }
                        path.push(output[m]['uid']);
                        break;
                    }
                }
            }
            path.reverse();
            output[l]['path']=path;
            output[l]['sortpath']=path.join('/');
        }
        var sortingCol='sortpath';
        output.sort(function(a, b){
            var x = a[sortingCol].toLowerCase(), y = b[sortingCol].toLowerCase();

            if(x == y){
                return 0;
            }
            if(_this.options.sortAsc){
                return x > y ? 1 : -1;
            }
            else{
                return x < y ? 1 : -1;
            }
        });
        return this.prepJava(output);
    },

    prepJava: function(sortedData, options) {
        var _this = this;
        var settings = {
            sorting: false,
        };

        settings = $.extend(settings, options);


        var output = [];
        var checker = {};
        var indent = 0;
        for (var i = 0; i < sortedData.length; i++) {
            var parent;
            var d = {};
            var path = [];

            //Assign parent paths, find ID of parent and assign its ID to "parent" attribute
            d['parent_uid']=sortedData[i]['parent_uid'];
            path.push(sortedData[i]['uid']);
            //Check if item has a parent
            if (sortedData[i]['parent_uid']!="null"){
                for(var j=0; j<sortedData.length; j++){
                    if (sortedData[j]['uid']==d['parent_uid'] && !d["parent"]){
                        d["parent"]= j;
                        break;
                    }
                }
                //If parent hasn't been encountered, increment the indent
                if (!(sortedData[i]['parent_uid'] in checker)){
                    indent++;
                }
                //If it has been encountered, make indent the same as others with same parent
                else {
                    indent = checker[sortedData[i]['parent_uid']];
                }
                //Make sure parent_uid is in checker
                checker[sortedData[i]['parent_uid']]=indent;
            }
            //If no parent, set parent to null and indent to 0
            else {
                indent=0;
                d["parent"]=null;
            }
            if (sortedData[i]._collapsed){
                d._collapsed=sortedData[i]._collapsed;
            }
            //Set other values
            d["id"] = i;
            if (!settings['sorting']){
                d["indent"] = indent;
                d["absoluteIndent"] = indent;
            }
            d = $.extend(true, sortedData[i], d);
            output[i]=d;
        }
        return output;
    },

    itemMover: function (args, url, src, dest){
        this.removeDraggerGuide();
//        $.post(url, {src: JSON.stringify(src), dest: JSON.stringify(dest)}, function(response){
//            //Make sure move succeeds
//            if (response=="fail"){
//                alert("Move failed!");
//                return false;
//            }
//            else{

        for(var y=0; y<args.rows.length; y++){
            var rows=[];
            //Make sure all children move as well
            var item = this.getItemByValue(this.data, args.rows[y], 'uid');
            var j = item['id'];
            var stopRow;
            do{
                rows.push(j);
                j+=1;
                stopRow = j;
            }while(this.data[j] && this.data[j]['indent']>item['indent']);

            //Update data
            var extractedRows = [], left, right;

            var insertBefore = this.Slick.grid.getDataItem(args.insertBefore)['id'];


            left = this.data.slice(0, insertBefore);
            right = this.data.slice(insertBefore, this.data.length);

            rows.sort(function(a,b) { return a-b; });

            for (var i = 0; i < rows.length; i++) {
                extractedRows.push(this.data[rows[i]]);
            }

            rows.reverse();

            for (var i = 0; i < rows.length; i++) {
                var row = rows[i];
                if (row < insertBefore) {
                    left.splice(row, 1);
                } else {
                    right.splice(row - insertBefore, 1);
                }
            }

//                    Change parent uid and uid

            var checker = {};
            var old_path = extractedRows[0]['path'];

            if (dest==null){
                extractedRows[0]['path'] = [extractedRows[0]['uid']];
                extractedRows[0]['parent_uid']="null";
                extractedRows[0]['sortpath']=extractedRows[0]['path'].join('/');
            }
            else{
                extractedRows[0]['parent_uid']=dest[dest.length-1];
                extractedRows[0]['path'] = dest.slice();
                extractedRows[0]['path'].push(extractedRows[0]['uid']);
                extractedRows[0]['sortpath']=extractedRows[0]['path'].join('/');
            }


            var new_path = extractedRows[0]['uid'];
            checker[old_path]=new_path;

            if (extractedRows.length > 1){
                for(var m=1; m<extractedRows.length; m++){
                    var par = this.getItemByValue(extractedRows, extractedRows[m]['parent_uid'], 'uid')['path'];
                    extractedRows[m]['path']= par.slice();
                    extractedRows[m]['path'].push(extractedRows[m]['uid']);
                    extractedRows[m]['sortpath']=extractedRows[m]['path'].join('/');
                }
            }

            this.data = left.concat(extractedRows.concat(right));

            var selectedRows = [];
            for (var i = 0; i < rows.length; i++){
                selectedRows.push(left.length + i);
            }

            var new_data = this.prepJava(this.data);
            this.data = new_data;
        }
        this.Slick.dataView.setItems(this.data);
        this.Slick.grid.invalidate();
        this.Slick.grid.setSelectedRows([]);
        this.currentlyRendered=[];
        this.Slick.grid.render();
        return true;
    },

    removeDraggerGuide: function() {
        var _this = this;
        $(_this.options.container).find(".dragger-guide").removeClass("dragger-guide");
        $(_this.options.container).find(".slick-viewport").removeClass("dragger-guide1");
    },

    draggerGuide: function(inserter) {
        var _this = this;
        _this.removeDraggerGuide();
        var dragParent=false;
        // If a target row exists
        if(inserter==null){
            if(_this.options.largeGuide){
                $(_this.options.container).find(".slick-viewport").addClass("dragger-guide1");
            }
        }
        else{
            if (inserter['uid']!="uploads"){
                if(inserter['type']=='folder'){
                    dragParent = _this.Slick.grid.getCellNode(_this.Slick.dataView.getRowById(inserter['id']), 0).parentNode;
                }
                else{
                    try{
                        dragParent = _this.Slick.grid.getCellNode(_this.Slick.dataView.getRowById(inserter['parent']), 0).parentNode;
                    }
                    catch(err){
                    }
                }
            }
            if(dragParent){
                $(dragParent).addClass("dragger-guide");
            }
        }
    },

    //Function called when sort is clicked
    onSort: function (e, args, grid, dataView, data){
        var _this = this;
        _this.options.sortAsc = !_this.options.sortAsc;
        var sortingCol = args.sortCol.field;
        var sorted = _this.sortHierarchy(data, sortingCol, dataView, grid);
        var new_data = _this.prepJava(sorted, {'sorting': true});
        _this.data = new_data;
        dataView.setItems(new_data);
        _this.currentlyRendered=[];
        _this.updateNav();
    },

    compare: function(a, b) {
        var _this = this;
        if (a instanceof Array && b instanceof Array) {
            for (var r, i=0, l=Math.min(a.length, b.length); i<l; i++)
                if (r = _this.compare(a[i], b[i]))
                    return r;
            return a.length - b.length;
        } else // use native comparison algorithm, including ToPrimitive conversion
            return (a > b) - (a < b);
    },

    sortHierarchy: function (data, sortingCol, dataView, grid){
        var _this = this;
        var sorted = data.sort(function(a, b){
            var x = a[sortingCol], y = b[sortingCol];
            if(_this.options.sortAsc){
                return _this.compare(x,y);
            }
            else{
                return -(_this.compare(x,y));
            }
        });
        var hierarchical = [];
        this.buildHierarchy(sorted, hierarchical, undefined);
        return hierarchical;
    },

    buildHierarchy: function (sorted, hierarchical, parent) {
        for(var i=0; i < sorted.length; i++)
        {
            var item = sorted[i];
            var parentId;
            if(parent){
                parentId = parent.id;
            }
            else{
                parentId = undefined;
            }
            if(item.parent == parentId){
                hierarchical.push(item);
                if (item['type'] == 'folder') {
                    this.buildHierarchy(sorted, hierarchical, item);
                }
            }
        }
    },

    setupListeners: function(){
        var _this = this;
        var grid = this.Slick.grid;
        var data = this.data;
        var dataView = this.Slick.dataView;
        var src = [];
        var dest = "";
        grid.setSelectionModel(new Slick.RowSelectionModel());
        var moveRowsPlugin = new Slick.RowMoveManager({
            cancelEditOnDrag: true
        });

        //Before rows are moved, make sure their dest is valid, document source and target
        _this.Slick.grid.onMouseEnter.subscribe(function(e, args){
            args['e'] = e;
            _this.hGridOnMouseEnter.notify(args);
        });

        _this.Slick.grid.onMouseLeave.subscribe(function(e, args){
            args['e'] = e;
            _this.hGridOnMouseLeave.notify(args);
        });

        moveRowsPlugin.onBeforeMoveRows.subscribe(function (e, args) {
            src = [];
            dest = "";
            var inserter=null;
            if (grid.getDataItem(args.insertBefore-1)){
                if(args.insertBefore==args.rows[0]+1){
                    inserter = grid.getDataItem(args.insertBefore-2);
                }
                else{
                    inserter = grid.getDataItem(args.insertBefore-1);
                }
            }
            try{
                var insertBefore = grid.getDataItem(args.insertBefore)['id'];
            }
            catch(error){
                if(error.name == TypeError){
                    return false;
                }
            }

            if(inserter!=null){
                if(inserter['type']=='folder'){
                    dest = inserter['path'];
                }
                else{
                    dest = _this.getItemByValue(data, inserter['parent_uid'], 'uid');
                    dest = dest['path'];
                }
            }
            else{
                if (_this.options.navLevel == "null") {
                    dest = null;
                } else {
                    dest = _this.getItemByValue(data, _this.options.navLevel, 'sortpath');
                    if (dest['parent_uid'] == "null") {
                        dest = null
                    } else {
                        dest = _this.getItemByValue(data, dest['parent_uid'], 'uid')['path'];
                    }
//                    dest = dest['path'].slice();
                }
            }

            for (var i = 0; i < args.rows.length; i++) {
                src[i]=_this.getItemByValue(_this.data, _this.Slick.dataView.getItem(args.rows[i])['id'], 'id')['path'];
//                src[i]=args.rows[i];
                if (dest==""){
                    dest = null;
                }
                var index = true;

                if (dest!=null){
                    if (dest.indexOf(src[i][src[i].length-1]) != -1 || dest=="catch" || dest.indexOf("uploads") == 0){
                        index = false;
                    }
                }
                else{
                    inserter=null;
                }
                _this.draggerGuide(inserter);
                if (args.rows[i] == insertBefore - 1 || index == false || src[i] == "uploads" || dest == "uploads") {
                    _this.removeDraggerGuide();
                    return false;
                }
            }
            return true;
        });

//        When rows are moved post to server and update data
        moveRowsPlugin.onMoveRows.subscribe(function(e, args){
            var src_id = [];
            for(var i=0; i<src.length; i++){
                src_id.push(src[i][src[i].length-1]);
            }

            var value = {};
            value['rows']=[];
            for(var j=0; j<src_id.length; j++){
                value['rows'].push(src_id[j]);
            }
            value['insertBefore']=args['insertBefore'];
            var promise = $.when(_this.hGridBeforeMove.notify(value));
            promise.done(function(event_status){
                if(event_status || typeof(event_status)==='undefined'){
                    _this.itemMover(value, "/sg_move", src, dest);
                    value['success']=true;
                    _this.updateNav();
                    _this.hGridAfterMove.notify(value);
                }
                else {
                    _this.removeDraggerGuide();
                    alert("Move failed");
                    value['success']=false;
                    _this.updateNav();
                    _this.hGridAfterMove.notify(value);
                }
            });
        });

        grid.registerPlugin(moveRowsPlugin);

        //Update the item when edited
        grid.onCellChange.subscribe(function (e, args) {
            _this.options.editable=false;
            var src=args.item;
            _this.Slick.dataView.updateItem(src.id, src);
//            $.post('/sg_edit', {grid_item: JSON.stringify(src)}, function(new_title){
//                if(new_title!="fail"){
//                }
//                else{
//                    src['name']=src['uid'];
//                    alert("You can't change the uploads folder!");
//                    dataView.updateItem(src.id, src);
//                }
//            });
        });

        grid.onClick.subscribe(function (e, args) {
            _this.hGridOnClick.notify({e: e, args: args});
            if ($(e.target).hasClass("toggle") || $(e.target).hasClass("folder")) {
                var item = dataView.getItem(args.row);
                if (item) {
                    var i=args.row;
                    var counter = -1;
                    do{
                        counter+=1;
                        i+=1;
                    }
                    while(data[i] && data[i]['indent']>data[args.row]['indent']);
                    _this.currentlyRendered = [];
                    if (!item._collapsed) {
                        item._collapsed = true;
                    } else {
                        item._collapsed = false;
                        counter=-counter;
                    }

                    dataView.updateItem(item.id, item);
                }
                e.stopImmediatePropagation();
            }
            grid.getOptions().editable=false;
        });

        //If amount of rows are changed, update and render
        dataView.onRowCountChanged.subscribe(function (e, args) {
            grid.updateRowCount();
            grid.currentlyRendered = [];
            grid.render();
        });

        //When rows are edited, re-render
        dataView.onRowsChanged.subscribe(function (e, args) {
            grid.invalidateRows(args.rows);
            grid.currentlyRendered = [];
            grid.render();
        });

        //When columns are dragged around, make columns new order
        grid.onColumnsReordered.subscribe(function(e, args){
            grid.invalidate();
            _this.options.columns=args.cols;
            grid.currentlyRendered = [];
            grid.render();
        });

        //When sort is clicked, call sort function
        grid.onSort.subscribe(function (e, args) {
            _this.onSort(e, args, grid, _this.Slick.dataView, _this.data);
        });


        grid.onDblClick.subscribe(function (e, args) {
            var navId = $(e.target).find('span.nav-filter-item').attr('data-hgrid-nav');
            var item = _this.getItemByValue(_this.data, navId, "uid");
            if(navId && _this.options.navigation){
                _this.navLevelFilter(navId);
                if(_this.dropZoneObj!=null){
                    _this.dropZoneObj.options.url = item['uploadUrl'];
                    _this.dropZoneObj.options.dropDestination = item['uid'];
                }
            }
            e.preventDefault();
        });

        // When a Breadcrumb is clicked, the grid filters
        $(_this.options.breadcrumbBox).on("click", ".hgrid-breadcrumb>a", function(e) {
            var navId = $(this).attr('data-hgrid-nav');
            var item = _this.getItemByValue(_this.data, navId, "uid");
            if(_this.dropZoneObj!=null){
                _this.dropZoneObj.options.url = item['uploadUrl'];
                _this.dropZoneObj.options.dropDestination = item['uid'];
            }
            _this.navLevelFilter(navId);
            e.preventDefault();

        });
        // When an HGrid item is clicked, the grid filters
        $(_this.options.container).on("click", ".nav-filter-item", function(e) {
            var navId = $(this).attr('data-hgrid-nav');
            _this.navLevelFilter(navId);
            e.preventDefault();
        });

    }
};

