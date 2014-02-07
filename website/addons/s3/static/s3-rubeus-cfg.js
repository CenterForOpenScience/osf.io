
(function(Rubeus) {

    Rubeus.cfg.s3 = {

        uploadMethod: 'PUT',
        uploadUrl: null,
        uploadAdded: function(file, item) {
            var self = this;
            var parent = self.getByID(item.parentID);
            var name = file.name;
            // Make it possible to upload into subfolders
            while (parent.depth > 1 && !parent.isComponent) {
                name = parent.name + '/' + name;
                parent = self.getByID(parent.parentID);
            }
            file.destination = name;
            self.dropzone.options.signedUrlFrom = parent.urls.upload;
        },

        uploadSending: function(file, formData, xhr) {
            xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
            xhr.setRequestHeader('x-amz-acl', 'private');
        },

        uploadSuccess: function(file, item, data) {
            // FIXME: need to update the item with new data, but can't do that
            // from the returned data from S3
        }
    };

})(Rubeus);
