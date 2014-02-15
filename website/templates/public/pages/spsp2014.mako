<%inherit file="base.mako"/>
<%def name="title()">FAQ</%def>
<%def name="content()">

<h2>SPSP 2014 Posters & Talks</h2>

<div id="grid" style="width:600px; height:600px;"></div>

<script type="text/javascript">

    var data = ${data};

    function tagsFormatter(row, cell, value, columnDef, dataContext) {
        return value.map(function(item) {
            return '<a href="' + item.url + '">' + item.label + '</a>';
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

    var columns = [
        {id: 'title', field: 'title', name: 'Title', sortable: true},
        {id: 'author', field: 'author', name: 'Author', sortable: true},
        {id: 'tags', field: 'tags', name: 'Tags', formatter: tagsFormatter},
        {id: 'download', field: 'download', name: 'Download', formatter: downloadFormatter}
    ];

    var options = {
        forceFitColumns: true
    };

    var grid = new Slick.Grid('#grid', data, columns, options);

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
