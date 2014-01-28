// Wrap GitHub helper functions in module to exclude from global namespace

(function() {

    function noNullObj(obj) {
        var noNull = {};
        var keys = Object.keys(obj);
        for (var i=0; i<keys.length; i++) {
            if (obj[keys[i]])
                noNull[keys[i]] = obj[keys[i]];
        }
        return noNull;
    }

    function deleteRecursive(grid, item, init) {
        init = typeof(init) === 'undefined';
        if (init) {
            grid.Slick.dataView.beginUpdate();
        }
        var children = grid.getItemsByValue(grid.data, item.uid, 'parent_uid');
        for (var i=0; i<children.length; i++) {
            var child = children[i];
            if (child.type == 'folder') {
                deleteRecursive(grid, child, false);
            } else {
                grid.Slick.dataView.deleteItem(children[i].id);
            }
        }
        grid.Slick.dataView.deleteItem(item.id);
        if (init) {
            grid.Slick.dataView.endUpdate();
        }
    }

    function refreshGitHubTree(grid, item, branch) {
        var data = item.data || {};
        data.parent = item.parent_uid;
        data.branch = branch;
        $.ajax({
            type: 'get',
            url: item.lazyLoad + 'dummy/?' + $.param(noNullObj(data)),
            success: function(response) {
                deleteRecursive(grid, item);
                response._collapsed = true;
                // Hack: HGrid doesn't correctly rebuild the item's path in this
                // case. Should be fixed with @sloria's refactor.
                response.path = item.path;
                grid.addItem(response);
                grid.expandItem(response);
            }
        });
    }

    $(document).ready(function() {

        $('body').delegate('.github-branch-select', 'change', function() {
            var $this = $(this);
            var branch = $this.val();
            var cell = $this.closest('.slick-cell');
            var uid = cell
                .find('[data-hgrid-nav]')
                .attr('data-hgrid-nav');
            var item = myGrid.getItemByValue(myGrid.data, uid, 'uid');
            refreshGitHubTree(myGrid, item, branch);
        });

    });

})();
