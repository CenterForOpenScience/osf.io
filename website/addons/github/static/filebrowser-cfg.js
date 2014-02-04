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
        $.ajax({
            type: 'get',
            url: item.lazyLoad + 'dummy/?branch=' + branch,
            success: function(response) {
                grid.emptyFolder(item);
                response.parentID = parentID;
                grid.addItem(response);
                grid.expandItem(response);
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

    };

})(FileBrowser);
