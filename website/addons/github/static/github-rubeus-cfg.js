/**
 * Github FileBrowser configuration module.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['js/rubeus'], factory);
    } else if (typeof $script === 'function') {
        $script.ready('rubeus', function() { factory(Rubeus); });
    } else { factory(Rubeus); }
}(this, function(Rubeus) {

    // Private members

    function refreshGitHubTree(grid, item, branch) {
        var data = item.data || {};
        data.branch = branch;
        var url = item.urls.branch + '?' + $.param({branch: branch});
        $.ajax({
            type: 'get',
            url: url
        }).done(function(response) {
            // Update the item with the new branch data
            $.extend(item, response[0]);
            grid.reloadFolder(item);
            //item.data = //what is returned
            d


        });
    }

//"
//            <select class="github-branch-select">
//                    <option value="develop" >develop</option>
//                    <option value="feature/add" >feature/add</option>
//                    <option value="feature/add_fa" >feature/add_fa</option>
//                    <option value="feature/bower" >feature/bower</option>
//                    <option value="feature/drag_and_drop" >feature/drag_and_drop</option>
//                    <option value="feature/dropzone" >feature/dropzone</option>
//                    <option value="feature/filter" >feature/filter</option>
//                    <option value="feature/icons" >feature/icons</option>
//                    <option value="feature/lazyload" >feature/lazyload</option>
//                    <option value="feature/move" >feature/move</option>
//                    <option value="feature/onhover" >feature/onhover</option>
//                    <option value="feature/pagination" >feature/pagination</option>
//                    <option value="feature/sorting" >feature/sorting</option>
//                    <option value="feature/style" >feature/style</option>
//                    <option value="feature/tests" >feature/tests</option>
//                    <option value="feature/visibleIndexes" >feature/visibleIndexes</option>
//                    <option value="hotfix/add-mithril" >hotfix/add-mithril</option>
//                    <option value="hotfix/fix_pagination" >hotfix/fix_pagination</option>
//                    <option value="hotfix/openlevel" >hotfix/openlevel</option>
//                    <option value="master" selected>master</option>
//            </select>
//        <a href="https://github.com/caneruguz/treebeard/commit/e2ede792bf963a11f483cf7dae44a405121ee849" target="_blank" class="github-sha text-muted">e2ede792bf</a>
//"

    // Register configuration
    Rubeus.cfg.github = {
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

    // Define HGrid Button Actions
    HGrid.Actions['githubDownloadZip'] = {
        on: 'click',
        callback: function (evt, row) {
            var url = row.urls.zip;
            window.location = url;
        }
    };

    HGrid.Actions['githubVisitRepo'] = {
        on: 'click',
        callback: function (evt, row) {
            var url = row.urls.repo;
            window.location = url;
        }
    };

}));
