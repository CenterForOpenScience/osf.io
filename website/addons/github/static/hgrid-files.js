// Wrap GitHub helper functions in module to exclude from global namespace

(function(FileBrowser) {

    // Private stuff

    // Public stuff
    FileBrowser.cfg.github = {
        listeners: [
            {
                on: 'change',
                selector: '.github-branch-select',
                callback: function(){}
            }
        ],
        uploadUrl: function(row) {
            return $.ajax({
                type: 'get',
                url: '/path/to/signed/link',
            });
        }
    };

})(FileBrowser);

(function() {

    function refreshGitHubTree(grid, item, branch) {
        var parentID = item.parentID;
        var data = item.data || {};
        data.branch = branch;
        $.ajax({
            type: 'get',
            url: item.lazyLoad + 'dummy/?branch=' + branch,
            success: function(response) {
                grid.removeFolder(item);
                response.parentID = parentID;
                grid.addItem(response);
                grid.expandItem(response);
            }
        });
    }

    $(document).ready(function() {

        $('body').delegate('.github-branch-select', 'change', function() {
            var $this = $(this);
            var id = $this.closest('.hg-item-content').attr('data-id');
            var item = grid.getByID(id);
            var branch = $this.val();
            refreshGitHubTree(grid, item, branch);
        });

    });

})();
