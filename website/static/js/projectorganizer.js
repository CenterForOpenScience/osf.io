;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'hgrid', 'js/dropzone-patch', 'bootstrap', 'cellselectionmodel',
            'rowselectionmodel','typeahead', 'handlebars'], factory);
    } else if (typeof $script === 'function') {
        $script.ready(['dropzone', 'dropzone-patch', 'hgrid', 'cellselectionmodel',
            'rowselectionmodel', 'typeahead', 'handlebars'], function () {
            global.ProjectOrganizer = factory(jQuery, global.HGrid);
            $script.done('projectorganizer');
        });
    } else {
        global.ProjectOrganizer = factory(jQuery, global.HGrid);
    }
}(this, function ($, HGrid) {
    'use strict';

    //
    // Private Helper Functions
    //
    var substringMatcher = function(strs) {
      return function findMatches(q, cb) {
        var matches, substringRegex;

        // an array that will be populated with substring matches
        matches = [];

        // regex used to determine if a string contains the substring `q`
        var substrRegex = new RegExp(q, 'i');

        // iterate through the pool of strings and for any string that
        // contains the substring `q`, add it to the `matches` array
        $.each(strs, function(i, str) {
          if (substrRegex.test(str.name)) {
            // the typeahead jQuery plugin expects suggestions to a
            // JavaScript object, refer to typeahead docs for more info
            matches.push({ value: str });
          }
        });

        cb(matches);
      };
    };

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
        width: 30
    };

    ProjectOrganizer.Col.Name.selectable = true;
    ProjectOrganizer.Col.Name.sortable = false;
    ProjectOrganizer.Col.Name.itemView = function (row) {
        var name = row.name.toString();

        var url = row.urls.fetch;
        var linkString = name;
        if (url != null) {
            linkString = '<a href="' + url + '">' + name + '</a>';
        }

        var type = "project"
        if (row.isPointer & !row.parentIsFolder) {
            type = "pointer"
        }
        if (row.isFolder) {
            type = "folder"
        }
        return '<img src="/static/img/hgrid/' + type + '.png"><span class="proj'
            + type + '">' + linkString + '</span>';
    };
    ProjectOrganizer.Col.Name.folderView = ProjectOrganizer.Col.Name.itemView;


    var baseOptions = {
        width: '550',
        height: '600',
        columns: [ProjectOrganizer.Col.Name,dateModifiedColumn,contributorsColumn

            ],
        slickgridOptions: {
            editable: true,
            enableCellNavigation: true,
            multiSelect: false
        }
    };

    var collapseAllInHGrid = function(grid) {
        grid.collapseAll();
    };

    var expandAllInHGrid = function(grid) {
        grid.getData().forEach(function(item) {
           grid.expandItem(item);
        });
    };

    //
    // Public methods
    //

    function ProjectOrganizer(selector, options) {
        var self = this;
        this.selector = selector;
        this.options = $.extend({}, baseOptions, options);
        this.init(self)
    }

    ProjectOrganizer.prototype.init = function(self) {
        self.grid = new HGrid(this.selector, this.options);
        self.myProjects = [];

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
        // Initially add the data to the HGrid
        // Start with the Smart Folder
        //

        self.grid.addItem({
            name: 'All My Projects',
            urls: {fetch: null},
            isFolder: true,
            isSmartFolder: true,
            isPointer: false,
            modifiedDelta: "",
            dateModified: "",
            permissions: {edit: false, view: true},
            kind: 'folder',
            id: -1,
            contributors: [],
            modifiedBy: ""
        });

        //
        // Grab the JSON for the contents of the smart folder. Add that data to the grid and put the
        // projects you can contribute to into self.myProjects so that we can use it for the autocomplete
        //

        $.getJSON("/api/v1/dashboard/get_all_projects/", function (projects) {
            self.grid.addData(projects.data, -1);
            projects.data.forEach(function(item) {
                if(!item.isPointer){
                    self.myProjects.push(
                        {
                            name: item.name,
                            node_id: item.node_id
                        }
                    )
                }
            });
        });

        //
        // Grab the dashboard structure and add it to the HGrid
        //

        $.getJSON("/api/v1/dashboard/get_dashboard/", function (projects) {
            self.grid.addData(projects.data);
        });

        //
        // When the selection changes, create the div that holds the detail information for the project including
        // whichever action buttons will work with that type of node. This is what will be changed by moving
        // to Knockout.js
        //

        this.grid.grid.onSelectedRowsChanged.subscribe(function () {
            var selectedRows = self.grid.grid.getSelectedRows();
            if (selectedRows.length == 1 ){
                var linkName;
                var linkID;
                var theItem = self.grid.grid.getDataItem(selectedRows[0]);
                var theParentNode = self.grid.grid.getData().getItemById(theItem.parentID)
                if (typeof theParentNode !== 'undefined') {
                    var theParentNodeID = theParentNode.node_id
                }
                else {
                    theParentNodeID = ""
                }
                var parentIsSmartFolder = false;
                if (theItem.parentID == -1){
                    parentIsSmartFolder = true;
                }
                if(theItem.id != -1) {
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
                        parentIsSmartFolder: parentIsSmartFolder
                    };
                    var displayHTML    = detailTemplate(detailTemplateContext);
                    $(".project-details").html(displayHTML);
                    $('#findNode'+theItem.node_id).hide();
                    $('#findNode'+theItem.node_id+' .typeahead').typeahead({
                      highlight: true
                    },
                    {
                      name: 'my-projects',
                      displayKey: function(data){
                              return data.value.name;
                          },
                      source: substringMatcher(self.myProjects),
                      templates: {
                        header: '<h3 class="category">My Projects</h3>',
                        suggestion: function(data){
                              return '<p>'+data.value.name+'</p>';
                          }
                      }
                    });
                    $('#input'+theItem.node_id).bind('typeahead:selected', function(obj, datum, name) {
                        $('#add-link-'+theItem.node_id).removeAttr('disabled');
                        linkName = datum.value.name;
                        linkID = datum.value.node_id;
                    });
                    $('#add-link-'+theItem.node_id).click(function() {
                        var url = "/api/v1/project/"+theItem.node_id+"/pointer/"; // the script where you handle the form input.
                        var postData = JSON.stringify({nodeIds: [linkID]});
                        $.ajax({
                            type: "POST",
                            url: url,
                            data: postData,
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                                window.location.reload();
                            }
                        });
                    });

                    $('#remove-link-'+theItem.node_id).click(function() {
                        var url = '/api/v1/folder/'+theParentNodeID+'/pointer/';
                        var postData = JSON.stringify({pointerNodeId: theItem.node_id});
                        $.ajax({
                            type: "DELETE",
                            url: url,
                            data: postData,
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                                window.location.reload();
                            }
                        });
                    });
                    $('#delete-folder-'+theItem.node_id).click(function() {
                        var confirmationText = "Are you sure you want to delete this folder? This will also delete any folders inside this one. You will not delete any projects in this folder."
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
                                        window.location.reload();
                                    }
                                });
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


    }

    return ProjectOrganizer;
}));