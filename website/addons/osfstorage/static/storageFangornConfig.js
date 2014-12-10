var Fangorn = require('fangorn');

/**
 * Build URL for a freshly uploaded file.
 */
 var m = require('mithril'); 

var Fangorn = require('fangorn'); 

var buildUrl = function(parent, file, mode, suffix) {
    var base = mode === 'api' ? parent.nodeApiUrl : parent.nodeUrl;
    suffix = suffix !== undefined ? suffix : '/';
    return base + 'osfstorage/files/' + file.name + suffix;
};

Fangorn.config.osfstorage = {
    uploadMethod: 'PUT',
    uploadUrl: null,
    uploadAdd: function(file, item) {
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
            'download': buildUrl(parent, file, 'web', '?action=download'),
            'delete': buildUrl(parent, file, 'api')
        };
        item.data.downloads = 0;  // This does not update download is a previously deleted file is downloaded. 
        console.log("parent permissions", parent.permissions);
        item.data.permissions = parent.permissions;
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