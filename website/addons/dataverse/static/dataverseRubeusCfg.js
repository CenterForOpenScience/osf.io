/**
* Dataverse FileBrowser configuration module.
*/

var $ = require('jquery');
var HGrid = require('hgrid');
var Rubeus = require('rubeus');
var bootbox = require('bootbox');
var osfHelpers = require('osfHelpers');

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
HGrid.Actions['publishDataset'] = {
    on: 'click',
    callback: function (evt, row) {
        var self = this;
        var url = row.urls.publish;
        bootbox.confirm({
            title: 'Publish this dataset?',
            message: 'By publishing this dataset, all content will be ' +
                'made available through the Harvard Dataverse using their ' +
                'internal privacy settings, regardless of your OSF project ' +
                'settings. Are you sure you want to publish this dataset?',
            callback: function(result) {
                if(result) {
                    self.changeStatus(row, Rubeus.Status.PUBLISHING_DATASET);
                    osfHelpers.putJSON(
                        url,
                        {}
                    ).done(function() {
                        osfHelpers.growl('Your dataset has been published.',
                                'Please allow up to 24 hours for the published version to ' +
                                'appear on your OSF project\'s file page.',
                            'success');
                        self.updateItem(row);
                    }).fail( function(args) {
                        var message = args.responseJSON.code === 400 ?
                            'Something went wrong when attempting to ' +
                            'publish your dataset.' :
                            'This version has already been published.';
                        osfHelpers.growl('Error', message);
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
