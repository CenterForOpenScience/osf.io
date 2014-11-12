;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['js/rubeus'], factory);
    } else if (typeof $script === 'function') {
        $script.ready('rubeus', function() { factory(Rubeus); });
    } else { factory(Rubeus); }
}(this, function(Rubeus) {

    /**
     * Build URL for a freshly uploaded file.
     */
    var buildUrl = function(parent, file, mode, suffix) {
        var base = mode === 'api' ? parent.nodeApiUrl : parent.nodeUrl;
        suffix = suffix !== undefined ? suffix : '/';
        return base + 'osfstorage/files/' + file.name + suffix;
    };

    Rubeus.cfg.osfstorage = {

        uploadMethod: 'PUT',
        uploadUrl: null,
        uploadAdded: function(file, item) {
            var self = this;
            var parent = self.getByID(item.parentID);
            file.signedUrlFrom = parent.urls.upload;
        },

        uploadSending: function(file, formData, xhr) {
            xhr.setRequestHeader(
                'Content-Type',
                file.type || 'application/octet-stream'
            );
        },

        uploadSuccess: function(file, row) {
            var self = this;
            var parent = self.getByID(row.parentID);
            row.urls = {
                'view': buildUrl(parent, file, 'web'),
                'download': buildUrl(parent, file, 'web', '/download/'),
                'delete': buildUrl(parent, file, 'api')
            };
            row.permissions = parent.permissions;
            self.updateItem(row);
            var updated = Rubeus.Utils.itemUpdated(row, parent);
            if (updated) {
                self.changeStatus(row, Rubeus.Status.UPDATED);
                self.delayRemoveRow(row);
            } else {
                self.changeStatus(row, Rubeus.Status.UPLOAD_SUCCESS, null, 2000,
                    function(row) {
                        self.showButtons(row);
                    }
                );
            }
        }

    };

}));
