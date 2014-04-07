<!-- SlickGrid CSS -->
<link rel="stylesheet" href="${STATIC_PATH}/tabular/css/slick.grid.css" type="text/css"/>
<link rel="stylesheet" href="${STATIC_PATH}/tabular/css/jquery-ui-1.8.16.custom.css" type="text/css"/>
<link rel="stylesheet" href="${STATIC_PATH}/tabular/css/examples.css" type="text/css"/>
<link rel="stylesheet" href="${STATIC_PATH}/tabular/css/slick-default-theme.css" type="text/css"/>

<!-- SlickGrid JS -->
<script src="${STATIC_PATH}/tabular/js/jquery.event.drag-2.2.js"></script>
<script src="${STATIC_PATH}/tabular/js/slick.core.js"></script>
<script src="${STATIC_PATH}/tabular/js/slick.grid.js"></script>
<div class="mfr-message">${writing}</div>

<div id="mfrGrid" class="mfr-slickgrid"></div>

<script>
(function(){
    var columns = ${columns};
    var rows = ${rows};

##todo make this based on the size of the window instead of hardcoded in -ajs
    if(columns.length < 9){
    var options = {
        enableCellNavigation: true,
        enableColumnReorder: false,
        forceFitColumns: true,
        syncColumnCellResize: true
    };
    }else{
    var options = {
        enableCellNavigation: true,
        enableColumnReorder: false,
        syncColumnCellResize: true
    };
    }

    var grid = new Slick.Grid("#mfrGrid", rows, columns, options);
})();
</script>