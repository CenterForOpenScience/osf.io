
(function(FileBrowser) {

    // Private stuff

    // Public stuff
    FileBrowser.cfg.s3 = {
        uploadMethod = 'PUT';

        uploadAdded: function(file, item) {
            var deferred = $.Deferred();

            return $.ajax({
                type: 'POST',
                url: nodeApiUrl + '/s3/upload/',
                data: JSON.stringify({name: file.name, type: file.type}),
                contentType: 'application/json',
                dataType: 'json'
            }).success(function (url) {
                deferred.resolve(url);
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
