<% import json %>
<div id="myGrid" class="filebrowser hgrid"></div>

<script type="text/javascript">
$(document).ready(function() {
    (function(global) {

    // Don't show dropped content if user drags outside grid
    global.ondragover = function(e) { e.preventDefault(); };
    global.ondrop = function(e) { e.preventDefault(); };

    var gridData = ${json.dumps(grid_data)};
    global.filebrowser = new Rubeus('#myGrid', {
        data: gridData, columns: [HGrid.Col.Name],
        uploads: false, width: "100%", height: 400
        // searchInput: '#searchInput'
    });

    })(window);

});

</script>
