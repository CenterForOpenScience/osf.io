/**
 * Dataverse FileBrowser configuration module.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['js/rubeus'], factory);
    } else if (typeof $script === 'function') {
        $script.ready('rubeus', function() { factory(Rubeus); });
    } else { factory(Rubeus); }
}(this, function(Rubeus) {

    // Private members

    function refreshDataverseTree(grid, item, branch) {
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
    Rubeus.cfg.dataverse = {
        // Handle changing the branch select
        listeners: [{
            on: 'change',
            selector: '.dataverse-branch-select',
            callback: function(evt, row, grid) {
                var $this = $(evt.target);
                var branch = $this.val();
                refreshDataverseTree(grid, row, branch);
            }
        }]
    };

}));
