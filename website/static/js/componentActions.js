'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');

var ComponentActions = {};

ComponentActions.deleteNode = function(childExists, nodeType, nodeApiUrl) {

    if(childExists){
        $osf.growl(
            'Error',
            'Any child components must be deleted prior to deleting this component.',
            'danger',
            30000
        );
    } else {
        // It's possible that the XHR request for contributors has not finished before getting to this
        // point; only construct the HTML for the list of contributors if the contribs list is populated
        var message = '<p>It will no longer be available to other contributors on the project.' +

        $osf.confirmDangerousAction({
            title: 'Are you sure you want to delete this ' + nodeType + '?',
            message: message,
            callback: function () {
                var request = $.ajax({
                    type: 'DELETE',
                    dataType: 'json',
                    url: nodeApiUrl
                });
                request.done(function(response) {
                    // Redirect to either the parent project or the dashboard
                    window.location.href = response.url;
                });
                request.fail($osf.handleJSONError);
            },
            buttons: {
                success: {
                    label: 'Delete'
                }
            }
        });
    }
};

window.ComponentActions = ComponentActions;
module.exports = ComponentActions;
