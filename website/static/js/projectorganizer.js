;
(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils', 'hgrid', 'bootstrap', 'hgrid-draggable',
            'typeahead', 'handlebars'], factory);
    } else if (typeof $script === 'function') {
        $script.ready(['hgrid', 'typeahead', 'handlebars', 'hgrid-draggable'],
            function () {
                global.ProjectOrganizer = factory(jQuery, global.HGrid, global.ko);
                $script.done('projectorganizer');
            });
    } else {
        global.ProjectOrganizer = factory(jQuery, global.HGrid, global.ko);
    }
}(this, function ($, HGrid, ko) {
    'use strict';

    //
    // Globals
    //
    // ReloadNextFolder semaphores
    var reloadNewFolder = false;
    var rnfPrevItem = "";
    var rnfToReload = "";
    // copyMode can be "copy", "move", "forbidden", or "none".
    var copyMode = "none";

    var fadeTime = 100;



    //
    // Private Helper Functions
    //
    function setReloadNextFolder(prevItem, toReload){
        reloadNewFolder = true;
        rnfPrevItem = prevItem;
        rnfToReload = toReload;
    }

    function getItemParentNodeId(theHgrid, item) {
        var itemParentID = item.parentID;
        var itemParent = theHgrid.grid.getData().getItemById(itemParentID);
        return itemParent.node_id;
    }

    function deleteMultiplePointersFromFolder(theHgrid, pointerIds, folderToDeleteFrom) {
        if(pointerIds.length > 0) {
            var folderNodeId = folderToDeleteFrom.node_id;
            var url = '/api/v1/folder/' + folderNodeId + '/pointers/';
            var postData = JSON.stringify({pointerIds: pointerIds});
            $.ajax({
                type: "DELETE",
                url: url,
                data: postData,
                contentType: 'application/json',
                dataType: 'json',
                success: function () {
                    if (theHgrid !== null) {
                        reloadFolder(theHgrid, folderToDeleteFrom);
                    }
                }
            });
        }
    }

    function setItemToExpand(item, callback) {
        var expandUrl = item.apiURL + 'expand/';
        var postData = JSON.stringify({});
        $.ajax({
            type: "POST",
            url: expandUrl,
            data: postData,
            contentType: 'application/json',
            dataType: 'json'
        }).done(function() {
            item.expand = false;
            if (typeof callback !== "undefined") {
                callback();
            }
        });
    }

    function reloadFolder(hgrid, theItem, theParentNode) {
        var toReload = theItem;
        if(typeof theParentNode !== "undefined" || theItem.kind !== 'folder') {
            toReload = theParentNode;
        }
        hgrid.reloadFolder(toReload);
        hgrid.grid.setSelectedRows([]);
        hgrid.grid.resetActiveCell();
        return toReload;
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
        if (itemParentNodeId == folder.node_id){
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
        if(copyMode === "move"){
            canDrop = canDrop && folder.permissions.acceptsMoves && movable;
        }
        if(copyMode === "copy"){
            canDrop = canDrop && folder.permissions.acceptsCopies && copyable;
        }
        return canDrop;
    }

    function dragLogic(event, items){
        var canCopy = true;
        var canMove = true;

        items.forEach(function (item) {
            canCopy = canCopy && item.permissions.copyable;
            canMove = canMove && item.permissions.movable;
        });

        // Check through possible move and copy options, and set the copyMode appropriately.
        if (!(canMove || canCopy)) {
            copyMode = "forbidden"
        }
        else if (canMove && canCopy) {
            if (altKey) {
                copyMode = "copy";
            } else {
                copyMode = "move";
            }
        }
        if (!canMove && canCopy) {
            copyMode = "copy";
        }
        if (!canCopy && canMove) {
            copyMode = "move";
        }

        // Set the cursor to match the appropriate copy mode
        switch (copyMode) {
            case "forbidden":
                $('.project-organizer-dand').css('cursor', 'not-allowed');
                break;
            case "copy":
                $('.project-organizer-dand').css('cursor', 'copy');
                break;
            case "move":
                $('.project-organizer-dand').css('cursor', 'move');
                break;
            default:
                $('.project-organizer-dand').css('cursor', 'default');
        }

    }

    function dropLogic(event, items, folder) {
        if (typeof folder !== "undefined" && folder !== null) {
            var theFolderNodeID = folder.node_id;
            var getChildrenURL = folder.apiURL + 'get_folder_pointers/';
            var folderChildren;
            var sampleItem = items[0];
            var itemParentID = sampleItem.parentID;
            var itemParent = draggable.grid.grid.getData().getItemById(itemParentID);
            var itemParentNodeID = itemParent.node_id;
            if (itemParentNodeID !== theFolderNodeID) { // This shouldn't happen, but if it does, it's bad
                $.getJSON(getChildrenURL, function (data) {
                    // We can't add a pointer to a folder that already has those pointers, so cull those away
                    folderChildren = data;
                    var itemsToMove = [];
                    var itemsNotToMove = [];
                    items.forEach(function (item) {
                        if ($.inArray(item.node_id, folderChildren) === -1) { // pointer not in folder to be moved to
                            itemsToMove.push(item.node_id);
                        } else if (copyMode == "move") { // Pointer is already in the folder and it's a move
    //                              We  need to make sure not to delete the folder if the item is moved to the same folder.
    //                              When we add the ability to reorganize within a folder, this will have to change.
                            itemsNotToMove.push(item.node_id);
                        }
                    });

                    var postInfo = {
                        "copy": {
                            "url": "/api/v1/project/" + theFolderNodeID + "/pointer/",
                            "json": {
                                nodeIds: itemsToMove
                            }
                        },
                        "move": {
                            "url": "/api/v1/pointers/move/",
                            "json": {
                                pointerIds: itemsToMove,
                                toNodeId: theFolderNodeID,
                                fromNodeId: itemParentNodeID
                            }
                        }
                    };

                    if (copyMode === "copy" || copyMode === "move") {
                        // Remove all the duplicated pointers
                        deleteMultiplePointersFromFolder(null, itemsNotToMove, itemParent);
                        setItemToExpand(folder, function () {
                            if (itemsToMove.length > 0) {
                                var url = postInfo[copyMode]["url"];
                                var postData = JSON.stringify(postInfo[copyMode]["json"]);
                                var outerFolderID = whichIsContainer(draggable.grid, itemParentID, folder.id);

                                $.ajax({
                                    type: "POST",
                                    url: url,
                                    data: postData,
                                    contentType: 'application/json',
                                    dataType: 'json',
                                    complete: function () {
                                        if (copyMode == "move") {
                                            if (typeof outerFolderID === 'undefined' || outerFolderID === null) {
                                                itemParent = draggable.grid.grid.getData().getItemById(itemParentID);
                                                setReloadNextFolder(itemParentID, folder.id);
                                                draggable.grid.reloadFolder(itemParent);

                                            } else {
                                                var outerFolder = draggable.grid.grid.getData().getItemById(outerFolderID);
                                                reloadFolder(draggable.grid, outerFolder);
                                            }

                                        } else {
                                            reloadFolder(draggable.grid, folder);
                                        }
                                        copyMode = "none";

                                    }
                                });
                            } else { // From:  if(itemsToMove.length > 0)
                                reloadFolder(draggable.grid, itemParent);
                            }
                        });
                    } // From: if (copyMode === "copy" || copyMode === "move")
                });
            } else {
                console.error("Parent node (" + itemParentNodeID + ") == Folder Node (" + theFolderNodeID + ")");
            }
        } else {
            if (typeof folder === "undefined") {
                console.error("oDrop folder is undefined.");
            }/* else {
                console.error("onDrop folder is null.");
            }*/
        }
        $('.project-organizer-dand').css('cursor', 'default');
    }
     /**
     * Takes two element IDs and tries to determine if one contains the other. Returns the container or null if
     * they are not directly related. Items contain themselves.
     * @method whichIsContainer
     * @param hgrid {Object: Hgrid}
     * @param itemOneID {Number}
     * @param itemTwoID {Number}
     * @returns item ID or null
     */
    function whichIsContainer(hgrid, itemOneID, itemTwoID){
        var pathToOne = hgrid.getPathToRoot(itemOneID);
        var pathToTwo = hgrid.getPathToRoot(itemTwoID);
        if(pathToOne.indexOf(itemTwoID) > -1 ){
            return itemTwoID;
        } else if (pathToTwo.indexOf(itemOneID) > -1) {
            return itemOneID;
        } else {
            return null;
        }
    }

    function createProjectDetailHTMLFromTemplate(theItem) {
        var detailTemplateSource = $("#project-detail-template").html();
        Handlebars.registerHelper('commalist', function (items, options) {
            var out = '';

            for (var i = 0, l = items.length; i < l; i++) {
                out = out + options.fn(items[i]) + (i !== (l - 1) ? ", " : "");
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
        $(".project-details").html(displayHTML);
        addFormKeyBindings(theItem.node_id);

    }

    var altKey = false;
    $(document).keydown(function (e) {
        if (e.altKey) {
            altKey = true;
        }
    });
    $(document).keyup(function (e) {
        if (!e.altKey) {
            altKey = false;
        }
    });

    function addFormKeyBindings(nodeID){
        $("#ptd-"+nodeID).keyup(function (e){
            if(e.which == 13){ //return
                // Find visible submit-button in this div and activate it
                $("#ptd-"+nodeID).find(".submit-button-"+nodeID).filter(":visible").click();
                return false;
            } else if (e.which == 27) {//esc
                // Find visible cancel-button in this div and activate it
                $("#ptd-"+nodeID).find(".cancel-button-"+nodeID).filter(":visible").click();
                return false;
            }
        });
    }

    var collapseAllInHGrid = function (grid) {
        grid.collapseAll();
    };

    var expandAllInHGrid = function (grid) {
        grid.getData().forEach(function (item) {
            grid.expandItem(item);
        });
    };

    //
    // HGrid Customization
    //

    ProjectOrganizer.Html = $.extend({}, HGrid.Html);
    ProjectOrganizer.Col = {};
    ProjectOrganizer.Col.Name = $.extend({}, HGrid.Col.Name);

    var dateModifiedColumn = {
        id: 'date-modified',
        text: 'Modified',
        // Using a function that receives `row` containing all the item information
        itemView: function (row) {
            if (row.modifiedDelta == 0) {
                return "";
            }
            return moment.utc(row.dateModified).fromNow() + ", " + row.modifiedBy.toString();
        },
        folderView: function (row) {
            if (row.modifiedDelta == 0) {
                return "";
            }
            return moment.utc(row.dateModified).fromNow() + ", " + row.modifiedBy.toString();
        },
        sortable: false,
        selectable: true,
        behavior: "move",
        width: 40
    };

    var contributorsColumn = {
        id: 'contributors',
        text: 'Contributors',
        // Using a function that receives `row` containing all the item information
        itemView: function (row) {
            var contributorCount = row.contributors.length;
            if (contributorCount == 0) {
                return "";
            }
            var contributorString = row.contributors[0].name.toString();
            if (contributorCount > 1) {
                contributorString += " +" + (contributorCount - 1);
            }
            return contributorString;
        },
        folderView: function (row) {
            var contributorCount = row.contributors.length;
            if (contributorCount == 0) {
                return "";
            }
            var contributorString = row.contributors[0].name.toString();
            if (contributorCount > 1) {
                contributorString += " +" + (contributorCount - 1);
            }
            return contributorString;
        },
        sortable: false,
        selectable: true,
        behavior: "move",
        width: 30
    };

    ProjectOrganizer.Col.Name.selectable = true;
    ProjectOrganizer.Col.Name.sortable = false;
    ProjectOrganizer.Col.Name.behavior = "move";
    ProjectOrganizer.Col.Name.indent = 20;
    ProjectOrganizer.Col.Name.showExpander = function(row, args) {
        return (row.childrenCount > 0);
    };
    ProjectOrganizer.Col.Name.itemView = function (row) {
        var name = row.name.toString();

        var url = row.urls.fetch;
        var linkString = name;
        var extraClass = "";
        if (url != null) {
            linkString = '<a href="' + url + '">' + name + '</a>';
        }

        var type = row.type;

        if (row.isSmartFolder) {
            type = "folder";
            extraClass += " smart-folder";
        }

        var regType = "";
        if(row.isRegistration){
            regType = "reg-";
            extraClass += " registration";
        }
        return '<img src="/static/img/hgrid/' + regType + type + '.png"><span class="project-'
            + type + extraClass + '">' + linkString + '</span>';
    };
    ProjectOrganizer.Col.Name.folderView = ProjectOrganizer.Col.Name.itemView;


    //
    // Hgrid Init
    //

    var hgridInit = function () {
        var self = this;
        self.gridData = self.grid.grid.getData();
        self.myProjects = [];
        self.publicProjects = [];
        self.grid.registerPlugin(draggable);
        // Expand/collapse All functions
        $(".pg-expand-all").click(function () {
            expandAllInHGrid(self.grid);
        });
        $(".pg-collapse-all").click(function () {
            collapseAllInHGrid(self.grid);
        });

        // This useful function found on StackOverflow http://stackoverflow.com/a/7385673
        // Used to hide the detail card when you click outside of it onto its containing div
        $(document).click(function (e) {
            var container = $("#project-grid");
            var altContainer = $(".project-details");

            if (!container.is(e.target) && !altContainer.is(e.target) // if the target of the click isn't the container...
                && container.has(e.target).length === 0 && altContainer.has(e.target).length === 0)// ... nor a descendant of the container
            {
                self.grid.grid.setSelectedRows([]);
                self.grid.grid.resetActiveCell();
            }
        });


        self.publicProjects = new Bloodhound({
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

        self.myProjects = new Bloodhound({
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

        //
        // When the selection changes, create the div that holds the detail information for the project including
        // whichever action buttons will work with that type of node. This is what will be changed by moving
        // to Knockout.js
        //

        self.grid.grid.onSelectedRowsChanged.subscribe(function (e, args) {
            var selectedRows = self.grid.grid.getSelectedRows();
            var multipleItems = false;
            if (selectedRows.length == 1) {
                self.myProjects.initialize();
                self.publicProjects.initialize();
                var linkName;
                var linkID;
                var theItem = self.grid.grid.getDataItem(selectedRows[0]);
                if (theItem.isFolder && !theItem.isSmartFolder) {
                    var getChildrenURL = theItem.apiURL + 'get_folder_pointers/';
                    var children;
                    $.getJSON(getChildrenURL, function (data) {
                        children = data;
                    });
                }
                var theParentNode = self.grid.grid.getData().getItemById(theItem.parentID);
                if (typeof theParentNode === 'undefined') {
                    theParentNode = theItem;
                    theItem.parentIsSmartFolder = true;
                }
                theItem.parentNode = theParentNode;

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
                            source: self.myProjects.ttAdapter(),
                            templates: {
                                header: function () {
                                    return '<h3 class="category">My Projects</h3>'
                                },
                                suggestion: function (data) {
                                    return '<p>' + data.name + '</p>';
                                }
                            }
                        },
                        {
                            name: 'public-projects',
                            displayKey: function (data) {
                                return data.name;
                            },
                            source: self.publicProjects.ttAdapter(),
                            templates: {
                                header: function () {
                                    return '<h3 class="category">Public Projects</h3>'
                                },
                                suggestion: function (data) {
                                    return '<p>' + data.name + '</p>';
                                }
                            }
                        });

                    $('#input' + theItem.node_id).bind('keyup', function (event) {
                        var key = event.keyCode || event.which;
                        var buttonEnabled = (typeof $('#add-link-' + theItem.node_id).prop('disabled') !== "undefined");

                        if (key === 13) {
                            if (buttonEnabled) {
                                $('#add-link-' + theItem.node_id).click(); //submits if the control is active
                            }
                        }
                        else {
                            $('#add-link-warn-' + theItem.node_id).text("");
                            $('#add-link-' + theItem.node_id).attr("disabled", "disabled");
                            linkName = "";
                            linkID = "";
                        }
                    });
                    $('#input' + theItem.node_id).bind('typeahead:selected', function (obj, datum, name) {
                        if (children.indexOf(datum.node_id) == -1) {
                            $('#add-link-' + theItem.node_id).removeAttr('disabled');
                            linkName = datum.name;
                            linkID = datum.node_id;
                        } else {
                            $('#add-link-warn-' + theItem.node_id).text("This project is already in the folder")
                        }
                    });
                    $('#add-link-' + theItem.node_id).click(function () {
                        var url = "/api/v1/pointer/";
                        var postData = JSON.stringify(
                            {
                                pointerID: linkID,
                                toNodeID: theItem.node_id
                            });
                        setItemToExpand(theItem, function() {
                            $.ajax({
                                type: "POST",
                                url: url,
                                data: postData,
                                contentType: 'application/json',
                                dataType: 'json',
                                success: function () {
                                    reloadFolder(self.grid, theItem, theParentNode);
                                }
                            });
                        });

                    });

                    $('#remove-link-' + theItem.node_id).click(function () {
                        var url = '/api/v1/folder/' + theParentNodeID + '/pointer/' + theItem.node_id;
                        var postData = JSON.stringify({});
                        $.ajax({
                            type: "DELETE",
                            url: url,
                            data: postData,
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function () {
                                reloadFolder(self.grid, theParentNode);
                            }
                        });
                    });
                    $('#delete-folder-' + theItem.node_id).click(function () {
                        var confirmationText = "Are you sure you want to delete this folder? This will also delete any folders inside this one. You will not delete any projects in this folder.";
                        bootbox.confirm(confirmationText, function (result) {
                            if (result !== null && result) {
                                var url = '/api/v1/folder/';
                                var postData = JSON.stringify({ 'node_id': theItem.node_id });
                                $.ajax({
                                    type: "DELETE",
                                    url: url,
                                    data: postData,
                                    contentType: 'application/json',
                                    dataType: 'json',
                                    success: function () {
                                        reloadFolder(self.grid, theParentNode);
                                    }
                                });
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
                            $('#add-folder-button' + theItem.node_id).attr("disabled", "disabled");
                        } else {
                            $('#add-folder-button' + theItem.node_id).removeAttr("disabled");
                        }
                    });

                    $('#add-folder-button' + theItem.node_id).click(function () {
                        var url = '/api/v1/folder/';
                        var postData = JSON.stringify({
                            node_id: theItem.node_id,
                            title: $.trim($('#add-folder-input' + theItem.node_id).val())
                        });
                        setItemToExpand(theItem, function() {
                            $.ajax({
                                type: "PUT",
                                url: url,
                                data: postData,
                                contentType: 'application/json',
                                dataType: 'json',
                                success: function () {
                                    reloadFolder(self.grid, theItem, theParentNode);
                                }
                            });
                        });

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
                            $('#rename-node-button' + theItem.node_id).attr("disabled", "disabled");
                        } else {
                            $('#rename-node-button' + theItem.node_id).removeAttr("disabled");
                        }
                    });

                    $('#rename-node-button' + theItem.node_id).click(function () {
                        var url = theItem.apiURL + 'edit/';
                        var postData = JSON.stringify({
                            name: 'title',
                            value: $.trim($('#rename-node-input' + theItem.node_id).val())
                        });
                        $.ajax({
                            type: "POST",
                            url: url,
                            data: postData,
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function () {
                                reloadFolder(self.grid, theParentNode);
                            }
                        });
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

                    $(".project-details").show();
                } else {
                    $(".project-details").hide();
                }
            } else if(selectedRows.length > 1) {
                var someItemsAreFolders = false;
                var pointerIds = [];

                selectedRows.forEach(function(item){
                    var thisItem = self.grid.grid.getDataItem(item);
                    someItemsAreFolders = someItemsAreFolders || thisItem.isFolder || thisItem.isSmartFolder
                        || thisItem.parentIsSmartFolder;
                    pointerIds.push(thisItem.node_id);
                });

                if(!someItemsAreFolders) {
                    var multiItemDetailTemplateSource = $("#project-detail-multi-item-template").html();
                    var detailTemplate = Handlebars.compile(multiItemDetailTemplateSource);
                    var detailTemplateContext = {
                        multipleItems: true,
                        itemsCount: selectedRows.length
                    };
                    var sampleItem = self.grid.grid.getDataItem(selectedRows[0]);
                    theParentNode = self.grid.grid.getData().getItemById(sampleItem.parentID);
                    theParentNodeID = theParentNode.node_id;
                    var displayHTML = detailTemplate(detailTemplateContext);
                    $(".project-details").html(displayHTML);
                    $(".project-details").show();
                    $('#remove-links-multiple').click(function(){
                        deleteMultiplePointersFromFolder(self.grid, pointerIds, theParentNode);
                    });

                } else {
                    $(".project-details").hide();
                }
            } else {
                    $(".project-details").hide();
                }


        }); // end onSelectedRowsChanged
    };


    var draggable = new HGrid.Draggable({
        onDrag: function (event, items) {
            dragLogic(event, items);
        },
        onDrop: function (event, items, folder) {
            dropLogic(event, items, folder);
        },
        canDrag: function (item) {
            return item.permissions.copyable || item.permissions.movable
        },
        acceptDrop: function (item, folder, done) {
            done();
        },
        canAcceptDrop: function(items, folder) {
            return canAcceptDrop(items, folder);
        },
        enableMove: false,
        rowMoveManagerOptions: {proxyClass: 'project-organizer-dand'}
    });


    //
    // Public methods
    //

    function ProjectOrganizer(selector, options) {
        var self = this;
        var baseHGridOptions = {
            width: '100%',
            height: '600',
            columns: [
                ProjectOrganizer.Col.Name,
                contributorsColumn,
                dateModifiedColumn
            ],
            slickgridOptions: {
                editable: true,
                enableAddRow: false,
                enableCellNavigation: true,
                multiSelect: true,
                forceFitColumns: true,
                autoEdit: false
            },
            data: '/api/v1/dashboard/get_dashboard/',  // Where to get the initial data
            fetchUrl: function (folder) {
                return '/api/v1/dashboard/get_dashboard/' + folder.node_id;
            },
            fetchSuccess: function(newData, item){
                if(reloadNewFolder) {
                    reloadNewFolder = false;
                    var toReloadItem = draggable.grid.grid.getData().getItemById(rnfToReload);
                    if (rnfPrevItem !== rnfToReload && typeof toReloadItem !== "undefined") {
                        draggable.grid.reloadFolder(toReloadItem);
                    }
                    draggable.grid.grid.setSelectedRows([]);
                    draggable.grid.grid.resetActiveCell();
                }
                self.options.success.call();
            },
            getExpandState: function(folder) {
                return folder.expand;
            },
            onExpand: function(event, item) {
                var self = this;
                item.expand = false;
                self.emptyFolder(item);
                if(typeof event !== 'undefined' && typeof item.apiURL !== "undefined" && item.type !== "pointer") {
                    setItemToExpand(item);
                }
            },
            onCollapse: function(event, item) {
                item.expand = false;
                if(typeof event !== 'undefined' && typeof item.apiURL !== "undefined" && item.type !== "pointer") {
                    var collapseUrl = item.apiURL + 'collapse/';
                    var postData = JSON.stringify({});
                    $.ajax({
                        type: "POST",
                        url: collapseUrl,
                        data: postData,
                        contentType: 'application/json',
                        dataType: 'json'
                    }).done(function() {
                        item.expand = false;
                    });
                }
            },

            init: hgridInit.bind(self)
        };

        var defaultOptions = {
           success: function() {}
        };

        self.selector = selector;
        self.options = $.extend(defaultOptions, options);
        self.hgridOptions = baseHGridOptions;

        self.init(self);
        self.altKey = false;
    }

    ProjectOrganizer.prototype.init = function () {
        var self = this;
        self.grid = new HGrid(self.selector, self.hgridOptions);
    };

    ProjectOrganizer.prototype.getGrid = function() {
        return this.grid;
    };

    return ProjectOrganizer;
}));