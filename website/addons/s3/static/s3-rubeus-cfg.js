;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['js/rubeus'], factory);
    } else if (typeof $script === 'function') {
        $script.ready('rubeus', function() { factory(Rubeus); });
    } else { factory(Rubeus); }
}(this, function(Rubeus) {

    Rubeus.cfg.s3 = {

        uploadMethod: 'PUT',
        uploadUrl: null,
        uploadAdded: function(file, item) {
            var self = this;
            var parent = self.getByID(item.parentID);
            var name = file.name;
            // Make it possible to upload into subfolders
            while (parent.depth > 1 && !parent.isAddonRoot) {
                name = parent.name + '/' + name;
                parent = self.getByID(parent.parentID);
            }
            file.destination = name;
            file.signedUrlFrom = parent.urls.upload;
        },

        uploadSending: function(file, formData, xhr) {
            xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');
            xhr.setRequestHeader('x-amz-acl', 'private');
        },

        uploadSuccess: function(file, item, data) {
            // Update the added item's urls and permissions
            var parent = this.getByID(item.parentID);
            item.urls = {
                'delete': parent.nodeApiUrl + 's3/' + file.destination + '/',
                'download': parent.nodeUrl + 's3/' + file.destination + '/download/',
                'view': parent.nodeUrl + 's3/' + file.destination + '/'
            };
            item.permissions = parent.permissions;
            this.updateItem(item);
            this.changeStatus(item, Rubeus.Status.UPLOAD_SUCCESS, 2000);
        }
    };

}));
