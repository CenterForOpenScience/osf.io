var $ = require('jquery');
var Slick = window.Slick;

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
    if (args.searchString === '') {
        return true;
    }
    if (item.title.toLowerCase().indexOf(args.searchString) !== -1 ||
            item.author.toLowerCase().indexOf(args.searchString) !== -1) {
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

function Meeting(data) {

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
        sortView(args.sortCol.field, args.sortAsc);
    });

    dataView.onRowCountChanged.subscribe(function () {
        grid.updateRowCount();
        grid.render();
    });

    dataView.onRowsChanged.subscribe(function (e, args) {
        grid.invalidateRows(args.rows);
        grid.render();
    });

    dataView.onPagingInfoChanged.subscribe(function (e, pagingInfo) {
        var isLastPage = pagingInfo.pageNum === pagingInfo.totalPages - 1;
        var enableAddRow = isLastPage || pagingInfo.pageSize === 0;
        var options = grid.getOptions();
        if (options.enableAddRow !== enableAddRow) {
            grid.setOptions({enableAddRow: enableAddRow});
        }
    });

    function updateFilter() {
        dataView.setFilterArgs({
            searchString: searchString
        });
        dataView.refresh();
    }

    $('#gridSearch').keyup(function (e) {
        // clear on Esc
        if (e.which === 27) {
            this.value = '';
        }
        searchString = this.value.toLowerCase();
        updateFilter();
    });

    dataView.beginUpdate();
    dataView.setItems(data);
    dataView.setFilterArgs({
        searchString: searchString
    });
    dataView.setFilter(searchFilter);
    dataView.endUpdate();

    // Sort by title by default
    sortView('title', true);

}

module.exports = Meeting;
