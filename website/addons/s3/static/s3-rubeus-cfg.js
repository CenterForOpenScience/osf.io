    var Rubeus = require('rubeus');

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

        uploadSuccess: function(file, row) {
            var self = this;
            var parent = this.getByID(row.parentID);
            row.urls = {
                'delete': parent.nodeApiUrl + 's3/' + file.destination + '/',
                'download': parent.nodeUrl + 's3/' + file.destination + '/download/',
                'view': parent.nodeUrl + 's3/' + file.destination + '/'
            };
            row.permissions = parent.permissions;
            this.updateItem(row);
            var updated = Rubeus.Utils.itemUpdated(row, parent);
            if (updated) {
                self.changeStatus(row, Rubeus.Status.UPDATED);
                self.delayRemoveRow(row);
            } else {
                self.changeStatus(row, Rubeus.Status.UPLOAD_SUCCESS, null, 2000,
                    function(row) {
                        self.showButtons(row);
                    });
            }
        }
    };

