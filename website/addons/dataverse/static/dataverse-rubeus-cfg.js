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

    function getCitation(item) {
        bootbox.alert(
            '<div class="col-md-3"><b>Title: </b></div>' +
                '<div class="col-md-8">' + item.study + '</div><br>' +
            '<div class="col-md-3"><b>Study Global ID: </b></div>' +
                '<div class="col-md-8">' +
                '<a href="http://dx.doi.org/' + item.doi.split(":")[1] + '">' +
                item.doi + '</a></div><br>' +
            '<div class="col-md-3"><b>Dataverse: </b></div>' +
                '<div class="col-md-8">' + item.dataverse + '</div><br>' +
            '<div class="col-md-3" style="padding-top: 10px;"><b>Citation: </b></div>' +
                '<div class="col-md-8" style="padding-top: 10px;">' + item.citation + '</div><br>'
        )
    }

    function releaseStudy(item) {
        var url = item.urls.release;
        bootbox.confirm(
            'By releasing this study, all content will be ' +
                'made available through the Harvard Dataverse using their ' +
                'internal privacy settings, regardless of your OSF project ' +
                'settings. Are you sure you want to release this study?',
            function(result) {
                if (result) {
                    $.ajax({
                        url: url,
                        type: 'POST',
                        contentType: 'application/json',
                        dataType: 'json',
                    }).success(function() {
                        bootbox.alert('Your study has been released. Please ' +
                        'allow up to 24 hours for the released version to ' +
                        'appear on your OSF project\'s file page.');
                    }).fail( function(args) {
                        var message = args.responseJSON.code == 400 ?
                            'Error: Something went wrong when attempting to ' +
                            'release your study.' :
                            'Error: This version has already been released.'
                        bootbox.alert(message);
                    });
                }
            }
        )
    }

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
            },
            {
                on: 'click',
                selector: '#dataverseReleaseStudy',
                callback: function(evt, row) {
                    releaseStudy(row)
                }
            },
            {
                on: 'click',
                selector: '#dataverseGetCitation',
                callback: function(evt, row) {
                    getCitation(row)
                }
            },
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
        }
    };

}));
