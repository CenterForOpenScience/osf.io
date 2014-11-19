;
(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils', 'treebeard', 'bootstrap', 'hgrid-draggable',
            'typeahead', 'handlebars'], factory);
    } else if (typeof $script === 'function') {
        global.ProjectOrganizer = factory(jQuery, global.Treebeard, global.ko);
        $script.done('projectorganizer');
    } else {
        global.ProjectOrganizer = factory(jQuery, global.Treebeard, global.ko);
    }
}(this, function ($, Treebeard, ko) {

    var projectOrganizer = {}; 

    projectOrganizer.publicProjects = new Bloodhound({
        datumTokenizer: function (d) {
            return Bloodhound.tokenizers.whitespace(d.name);
        },
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: '/api/v1/search/projects/?term=%QUERY&maxResults=20&includePublic=yes&includeContributed=no',
            filter: function (projects) {
                return $.map(projects, function (project) {
                    return {
                        name: project.value,
                        node_id: project.id,
                        category: project.category
                    };
                });
            },
            limit: 10
        }
    });

    projectOrganizer.myProjects = new Bloodhound({
        datumTokenizer: function (d) {
            return Bloodhound.tokenizers.whitespace(d.name);
        },
        queryTokenizer: Bloodhound.tokenizers.whitespace,
        remote: {
            url: '/api/v1/search/projects/?term=%QUERY&maxResults=20&includePublic=no&includeContributed=yes',
            filter: function (projects) {
                return $.map(projects, function (project) {
                    return {
                        name: project.value,
                        node_id: project.id,
                        category: project.category
                    };
                });
            },
            limit: 10
        }
    });


    function _poTitleColumn (item) {
        return m('span', item.data.name);
    }

    function _gotoEvent (event, item, col) {
        event.stopPropagation();
        window.location = item.data.urls.fetch;
    }


    function createProjectDetailHTMLFromTemplate(theItem) {
        var detailTemplateSource = $('#project-detail-template').html();
        Handlebars.registerHelper('commalist', function (items, options) {
            var out = '';

            for (var i = 0, l = items.length; i < l; i++) {
                out = out + options.fn(items[i]) + (i !== (l - 1) ? ', ' : '');
            }
            return out;
        });
        var detailTemplate = Handlebars.compile(detailTemplateSource);
        var detailTemplateContext = {
            theItem: theItem,
            multipleContributors: theItem.contributors.length > 1,
            parentIsSmartFolder: theItem.parentIsSmartFolder
        };
        var displayHTML = detailTemplate(detailTemplateContext);
        $('.project-details').html(displayHTML);
       addFormKeyBindings(theItem.node_id);

    }

    function addFormKeyBindings(nodeID){
        $('#ptd-'+nodeID).keyup(function (e){
            /*if(e.which == 13){ //return
                // Find visible submit-button in this div and activate it
                $('#ptd-'+nodeID).find('.submit-button-'+nodeID).filter(':visible').click();
                return false;
            } else*/ if (e.which === 27) {//esc
                // Find visible cancel-button in this div and activate it
                $('#ptd-'+nodeID).find('.cancel-button-'+nodeID).filter(':visible').click();
                return false;
            }
        });
    }

    function setItemToExpand(item, callback) {
        var expandUrl = item.apiURL + 'expand/';
        var postAction = $.osf.postJSON(expandUrl,{});
        postAction.done(function() {
            item.expand = false;
            if (typeof callback !== 'undefined') {
                callback();
            }
        }).fail($.osf.handleJSONError);
    }

    function _showProjectDetails (event, item, col) {
        var treebeard = this; 
        projectOrganizer.myProjects.initialize();
        projectOrganizer.publicProjects.initialize();
        // injecting error into search results from https://github.com/twitter/typeahead.js/issues/747

        var mySourceWithEmptySelectable = function(q, cb) {
          var emptyMyProjects = [{ error: 'There are no matching projects to which you contribute.' }];
          projectOrganizer.myProjects.get(q, injectEmptySelectable);

          function injectEmptySelectable(suggestions) {
            if (suggestions.length === 0) {
              cb(emptyMyProjects);
            }

            else {
              cb(suggestions);
            }
          }
        };

        var publicSourceWithEmptySelectable = function(q, cb) {
          var emptyPublicProjects = { error: 'There are no matching public projects.' };
          projectOrganizer.publicProjects.get(q, injectEmptySelectable);

          function injectEmptySelectable(suggestions) {
            if (suggestions.length === 0) {
              cb([emptyPublicProjects]);
            }

            else {
              cb(suggestions);
            }
          }

        };

        var linkName;
        var linkID;
        var theItem = item.data;

        var theParentNode = item.parent();
        if (typeof theParentNode === 'undefined') {
            theParentNode = theItem;
            theItem.parentIsSmartFolder = true;
        }
        theItem.parentNode = theParentNode.data;

            var theParentNodeID = theParentNode.node_id;
            theItem.parentIsSmartFolder = theParentNode.isSmartFolder;
            theItem.parentNodeID = theParentNodeID;


        if (!theItem.isSmartFolder) {
            createProjectDetailHTMLFromTemplate(theItem);
            $('#findNode' + theItem.node_id).hide();
            $('#findNode' + theItem.node_id + ' .typeahead').typeahead({
                    highlight: true
                },
                {
                    name: 'my-projects',
                    displayKey: function (data) {
                        return data.name;
                    },
                    source: mySourceWithEmptySelectable,
                    templates: {
                        header: function () {
                            return '<h3 class="category">My Projects</h3>'
                        },
                        suggestion: function (data) {
                            if(typeof data.name !== 'undefined') {
                                return '<p>' + data.name + '</p>';
                            } else {
                                return '<p>' + data.error + '</p>';
                            }
                        }
                    }
                },
                {
                    name: 'public-projects',
                    displayKey: function (data) {
                        return data.name;
                    },
                    source: publicSourceWithEmptySelectable,
                    templates: {
                        header: function () {
                            return '<h3 class="category">Public Projects</h3>'
                        },
                        suggestion: function (data) {
                            if(typeof data.name !== 'undefined') {
                                return '<p>' + data.name + '</p>';
                            } else {
                                return '<p>' + data.error + '</p>';
                            }
                        }
                    }
                });


            $('#input' + theItem.node_id).bind('keyup', function (event) {
                var key = event.keyCode || event.which;
                var buttonEnabled = (typeof $('#add-link-' + theItem.node_id).prop('disabled') !== 'undefined');

                if (key === 13) {
                    if (buttonEnabled) {
                        $('#add-link-' + theItem.node_id).click(); //submits if the control is active
                    }
                }
                else {
                    $('#add-link-warn-' + theItem.node_id).text('');
                    $('#add-link-' + theItem.node_id).attr('disabled', 'disabled');
                    linkName = '';
                    linkID = '';
                }
            });
            $('#input' + theItem.node_id).bind('typeahead:selected', function (obj, datum, name) {
                var getChildrenURL = theItem.apiURL + 'get_folder_pointers/';
                var children;
                $.getJSON(getChildrenURL, function (data) {
                    children = data;
                    if (children.indexOf(datum.node_id) === -1) {
                        $('#add-link-' + theItem.node_id).removeAttr('disabled');
                        linkName = datum.name;
                        linkID = datum.node_id;
                    } else {
                        $('#add-link-warn-' + theItem.node_id).text('This project is already in the folder')
                    }
                }).fail($.osf.handleJSONError);

            });
            $('#close-' + theItem.node_id).click(function () {
                $('.project-details').hide();
                return false;
            });
            $('#add-link-' + theItem.node_id).click(function () {
                var url = '/api/v1/pointer/';
                var postData = JSON.stringify(
                    {
                        pointerID: linkID,
                        toNodeID: theItem.node_id
                    });
                setItemToExpand(theItem, function() {
                    var tb = treebeard; 
                    var postAction = $.ajax({
                        type: 'POST',
                        url: url,
                        data: postData,
                        contentType: 'application/json',
                        dataType: 'json'
                    });
                    postAction.done(function () {
                        tb.updateFolder(null, item);
                    });
                });
                return false;
            });

            $('#remove-link-' + theItem.node_id).click(function () {
                var url = '/api/v1/folder/' + theParentNodeID + '/pointer/' + theItem.node_id;
                var deleteAction = $.ajax({
                    type: 'DELETE',
                    url: url,
                    contentType: 'application/json',
                    dataType: 'json'
                });
                deleteAction.done(function () {
                        treebeard.updateFolder(null, theParentNode);
                });
            });
            $('#delete-folder-' + theItem.node_id).click(function () {
                bootbox.confirm({
                    title: 'Delete this folder?',
                    message: 'Are you sure you want to delete this folder? This will also delete any folders ' +
                        'inside this one. You will not delete any projects in this folder.',
                    callback: function(result) {
                        if (result !== null && result) {
                            var url = '/api/v1/folder/'+ theItem.node_id;
                            var deleteAction = $.ajax({
                                type: 'DELETE',
                                url: url,
                                contentType: 'application/json',
                                dataType: 'json'
                            });
                            deleteAction.done(function () {
                                treebeard.updateFolder(null, item.parent());
                                $('.project-details').hide();
                            });
                        }
                    }
                });
            });
            $('#add-folder-' + theItem.node_id).click(function () {
                $('#buttons' + theItem.node_id).hide();
                $('#rnc-' + theItem.node_id).hide();
                $('#findNode' + theItem.node_id).hide();
                $('#afc-' + theItem.node_id).show();
            });
            $('#add-folder-input' + theItem.node_id).bind('keyup', function () {
                var contents = $.trim($(this).val());
                if (contents === '') {
                    $('#add-folder-button' + theItem.node_id).attr('disabled', 'disabled');
                } else {
                    $('#add-folder-button' + theItem.node_id).removeAttr('disabled');
                }
            });

            $('#add-folder-button' + theItem.node_id).click(function () {
                var url = '/api/v1/folder/';
                var postData = {
                    node_id: theItem.node_id,
                    title: $.trim($('#add-folder-input' + theItem.node_id).val())
                };
                setItemToExpand(theItem, function() {
                    var putAction = $.osf.putJSON(url, postData);
                    putAction.done(function () {
                        treebeard.updateFolder(null, item);
                        $('.project-details').hide();
                    }).fail($.osf.handleJSONError);

                });
                return false;
            });
            $('#rename-node-' + theItem.node_id).click(function () {
                $('#buttons' + theItem.node_id).hide();
                $('#afc-' + theItem.node_id).hide();
                $('#findNode' + theItem.node_id).hide();
                $('#nc-' + theItem.node_id).hide();
                $('#rnc-' + theItem.node_id).show();
            });
            $('#rename-node-input' + theItem.node_id).bind('keyup', function () {
                var contents = $.trim($(this).val());
                if (contents === '' || contents === theItem.name) {
                    $('#rename-node-button' + theItem.node_id).attr('disabled', 'disabled');
                } else {
                    $('#rename-node-button' + theItem.node_id).removeAttr('disabled');
                }
            });

            $('#rename-node-button' + theItem.node_id).click(function () {
                var url = theItem.apiURL + 'edit/';
                var postData = {
                    name: 'title',
                    value: $.trim($('#rename-node-input' + theItem.node_id).val())
                };
                var postAction = $.osf.postJSON(url, postData);
                postAction.done(function () {
                        treebeard.updateFolder(null, theParentNode);
                        $('.project-details').hide();
                    }).fail($.osf.handleJSONError);
                return false;
            });
            $('.cancel-button-' + theItem.node_id).click(function() {
                $('#afc-' + theItem.node_id).hide();
                $('#rnc-' + theItem.node_id).hide();
                $('#findNode' + theItem.node_id).hide();
                $('#nc-' + theItem.node_id).show();
                $('#buttons' + theItem.node_id).show();

            });

            $('#add-item-' + theItem.node_id).click(function () {
                $('#buttons' + theItem.node_id).hide();
                $('#afc-' + theItem.node_id).hide();
                $('#rnc-' + theItem.node_id).hide();
                $('#findNode' + theItem.node_id).show();
            });

            $('.project-details').toggle();
        } else {
            $('.project-details').hide();
        }
    }

    function _poActionColumn (item, col) {
        var self = this; 
        var buttons = [];
        var url = item.data.urls.fetch;
        if (!item.data.isSmartFolder) {
           
            buttons.push({ 
                'name' : '',
                'icon' : 'icon-info',
                'css' : 'project-organizer-iconinfo fangorn-clickable btn btn-default btn-xs',
                'onclick' : _showProjectDetails
            });

            
            if (url !== null) {
                buttons.push({
                    'name' : '',    
                    'icon' : 'icon-chevron-right',
                    'css' : 'project-organizer-icon-visit fangorn-clickable btn btn-info btn-xs',
                    'onclick' : _gotoEvent
                });
            }
        }    

        // Build the template for icons
        return buttons.map(function(btn){ 
            return m('span', { 'data-col' : item.id }, [ m('i', 
                { 'class' : btn.css, style : btn.style, 'onclick' : function(){ btn.onclick.call(self, event, item, col); } },
                [ m('span', { 'class' : btn.icon}, btn.name) ])
            ]);
        }); 
    }

    function _poContributors (item) {
        if(!item.data.contributors){
            return '';
        }
        return item.data.contributors.map(function(person){
            return m('span',person.name);
        });
    }

    function _poModified (item) {

        if (item.data.modifiedDelta === 0) {
            return m('span');
        }
        var dateString = moment.utc(item.data.dateModified).fromNow();
        if (item.data.modifiedBy !== '') {
            personString = item.data.modifiedBy.toString();
        }

        return m('span', dateString + ', by ' + personString );
    }

    function _poResolveRows(item){
        // this = treebeard;
        var css = '',
            draggable = item.data.permissions.movable || item.data.permissions.copyable;
        if(draggable) {
            css = 'po-draggable'; 
        } 
        item.css = '';
        var default_columns = [{
            data : 'name',  // Data field name
            folderIcons : true,
            filter : true,
            css : css,
            custom : _poTitleColumn
        },{
            sortInclude : false,
            custom : _poActionColumn
        },{
            filter : true,
            custom : _poContributors
        },{
            filter : false,
            custom : _poModified
        }];

        
        return default_columns;
    }

    function _poColumnTitles () {
        var columns = [];
        columns.push({
                title: 'Name',
                width : '40%',
                sort : true,
                sortType : 'text'
            },
            {
                title : 'Actions',
                width : '15%',
                sort : false
            }, 
            {
                title : 'Contributors',
                width : '20%',
                sort : false
            }, 
            {
                title : 'Modified',
                width : '25%',
                sort : false
            });
        return columns;  
    } 

    function _poToggleCheck (item) {
        if (item.data.permissions.view) {
            return true;
        }
        item.notify.update('Not allowed: Private folder', 'warning', 1, undefined);
        return false;
    }

    // function _poMouseOverRow (item, event) {
    //     $('.fg-hover-hide').hide(); 
    //         $(event.target).closest('.tb-row').find('.fg-hover-hide').show();
    // }

    function _poResolveIcon(item){
        var folder = m('img', { src : '/static/img/hgrid/folder.png' }),
            smartFolder = m('img', {src : '/static/img/hgrid/smart-folder.png'}),
            project = m('img', {src : '/static/img/hgrid/project.png'}),
            registration = m('img', {src : '/static/img/hgrid/reg-project.png'}),
            component = m('img', {src : '/static/img/hgrid/component.png'}),
            registeredComponent = m('img', {src : '/static/img/hgrid/reg-component.png'}),
            link = m('img', {src : '/static/img/hgrid/pointer.png'});

        if (item.data.isFolder) {
            return folder;
        }
        if(item.data.isSmartFolder) {
            return smartFolder;
        } 
        if(item.data.isProject) {
            return project;
        }
        if(item.data.isRegistration) {
            return registration;
        }
        if(item.data.isComponent) {
            return component;
        }
        if(item.data.isRegistration && item.data.isComponent) {
            return registeredComponent;
        }
        if (item.data.isPointer) {
            return link;
        }
        return folder; 
    }

    function _poResolveToggle(item){
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

    function _poResolveLazyLoad(tree, item){
        console.log("tree", item);
        return '/api/v1/dashboard/' + item.data.node_id;
    }

    function _poLoadOpenChildren () {
        var tb = this;
        this.treeData.children.map(function(item){
            item.data.expand = true; 
            if (item.data.expand) {
                $.ajax({
                    url : '/api/v1/dashboard/' + item.data.node_id
                }).done(function(result){
                    console.log(result);
                    result.data.map(function(rItem){
                        item.add(tb.buildTree(rItem, item));                        
                    });
                    tb.redraw();
                    tb.moveOn();

                });
            }
        }); 

    }

    function _poMultiselect (event, tree) {
            var selectedRows = filterRowsNotInParent.call(this, this.multiselected);
            console.log("SelectedRows", selectedRows);
            var multipleItems = false;

            if(selectedRows.length > 1) {
                var someItemsAreFolders = false;
                var pointerIds = [];
                selectedRows.forEach(function(item){
                    var thisItem = item.data;
                    someItemsAreFolders = someItemsAreFolders ||
                                          thisItem.isFolder ||
                                          thisItem.isSmartFolder ||
                                          thisItem.parentIsSmartFolder ||
                                          !thisItem.permissions.movable;
                    pointerIds.push(thisItem.node_id);
                });
                if(!someItemsAreFolders) {
                    var multiItemDetailTemplateSource = $('#project-detail-multi-item-template').html();
                    var detailTemplate = Handlebars.compile(multiItemDetailTemplateSource);
                    var detailTemplateContext = {
                        multipleItems: true,
                        itemsCount: selectedRows.length
                    };
                    var theParentNode = selectedRows[0].parent().data;
                    var displayHTML = detailTemplate(detailTemplateContext);
                    $('.project-details').html(displayHTML);
                    $('.project-details').show();
                    $('#remove-links-multiple').click(function(){
                        deleteMultiplePointersFromFolder(self.grid, pointerIds, theParentNode);
                    });
                    $('#close-multi-select').click(function () {
                        $('.project-details').hide();
                        return false;
                    });

                } else {
                    $('.project-details').hide();
                }
            } else {
                    $('.project-details').hide();
                }
        } // end onSelectedRowsChanged

    function deleteMultiplePointersFromFolder(theHgrid, pointerIds, folderToDeleteFrom) {
        if(pointerIds.length > 0) {
            var folderNodeId = folderToDeleteFrom.node_id;
            var url = '/api/v1/folder/' + folderNodeId + '/pointers/';
            var postData = JSON.stringify({pointerIds: pointerIds});
            var reloadHgrid = function () {
                if (theHgrid !== null) {
                    reloadFolder(theHgrid, folderToDeleteFrom);
                }
            };
            var deleteAction = $.ajax({
                type: 'DELETE',
                url: url,
                data: postData,
                contentType: 'application/json',
                dataType: 'json'
            });
            deleteAction.done(reloadHgrid);
            deleteAction.fail(function (jqxhr, textStatus, errorThrown){
                bootbox.alert('Error: ' + textStatus + '. ' + errorThrown);
            });
        }
    }

    function filterRowsNotInParent(rows) {
            // GET ORIGINAL ITEM
            // filter checking if : every item has the same parent as original item:  if not discard; 
            // return the new list and update selection view 

            var i, newRows = [];
            var originalRow = this.find(this.selected);
            if(typeof originalRow !== "undefined") {
                var originalParent = originalRow.parentID;
                for (i = 0; i < rows.length; i++) {
                    var currentItem = rows[i];
                    if(currentItem.parentID === originalParent && currentItem.id !== -1){
                        newRows.push(rows[i]);
                    }
                }
            }
            this.multiselected = newRows;
            this.highlightMultiselect.call(this); 
            return newRows;
        }



    // DRAG AND DROP METHODS
    function _poDrag (event, ui) {
        var itemID = $(event.target).attr('data-id');
        var item = this.find(itemID);
        $(ui.helper).css({ 'height' : '25px', 'width' : '400px', 'background' : 'white', 'padding' : '0px 10px', 'box-shadow' : '0 0 4px #ccc'});
        items = this.multiselected.length > 0 ? this.multiselected : [item]; 
        console.log("draglogic", event, ui, items); 
        dragLogic(event, items, ui);
    }

    function _poDrop (event, ui) {
        console.log(this, "Drop");
    }

    function dragLogic(event, items, ui){
        var canCopy = true;
        var canMove = true;
        items.forEach(function (item) {
            canCopy = canCopy && item.data.permissions.copyable;
            canMove = canMove && item.data.permissions.movable;
        });

        // Check through possible move and copy options, and set the copyMode appropriately.
        if (!(canMove && canCopy )) { //&& canAcceptDrop(items, folder))) {
            copyMode = 'forbidden';
        }
        else if (canMove && canCopy) {
            if (altKey) {
                copyMode = 'copy';
            } else {
                copyMode = 'move';
            }
        }
        if (!canMove && canCopy) {
            copyMode = 'copy';
        }
        if (!canCopy && canMove) {
            copyMode = 'move';
        }
        console.log('copyMode', copyMode);
        // Set the cursor to match the appropriate copy mode
        switch (copyMode) {
            case 'forbidden':
                $(ui.helper).css('cursor', 'not-allowed');
                break;
            case 'copy':
                $(ui.helper).css('cursor', 'copy');
                break;
            case 'move':
                $(ui.helper).css('cursor', 'move');
                break;
            default:
                $(ui.helper).css('cursor', 'default');
        }
    }

    function canAcceptDrop(items, folder){
        // folder is the drop target.
        // items is an array of things to go into the drop target.

        if (folder.isSmartFolder || !folder.isFolder){
            return false;
        }


        // if the folder is contained by the item, return false

        var representativeItem = items[0];
        if (draggable.grid.folderContains(representativeItem.id, folder.id)){
            return false;
        }

        // If trying to drop on the folder it came from originally, return false
        var itemParentNodeId = getItemParentNodeId(draggable.grid, representativeItem);
        if (itemParentNodeId === folder.node_id){
            return false;
        }

        var hasComponents = false;
        var hasFolders = false;
        var copyable = true;
        var movable = true;
        var canDrop = true;

        items.forEach(function(item){
            hasComponents = hasComponents || item.isComponent;
            hasFolders = hasFolders || item.isFolder;
            copyable = copyable && item.permissions.copyable;
            movable = movable && item.permissions.movable;
        });


        if(hasComponents){
            canDrop = canDrop && folder.permissions.acceptsComponents;
        }
        if(hasFolders){
            canDrop = canDrop && folder.permissions.acceptsFolders;
        }
        if(copyMode === 'move'){
            canDrop = canDrop && folder.permissions.acceptsMoves && movable;
        }
        if(copyMode === 'copy'){
            canDrop = canDrop && folder.permissions.acceptsCopies && copyable;
        }
        return canDrop;
    }

    // OSF-specific Treebeard options common to all addons
        tbOptions = {
                rowHeight : 35,         // user can override or get from .tb-row height
                showTotal : 15,         // Actually this is calculated with div height, not needed. NEEDS CHECKING
                paginate : false,       // Whether the applet starts with pagination or not.
                paginateToggle : false, // Show the buttons that allow users to switch between scroll and paginate.
                uploads : false,         // Turns dropzone on/off.
                columnTitles : _poColumnTitles,
                resolveRows : _poResolveRows,
                showFilter : false,     // Gives the option to filter by showing the filter box.
                title : false,          // Title of the grid, boolean, string OR function that returns a string.
                allowMove : true,       // Turn moving on or off.
                moveClass : 'po-draggable',
                hoverClass : 'fangorn-hover',
                hoverClassMultiselect : 'po-hover-multiselect',
                togglecheck : _poToggleCheck,
                sortButtonSelector : { 
                    up : 'i.icon-chevron-up',
                    down : 'i.icon-chevron-down'
                },
                dragOptions : {},
                dropOptions : {},
                dragEvents : {
                    start : function () {
                        $('.project-details').hide();
                    },
                    drag : _poDrag
                },
                dropEvents : {
                    out  : function () { console.log(this, "Out");},
                    over : function (event, ui) { console.log(this, event, ui, "Over");},
                    drop : _poDrop
                },
                onload : function (){
                    var tb = this;
                    // reload the data with expand options 
                    _poLoadOpenChildren.call(tb);
                },
                createcheck : function (item, parent) {
                    window.console.log('createcheck', this, item, parent);
                    return true;
                },
                deletecheck : function (item) {  // When user attempts to delete a row, allows for checking permissions etc.
                    window.console.log('deletecheck', this, item);
                    return true;
                },
                onselectrow : function (item) {
                    console.log('Row: ', item);
                },
                // onmouseoverrow : _poMouseOverRow,
                onmultiselect : _poMultiselect,
                dropzone : {                                           // All dropzone options.
                    url: '/api/v1/project/',  // When users provide single URL for all uploads
                    clickable : '#treeGrid',
                    addRemoveLinks: false,
                    previewTemplate: '<div></div>',
                    parallelUploads: 1
                    
                },
                resolveIcon : _poResolveIcon,
                resolveToggle : _poResolveToggle,
                resolveLazyloadUrl : _poResolveLazyLoad,
                // lazyLoadError : _fangornLazyLoadError,
                // resolveUploadMethod :_fangornUploadMethod,

    };


    function ProjectOrganizer(options) {
        this.options = $.extend({}, tbOptions, options);
        console.log('Options', this.options);
        this.grid = null; // Set by _initGrid
        this.init();
    }

    ProjectOrganizer.prototype = {
        constructor: ProjectOrganizer,
        init: function() {
            this._initGrid();
        },
        // Create the Treebeard once all addons have been configured
        _initGrid: function() {
            this.grid = Treebeard.run(this.options);
            return this.grid;
        }

    };


        return ProjectOrganizer;
}));