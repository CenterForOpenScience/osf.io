
(function(Rubeus) {

    Rubeus.cfg.s3 = {

        uploadMethod: null,
        uploadUrl: null,

        uploadAdded: function(file, item) {
            var self = this;
            var parent = this.getByID(item.parentID);
            var name = file.name;
            while (parent.depth > 1 && !parent.isComponent) {
                name = parent.name + '/' + name;
                parent = this.getByID(parent.parentID);
            }
            this.dropzone.options.signedUrl = parent.urls.upload;
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
