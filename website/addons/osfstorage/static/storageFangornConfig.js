;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['js/fangorn'], factory);
    } else if (typeof $script === 'function') {
        $script.ready('fangorn', function() { factory(Fangorn); });
    } else { factory(Fangorn); }
}(this, function(Fangorn) {

    /**
     * Build URL for a freshly uploaded file.
     */
    var buildUrl = function(parent, file, mode, suffix) {
        var base = mode === 'api' ? parent.nodeApiUrl : parent.nodeUrl;
        suffix = suffix !== undefined ? suffix : '/';
        return base + 'osfstorage/files/' + file.name + suffix;
    };

    Fangorn.config.osfstorage = {

        uploadMethod: 'PUT',
        uploadUrl: null,
        uploadAdd: function(file, item) {
            // var self = this;
            //console.log("HELLO");
            //var parent = item.parent().data;
            file.signedUrlFrom = item.data.urls.upload;
        },

        uploadSending: function(file, xhr, formData) {
            xhr.setRequestHeader(
                'Content-Type',
                file.type || 'application/octet-stream'
            );
        },

        uploadSuccess: function(file, item) {
            var self = this;
            var parent = item.parent().data; // self.getByID(row.parentID);
            item.data.urls = {
                'view': buildUrl(parent, file, 'web'),
                'download': buildUrl(parent, file, 'web', '/download/'),
                'delete': buildUrl(parent, file, 'api')
            };
            item.data.permissions = parent.permissions;
            //self.updateItem(row);
            // var updated = Rubeus.Utils.itemUpdated(row, parent);
            // if (updated) {
            //     self.changeStatus(row, Rubeus.Status.UPDATED);
            //     self.delayRemoveRow(row);
            // } else {
            //     self.changeStatus(row, Rubeus.Status.UPLOAD_SUCCESS, null, 2000,
            //         function(row) {
            //             self.showButtons(row);
            //         }
            //     );
            // }
            return item;
        },

        /**
         * Tornado probabilistically interrupts the connection with the client
         * when an error is raised in `prepare` or `data_received`. Detect the
         * disconnect event and a 409 and raise a more helpful error message.
         * See https://groups.google.com/forum/#!topic/python-tornado/-8GUVdSPp2k
         * for details.
         */
        uploadError: function(file, message) {
            if (message === 'Server responded with 0 code.' || message.indexOf('409') !== -1) {
                return 'Unable to upload file. Another upload with the ' +
                    'same name may be pending; please try again in a moment.';
            }
        }

    };

}));
