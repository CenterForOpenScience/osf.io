
(function(FileBrowser) {

    // Private stuff

    // Public stuff
    FileBrowser.cfg.s3 = {
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
        uploadMethod:'PUT',

        uploadAdded: function(file, item) {
            console.log('Called up')
            var deferred = $.Deferred();
            console.log(file)
            return $.ajax({
                type: 'POST',
                url: nodeApiUrl + 's3/upload/',
                data: JSON.stringify({name: file.name, type: file.type}),
                contentType: 'application/json',
                dataType: 'json'
            }).success(function (url) {
                deferred.resolve(url);
                this.dropzone.options.uploadUrl = deferred;
            });
        }
    };

})(FileBrowser);

/*
 *
 * xhr.setRequestHeader('Content-Type', type);
 * xhr.setRequestHeader('x-amz-acl', 'private');
 *
 *
 */
