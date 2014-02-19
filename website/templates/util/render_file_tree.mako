<div id="myGrid" class="filebrowser hgrid"></div>

<script type="text/javascript">
$(document).ready(function() {
    (function(global) {
        var gridData = ${grid_data};
        filebrowser = new Rubeus('#myGrid', {
            data: gridData,
            columns: [HGrid.Col.Name],
            uploads: false,
            width: "100%",
            height: 400
        });
    })(window);
});
</script>
