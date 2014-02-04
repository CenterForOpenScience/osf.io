
(function(FileBrowser) {

    // Private stuff

    // Public stuff
    FileBrowser.cfg.s3 = {

        headers: {
            'x-amz-acl': 'private'
        },

        uploadMethod:'PUT',

        uploadAdded: function(file, item) {
            var deferred = $.Deferred();
            var self = this;
            return $.ajax({
                type: 'POST',
                url: nodeApiUrl + 's3/upload/',
                data: JSON.stringify({name: file.name, type: file.type}),
                contentType: 'application/json',
                dataType: 'json'
            }).success(function (url) {
                deferred.resolve(url);
                self.dropzone.options.url = url;
                console.log(self.dropzone.options.url);
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
