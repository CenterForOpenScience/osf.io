
(function(FileBrowser) {

    // Private stuff
console.log('S3 settings loaded')
    // Public stuff
    FileBrowser.cfg.s3 = {

        uploadMethod: function(row){return 'PUT';},

        uploadAdded: function(file, item) {
            var deferred = $.Deferred();
            var self = this;
            console.log(this.dropzone.url);
            return $.ajax({
                type: 'POST',
                url: nodeApiUrl + 's3/upload/',
                data: JSON.stringify({name: file.name, type: file.type}),
                contentType: 'application/json',
                dataType: 'json',
                async: false
            }).success(function (url) {
                deferred.resolve(url);
                self.dropzone.options.url = url;
            });
        },

        uploadSending: function(file, formData, xhr) {
            console.log('Called');
            xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
            xhr.setRequestHeader('x-amz-acl', 'private');
        }


    };

})(FileBrowser);
