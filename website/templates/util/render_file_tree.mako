<div id="filetreeProgressBar" class="progress progress-striped active">
    <div class="progress-bar"  role="progressbar" aria-valuenow="100" aria-valuemin="0" aria-valuemax="100" style="width: 100%">
        <span class="sr-only">Loading</span>
    </div>
</div>

<div id="myGrid" class="filebrowser hgrid"></div>

<script type="text/javascript">
$(document).ready(function() {
    var filebrowser = new Rubeus('#myGrid', {
            data: nodeApiUrl + 'files/grid/',
            columns: [HGrid.Col.Name],
            uploads: false,
            width: "100%",
            height: 600,
            progBar: '#filetreeProgressBar'
    });
});
</script>
