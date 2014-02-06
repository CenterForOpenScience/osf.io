/**
 * Github FileBrowser configuration module.
 */
(function(FileBrowser) {

    // Private members

    function refreshGitHubTree(grid, item, branch) {
        var parentID = item.parentID;
        var data = item.data || {};
        data.branch = branch;
        var url = item.urls.branch + '?' + $.param({branch: branch});
        $.ajax({
            type: 'get',
            url: url,
            success: function(data) {
                // Update the item with the new branch data
                $.extend(item, data);
                grid.reloadFolder(item);
            }
        });
    }

    // Register configuration
    FileBrowser.cfg.github = {
        // Handle changing the branch select
        listeners: [{
            on: 'change',
            selector: '.github-branch-select',
            callback: function(evt, row, grid) {
                var $this = $(evt.target);
                var branch = $this.val();
                refreshGitHubTree(grid, row, branch);
            }
        }]
    };

})(FileBrowser);
