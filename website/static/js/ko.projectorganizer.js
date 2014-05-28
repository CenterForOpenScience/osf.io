;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils', 'hgrid', 'js/dropzone-patch', 'bootstrap',
            'hgridrowselectionmodel', 'rowmovemanager', 'typeahead', 'handlebars'], factory);
    } else if (typeof $script === 'function') {
            $script.ready(['dropzone', 'dropzone-patch', 'hgrid',
            'hgridrowselectionmodel', 'rowmovemanager', 'typeahead', 'handlebars'], function () {
                global.ProjectOrganizer = factory(jQuery, global.HGrid, global.ko);
                $script.done('projectorganizer-ko');
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
        return '<img src="/static/img/hgrid/' + type + '.png"><span class="project-'
            + type + extraClass + '">' + linkString + '</span>';
    };
    ProjectOrganizer.Col.Name.folderView = ProjectOrganizer.Col.Name.itemView;


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

    ko.bindingHandlers.HGrid = {
        init: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
            self.init(self, element)
        },
        update: function(element, valueAccessor, allBindings, viewModel, bindingContext) {
            // This will be called once when the binding is first applied to an element,
            // and again whenever the associated observable changes value.
            // Update the DOM element based on the supplied values here.
        }
    };

    //
    // Public methods
    //

    function ProjectOrganizer(selector, options) {
        var self = this;
        this.selector = selector;
        this.options = $.extend({}, baseOptions, options);

    }

    ProjectOrganizer.prototype.init = function(self, element) {
        self.grid = new HGrid(element, self.options);
        self.gridData = self.grid.grid.getData();
        self.myProjects = [];

        // addDragAndDrop(self);

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



    };

    return ProjectOrganizer;
}));