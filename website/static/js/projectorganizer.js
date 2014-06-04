;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils', 'hgrid', 'js/dropzone-patch', 'bootstrap',
            'hgridrowselectionmodel', 'rowmovemanager', 'typeahead', 'handlebars'], factory);
    } else if (typeof $script === 'function') {
            $script.ready(['dropzone', 'dropzone-patch', 'hgrid',
            'hgridrowselectionmodel', 'rowmovemanager', 'typeahead', 'handlebars'], function () {
                global.ProjectOrganizer = factory(jQuery, global.HGrid, global.ko);
                $script.done('projectorganizer');
            });
    } else {
        global.ProjectOrganizer = factory(jQuery, global.HGrid, global.ko);
    }
}(this, function ($, HGrid, ko) {
    'use strict';

    //
    // Private Helper Functions
    //
    //
    // HGrid Customization
    //

    ProjectOrganizer.Html = $.extend({}, HGrid.Html);
    ProjectOrganizer.Col = {};
    ProjectOrganizer.Col.Name = $.extend({}, HGrid.Col.Name);


    function nameRowView(row) {
        var name = row.name.toString();

        var url = row.urls.fetch;
        var linkString = name;
        if (url != null) {
            linkString = '<a href="' + url.toString() + '">' + name + '</a>';
        }

        var type = "project";
        if (row.isPointer) {
            type = "pointer";
        }
        return '<img src="/static/img/hgrid/' + type + '.png"><span class="'
            + type + '">' + linkString + '</span>';

    }

    var dateModifiedColumn = {
        id: 'date-modified',
        text: 'Modified',
        // Using a function that receives `row` containing all the item information
        itemView: function (row) {
            if(row.modifiedDelta == 0){
                return "";
            }
            return moment.utc(row.dateModified).fromNow()+", "+row.modifiedBy.toString();
        },
        folderView: function (row) {
            if(row.modifiedDelta == 0){
                return "";
            }
            return moment.utc(row.dateModified).fromNow()+", "+row.modifiedBy.toString();
        },
        sortable: false,
        selectable: true,
        width: 40
    };

    var contributorsColumn = {
        id: 'contributors',
        text: 'Contributors',
        // Using a function that receives `row` containing all the item information
        itemView: function (row) {
            var contributorCount = row.contributors.length;
            if(contributorCount == 0){
                return "";
            }
            var contributorString = row.contributors[0].name.toString();
            if(contributorCount > 1) {
                contributorString += " +" + (contributorCount - 1);
            }
            return contributorString;
        },
        folderView: function (row) {
            var contributorCount = row.contributors.length;
            if(contributorCount == 0){
                return "";
            }
            var contributorString = row.contributors[0].name.toString();
            if(contributorCount > 1) {
                contributorString += " +" + (contributorCount - 1);
            }
            return contributorString;
        },
        sortable: false,
        selectable: true,
        // behavior: "selectAndMove",
        width: 30
    };

    ProjectOrganizer.Col.Name.selectable = true;
    ProjectOrganizer.Col.Name.sortable = false;
    ProjectOrganizer.Col.Name.itemView = function (row) {
        var name = row.name.toString();

        var url = row.urls.fetch;
        var linkString = name;
        var extraClass = "";
        if (url != null) {
            linkString = '<a href="' + url + '">' + name + '</a>';
        }

        var type = "project";
        if (row.isPointer && !row.parentIsFolder) {
            type = "pointer"
        }
        if (row.isFolder) {
            type = "folder";
            if(!row.isSmartFolder) {
                extraClass = " dropzone";
            }
        }
        if (row.isSmartFolder) {
            extraClass += " smart-folder";

        }
        return '<img src="/static/img/hgrid/' + type + '.png"><span class="project-'
            + type + extraClass + '">' + linkString + '</span>';
    };
    ProjectOrganizer.Col.Name.folderView = ProjectOrganizer.Col.Name.itemView;


    var collapseAllInHGrid = function(grid) {
        grid.collapseAll();
    };

    var expandAllInHGrid = function(grid) {
        grid.getData().forEach(function(item) {
           grid.expandItem(item);
        });
    };

    var hgridInit = function(){
        var self = this;
        self.gridData = self.grid.grid.getData();
        self.myProjects = [];
        self.publicProjects = [];

        expandAllInHGrid(self.grid);

        // Expand/collapse All functions
        $(".pg-expand-all").click(function (){
            expandAllInHGrid(self.grid);
        });
        $(".pg-collapse-all").click(function (){
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


        self.grid.grid.setSelectionModel(new Slick.RowSelectionModel());
        //
        // Grab the JSON for the contents of the smart folder. Add that data
        // to self.myProjects so that we can use it for the autocomplete
        //
        // /api/v1/search/projects/?term=amel&maxResults=5&includePublic=no&includeContributed=yes

        self.publicProjects = new Bloodhound({
            datumTokenizer: function (d) {
                return Bloodhound.tokenizers.whitespace(d.name);
            },
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            remote: {
                url: '/api/v1/search/projects/?term=%QUERY&maxResults=10&includePublic=yes&includeContributed=no',
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
                url: '/api/v1/search/projects/?term=%QUERY&maxResults=10&includePublic=no&includeContributed=yes',
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

        self.grid.grid.onSelectedRowsChanged.subscribe(function () {
            var selectedRows = self.grid.grid.getSelectedRows();
            if (selectedRows.length == 1 ){
                self.myProjects.initialize();
                self.publicProjects.initialize();
                var linkName;
                var linkID;
                var theItem = self.grid.grid.getDataItem(selectedRows[0]);

                var theParentNode = self.grid.grid.getData().getItemById(theItem.parentID);
                if (typeof theParentNode !== 'undefined') {
                    var theParentNodeID = theParentNode.node_id;
                     theItem.parentIsSmartFolder = theParentNode.isSmartFolder;
                }
                else {
                    theParentNodeID = "";
                    theItem.parentIsSmartFolder = true;
                }

                if(!theItem.isSmartFolder) {
                    createProjectDetailHTMLFromTemplate(theItem);
                    $('#findNode'+theItem.node_id).hide();
                    $('#findNode'+theItem.node_id+' .typeahead').typeahead({
                      highlight: true
                    },
                    {
                        name: 'my-projects',
                        displayKey: function(data){
                              return data.name;
                          },
                        source: self.myProjects.ttAdapter(),
                        templates: {
                        header: function(){
                            return '<h3 class="category">My Projects</h3>'
                        },
                        suggestion: function(data){
                              return '<p>'+data.name+'</p>';
                          }
                        }
                    },
                    {
                        name: 'public-projects',
                        displayKey: function(data){
                              return data.name;
                          },
                        source: self.publicProjects.ttAdapter(),
                        templates: {
                        header: function(){
                            return '<h3 class="category">Public Projects</h3>'
                        },
                        suggestion: function(data){
                              return '<p>'+data.name+'</p>';
                          }
                        }
                   });

                    $('#input'+theItem.node_id).bind('typeahead:selected', function(obj, datum, name) {
                        $('#add-link-'+theItem.node_id).removeAttr('disabled');
                        linkName = datum.name;
                        linkID = datum.node_id;
                    });
                    $('#add-link-'+theItem.node_id).click(function() {
                        var url = "/api/v1/pointer/"; // the script where you handle the form input.
                        var postData = JSON.stringify(
                            {
                                pointerID: linkID,
                                toNodeID: theItem.node_id
                            });
                        $.ajax({
                            type: "POST",
                            url: url,
                            data: postData,
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                               reloadFolder(self, theItem);
                            }
                        });
                    });

                    $('#remove-link-'+theItem.node_id).click(function() {
                        var url = '/api/v1/folder/'+theParentNodeID+'/pointer/'+theItem.node_id;
                        var postData = JSON.stringify({});
                        $.ajax({
                            type: "DELETE",
                            url: url,
                            data: postData,
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                                reloadFolder(self, theItem);
                            }
                        });
                    });
                    $('#delete-folder-'+theItem.node_id).click(function() {
                        var confirmationText = "Are you sure you want to delete this folder? This will also delete any folders inside this one. You will not delete any projects in this folder.";
                        bootbox.confirm(confirmationText, function(result) {
                            if (result !== null && result) {
                                var url = '/api/v1/folder/'+theItem.node_id;
                                var postData = JSON.stringify({});
                                $.ajax({
                                    type: "DELETE",
                                    url: url,
                                    data: postData,
                                    contentType: 'application/json',
                                    dataType: 'json',
                                    success: function() {
                                        reloadFolder(self, theParentNode);
                                    }
                                });
                            }
                        });
                    });
                    $('#add-folder-'+theItem.node_id).click(function(){
                        $('#afc-'+theItem.node_id).show();
                    });
                    $('#add-folder-input'+theItem.node_id).bind('keyup',function() {
                        var contents = $.trim($(this).val());
                        if(contents === ''){
                            $('#add-folder-button'+theItem.node_id).attr("disabled", "disabled");
                        } else {
                            $('#add-folder-button'+theItem.node_id).removeAttr("disabled");
                        }
                    });

                     $('#add-folder-button'+theItem.node_id).click(function(){
                         var url = '/api/v1/folder/';
                         var postData = JSON.stringify({
                             node_id: theItem.node_id,
                             title: $.trim($('#add-folder-input'+theItem.node_id).val())
                         });
                         $.ajax({
                            type: "PUT",
                            url: url,
                            data: postData,
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                               reloadFolder(self, theItem);
                            }
                        });
                     });
                    $('#rename-node-'+theItem.node_id).click(function(){
                        $('#rnc-'+theItem.node_id).show();
                    });
                     $('#rename-node-input'+theItem.node_id).bind('keyup',function() {
                        var contents = $.trim($(this).val());
                        if(contents === '' || contents === theItem.name){
                            $('#rename-node-button'+theItem.node_id).attr("disabled", "disabled");
                        } else {
                            $('#rename-node-button'+theItem.node_id).removeAttr("disabled");
                        }
                    });

                     $('#rename-node-button'+theItem.node_id).click(function(){
                         var url = theItem.apiURL+'edit/';
                         var postData = JSON.stringify({
                             name: 'title',
                             value: $.trim($('#rename-node-input'+theItem.node_id).val())
                         });
                         $.ajax({
                            type: "POST",
                            url: url,
                            data: postData,
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                               reloadFolder(self, theItem);
                            }
                        });
                     });

                    $('#add-item-'+theItem.node_id).click(function(){
                        $('#buttons'+theItem.node_id).hide();
                        $('#findNode'+theItem.node_id).show();
                    });

                    $(".project-details").show();
                } else {
                    $(".project-details").hide();
                }
            } else {
                $(".project-details").hide();
            }



        }); // end onSelectedRowsChanged
    };

    function reloadFolder(self, theItem){
        self.grid.reloadFolder(theItem);
        self.grid.grid.setSelectedRows([]);
        self.grid.grid.resetActiveCell();
    }

    function createProjectDetailHTMLFromTemplate(theItem){
        var detailTemplateSource   = $("#project-detail-template").html();
        Handlebars.registerHelper('commalist', function(items, options) {
            var out = '';

            for(var i=0, l=items.length; i<l; i++) {
                out = out + options.fn(items[i]) + (i!==(l-1) ? ", ":"");
            }
            return out;
        });
        var detailTemplate = Handlebars.compile(detailTemplateSource);
        var detailTemplateContext = {
            theItem: theItem,
            multipleContributors: theItem.contributors.length > 1,
            parentIsSmartFolder: theItem.parentIsSmartFolder
        };
        var displayHTML    = detailTemplate(detailTemplateContext);
        $(".project-details").html(displayHTML);
    }

    //
    // Public methods
    //

    function ProjectOrganizer(selector, options) {
        var self = this;
        var baseOptions = {
            width: '550',
            height: '600',
            columns: [
                ProjectOrganizer.Col.Name,
                dateModifiedColumn,
                contributorsColumn
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
            fetchUrl: function(folder) {
                return '/api/v1/dashboard/get_dashboard/' + folder.node_id;
            },
            init: hgridInit.bind(self)
        };

        self.selector = selector;
        self.options = $.extend({}, baseOptions, options);
        self.init(self);
    }

    ProjectOrganizer.prototype.init = function() {
        var self = this;
        self.grid = new HGrid(self.selector, self.options);

    };

    return ProjectOrganizer;
}));