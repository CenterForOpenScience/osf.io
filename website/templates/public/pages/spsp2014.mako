<%inherit file="base.mako"/>
<%def name="title()">SPSP 2014</%def>
<%def name="content()">

<h2 style="padding-bottom: 30px;">SPSP 2014 Posters & Talks</h2>

<div><a href="http://cos.io/spsp/">Add your poster or talk</a></div>
<div style="padding-bottom: 30px;">Search results by title or author: <input id="gridSearch" /></div>
<div id="grid" style="width: 100%;"></div>

<script type="text/javascript">

    var data = ${data};

    function titleFormatter(row, cell, value, columnDef, dataContext) {
        return '<a target="_blank" href="' + dataContext.nodeUrl + '">' +
            value +
        '</a>';
    }

    function authorFormatter(row, cell, value, columnDef, dataContext) {
        if (value) {
            return '<a target="_blank" href="' + dataContext.authorUrl + '">' +
                value +
            '</a>';
        }
        return '';
    }

    function downloadFormatter(row, cell, value, columnDef, dataContext) {
        if (dataContext.downloadUrl) {
            return '<a href="' + dataContext.downloadUrl + '">' +
                '<button class="btn btn-success btn-mini" style="margin-right: 10px;">' +
                    '<i class="icon-download-alt icon-white"></i>' +
                '</button>' +
            '</a>&nbsp;' + value;
        } else {
            return '';
        }
    }

    function searchFilter(item, args) {
        if (args.searchString == '') {
            return true;
        }
        if (item.title.toLowerCase().indexOf(args.searchString) != -1 ||
                item.author.toLowerCase().indexOf(args.searchString) != -1) {
            return true;
        }
        return false;
    }

    var columns = [
        {id: 'title', field: 'title', name: 'Title', width: 400, sortable: true, formatter: titleFormatter},
        {id: 'author', field: 'author', name: 'Author', width: 100, formatter: authorFormatter, sortable: true},
        {id: 'category', field: 'category', name: 'Category', width: 100, sortable: true},
        {id: 'download', field: 'download', name: 'Downloads', width: 100, sortable: true, formatter: downloadFormatter}
    ];

    var options = {
        autoHeight: true,
        forceFitColumns: true
    };

    var dataView = new Slick.Data.DataView({inlineFilters: true});
    var grid = new Slick.Grid('#grid', dataView, columns, options);
    var searchString = '';

    function sortView(field, sortAsc) {
        function comparator(a, b) {
            return a[field] > b[field] ? 1 :
                   a[field] < b[field] ? -1 :
                   0;
        }
        dataView.sort(comparator, sortAsc);
        dataView.refresh();
    }

    grid.onSort.subscribe(function(e, args) {
        sortView(args.sortCol.field, args.sortAsc)
    });

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
        searchString = this.value.toLowerCase();
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

    // Sort by title by default
    sortView('title', true);

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
