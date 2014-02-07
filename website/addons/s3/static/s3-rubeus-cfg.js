
(function(Rubeus) {

    // Private stuff

    // Public stuff
    Rubeus.cfg.s3 = {

        uploadMethod: 'PUT',

        uploadAdded: function(file, item) {
            var deferred = $.Deferred();
            var self = this;
            var parent = this.getByID(item.parentID);
            var name = file.name;

            while (parent.depth > 1 && !parent.isComponent) {
                name = parent.name + '/' + name;
                parent = this.getByID(parent.parentID);
            }
            return $.ajax({
                type: 'POST',
                url: parent.urls.upload,//nodeApiUrl + 's3/upload/',
                data: JSON.stringify({name: name, type: file.type || 'application/octet-stream'}),
                contentType: 'application/json',
                dataType: 'json'
            }).success(function (url) {
                deferred.resolve(url);
                self.dropzone.options.url = url;
                self.dropzone.emit('processing');
            });
        },

        uploadSending: function(file, formData, xhr) {
            xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
            xhr.setRequestHeader('x-amz-acl', 'private');
        }
    };

})(Rubeus);
