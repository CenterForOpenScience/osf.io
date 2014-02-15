<%inherit file="base.mako"/>
<%def name="title()">FAQ</%def>
<%def name="content()">

<h2>SPSP 2014 Posters & Talks</h2>
Search results by title: <input id="gridSearch" />

<div id="grid" style="width:800px; height:400px;"></div>

<script type="text/javascript">

    var data = ${data};

    function titleFormatter(row, cell, value, columnDef, dataContext) {
        return '<a target="_blank" href="' + dataContext.nodeUrl + '">' +
            value +
        '</a>';
    }

    function tagsFormatter(row, cell, value, columnDef, dataContext) {
        return value.map(function(item) {
            return '<a target="_blank" href="' + item.url + '">' +
                item.label +
            '</a>';
        }).join(', ');
    }

    function downloadFormatter(row, cell, value, columnDef, dataContext) {
        if (value.url) {
            return '<a href="' + value.url + '">' +
                '<button class="btn btn-success btn-mini">' +
                    '<i class="icon-download-alt icon-white"></i>' +
                '</button>' +
            '</a>&nbsp;' + value.count;
        } else {
            return '';
        }
    }

    function searchFilter(item, args) {
        console.log(item);
        if (args.searchString != "" && item.title.indexOf(args.searchString) == -1) {
            console.log('no')
            return false;
        }
        console.log('yes')
        return true;
    }

    var columns = [
        {id: 'title', field: 'title', name: 'Title', sortable: true, formatter: titleFormatter},
        {id: 'author', field: 'author', name: 'Author', sortable: true},
        {id: 'tags', field: 'tags', name: 'Tags', formatter: tagsFormatter},
        {id: 'download', field: 'download', name: 'Download', formatter: downloadFormatter}
    ];

    var options = {
        forceFitColumns: true
    };

    var dataView = new Slick.Data.DataView({inlineFilters: true});
    var grid = new Slick.Grid('#grid', dataView, columns, options);
    var searchString = '';

    grid.onSort.subscribe(function(e, args) {
        var field = args.sortCol.field;
        data.sort(function(a, b){
            var result =
                a[field] > b[field] ? 1 :
                a[field] < b[field] ? -1 :
                0;

            return args.sortAsc ? result : -result;
        });
        grid.invalidate();
    });

    // wire up model events to drive the grid
    dataView.onRowCountChanged.subscribe(function (e, args) {
        grid.updateRowCount();
        grid.render();
    });

    dataView.onRowsChanged.subscribe(function (e, args) {
        grid.invalidateRows(args.rows);
        grid.render();
    });

    dataView.onPagingInfoChanged.subscribe(function (e, pagingInfo) {
        var isLastPage = pagingInfo.pageNum == pagingInfo.totalPages - 1;
        var enableAddRow = isLastPage || pagingInfo.pageSize == 0;
        var options = grid.getOptions();

        if (options.enableAddRow != enableAddRow) {
            grid.setOptions({enableAddRow: enableAddRow});
        }
    });

    $("#gridSearch").keyup(function (e) {
        // clear on Esc
        if (e.which == 27) {
          this.value = '';
        }
        searchString = this.value;
        updateFilter();
    });

    function updateFilter() {
        dataView.setFilterArgs({
            searchString: searchString
        });
        dataView.refresh();
    }

    dataView.beginUpdate();
    dataView.setItems(data);
    dataView.setFilterArgs({
        searchString: searchString
    });
    dataView.setFilter(searchFilter);
    dataView.endUpdate();

</script>

</%def>

<%def name="stylesheets()">
<link rel="stylesheet" href="/static/css/hgrid-base.css" type="text/css" />
</%def>

<%def name="javascript()">
<script src="/static/vendor/jquery-drag-drop/jquery.event.drag-2.2.js"></script>
<script src="/static/vendor/jquery-drag-drop/jquery.event.drop-2.2.js"></script>
<script src="/static/js/slickgrid.custom.min.js"></script>
</%def>
