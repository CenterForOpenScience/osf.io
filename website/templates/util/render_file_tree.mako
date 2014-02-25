<div id="myGrid" class="filebrowser hgrid"></div>

<script type="text/javascript">
$(document).ready(function() {
    var filebrowser = new Rubeus('#myGrid', {
            data: nodeApiUrl + 'files/grid/',
            columns: [HGrid.Col.Name],
            uploads: false,
            width: "100%",
            height: 400
    });
});
</script>
