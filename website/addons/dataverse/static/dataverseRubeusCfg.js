/**
 * Dataverse FileBrowser configuration module.
 */
;(function (global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['js/rubeus'], factory);
    } else if (typeof $script === 'function') {
        $script.ready('rubeus', function() { factory(Rubeus); });
    } else { factory(Rubeus); }
}(this, function(Rubeus) {

    // Private members
    function refreshDataverseTree(grid, item, state) {
        var data = item.data || {};
        data.state = state;
        var url = item.urls.state + '?' + $.param({state: state});
        $.ajax({
            type: 'get',
            url: url,
            success: function(data) {
                // Update the item with the new state data
                $.extend(item, data[0]);
                grid.reloadFolder(item);
            }
        });
    }

    // Define HGrid Button Actions
    HGrid.Actions['releaseStudy'] = {
        on: 'click',
        callback: function (evt, row) {
            var self = this;
            var url = row.urls.release;
            bootbox.confirm({
                title: 'Release this study?',
                message: 'By releasing this study, all content will be ' +
                    'made available through the Harvard Dataverse using their ' +
                    'internal privacy settings, regardless of your OSF project ' +
                    'settings. Are you sure you want to release this study?',
                callback: function(result) {
                    if(result) {
                        self.changeStatus(row, Rubeus.Status.RELEASING_STUDY);
                        $.osf.putJSON(
                            url,
                            {}
                        ).done(function() {
                            $.osf.growl('Your study has been released.',
                                    'Please allow up to 24 hours for the released version to ' +
                                    'appear on your OSF project\'s file page.',
                                'success');
                            self.updateItem(row);
                        }).fail( function(args) {
                            var message = args.responseJSON.code === 400 ?
                                'Something went wrong when attempting to ' +
                                'release your study.' :
                                'This version has already been released.';
                            $.osf.growl('Error', message);
                            self.updateItem(row);
                        });
                    }
                }
            });
        }
    };

    // Register configuration
    Rubeus.cfg.dataverse = {
        // Handle events
        listeners: [
            {
                on: 'change',
                selector: '.dataverse-state-select',
                callback: function(evt, row, grid) {
                    var $this = $(evt.target);
                    var state = $this.val();
                    refreshDataverseTree(grid, row, state);
                }
            }
        ],
        // Update file information for updated files
        uploadSuccess: function(file, row, data) {
            if (data.actionTaken === 'file_updated') {
                var gridData = this.getData();
                for (var i=0; i < gridData.length; i++) {
                    var item = gridData[i];
                    if (item.file_id && data.old_id &&
                        item.file_id === data.old_id) {
                        $.extend(item, data);
                        this.updateItem(item);
                    }
                }
            }
        },
        UPLOAD_ERROR: '<span class="text-danger">The Dataverse could ' +
                        'not accept your file at this time. </span>'
    };

}));
