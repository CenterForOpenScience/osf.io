/**
 * Github FileBrowser configuration module.
 */
(function(FileBrowser) {

    // Private members

    // FIXME: This doesn't work yet.
    function refreshGitHubTree(grid, item, branch) {
        var parentID = item.parentID;
        var data = item.data || {};
        data.branch = branch;
        var url = item.urls.branch + '?' + $.param({branch: branch});
        $.ajax({
            type: 'get',
            url: url,
            success: function(response) {
                console.log(response);
                grid.emptyFolder(item, true);
                parentID = response.parentID;
                grid.addData([response], parentID);
            }
        });
    }

    // Register configuration
    FileBrowser.cfg.github = {
        listeners: [{
            on: 'change',
            selector: '.github-branch-select',
            callback: function(evt, row, grid) {
                var $this = $(evt.target);
                var id = row.id;
                var item = grid.getByID(id);
                var branch = $this.val();
                refreshGitHubTree(grid, item, branch);
            }
        }],
        uploadAdded: function(file, row) {
            console.log(row);
        }

    };

})(FileBrowser);
