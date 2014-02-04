
(function(FileBrowser) {

    // Private stuff

    // Public stuff
    FileBrowser.cfg.github = {
        uploadMethod = 'PUT';
        //TODO can this be moved up a level?
        fileName = '';
        mimeType = '';
        uploadUrl: function(row) {
            var deferred = $.Deferred();

            return $.ajax({
                type: 'POST',
                url: nodeApiUrl + '/s3/upload/',
                data: JSON.stringify({name: fileName, type:mimeType}),
                contentType: 'application/json',
                dataType: 'json'
            }).success(function (url) {
                deferred.resolve(url);
            });
        }

        uploadAdded: function(file, item) {
            fileName = file.name;
            mimeType = file.type;
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
