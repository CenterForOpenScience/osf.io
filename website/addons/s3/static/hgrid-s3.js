
(function(FileBrowser) {

    // Private stuff
console.log('S3 settings loaded')
    // Public stuff
    FileBrowser.cfg.s3 = {

        uploadMethod: function(row){return 'PUT';},

        uploadAdded: function(file, item) {
            var deferred = $.Deferred();
            var self = this;
            var parent = this.getByID(item.parentID);
            var name = file.name;
            while (parent.depth > 1) {
                name = parent.name + '/' + name;
                parent = this.getByID(parent.parentID);
            }
            return $.ajax({
                type: 'POST',
                url: nodeApiUrl + 's3/upload/',
                data: JSON.stringify({name: name, type: file.type}),
                contentType: 'application/json',
                dataType: 'json',
                async: false
            }).success(function (url) {
                deferred.resolve(url);
                self.dropzone.options.url = url;
            });
        },

        uploadSending: function(file, formData, xhr) {
            xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
            xhr.setRequestHeader('x-amz-acl', 'private');
        },

        uploadSuccess: function(file, item, data) {
            //Build nolonger dummy file here
            console.log(file);
            console.log(item);
            console.log(data);

        }

    };

})(FileBrowser);
