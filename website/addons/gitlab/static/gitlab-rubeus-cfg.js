/**
 * Gitlab FileBrowser configuration module.
 */
(function(Rubeus) {

    // Private members

    function refreshGitLabTree(grid, item, branch) {
        var data = item.data || {};
        data.branch = branch;
        var url = item.urls.branch + '?' + $.param({branch: branch});
        $.ajax({
            type: 'get',
            url: url,
            success: function(data) {
                // Update the item with the new branch data
                $.extend(item, data[0]);
                grid.reloadFolder(item);
            }
        });
    }

    // Register configuration
    Rubeus.cfg.gitlab = {
        // Handle changing the branch select
        listeners: [{
            on: 'change',
            selector: '.gitlab-branch-select',
            callback: function(evt, row, grid) {
                var $this = $(evt.target);
                var branch = $this.val();
                refreshGitLabTree(grid, row, branch);
            }
        }]
    };

})(Rubeus);
