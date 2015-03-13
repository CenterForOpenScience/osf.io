var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var $osf = require('osfHelpers');

var ProjectSettings = {};


// Request the first 5 contributors, for display in the deletion modal
var contribs = [];
var moreContribs = 0;

var contribURL = nodeApiUrl + 'get_contributors/?limit=5';
var request = $.ajax({
    url: contribURL,
    type: 'get',
    dataType: 'json'
});
request.done(function(response) {
    var currentUserName = window.contextVars.currentUser.fullname;
    contribs = response.contributors.filter(function(contrib) {
        return contrib.shortname !== currentUserName;
    });
    moreContribs = response.more;
});
request.fail(function(xhr, textStatus, err) {
    Raven.captureMessage('Error requesting contributors', {
        url: contribURL, textStatus: textStatus, err: err,
    });
});


/**
    * Pulls a random name from the scientist list to use as confirmation string
*  Ignores case and whitespace
*/
ProjectSettings.getConfirmationCode = function(nodeType) {
    var message = '<p>It will no longer be available to other contributors on the project.';

    // It's possible that the XHR request for contributors has not finished before getting to this
    // point; only construct the HTML for the list of contributors if the contribs list is populated
    console.log(contribs);
    if (contribs.length) {
        message += ' These include:<ul>';
        $.each(contribs, function(i, b){
            message += '<li>' + b.fullname + '</li>';
        });
        message += '</ul>';

        if (moreContribs) {
            message += '<p>and <strong>' + moreContribs + '</strong> others.';
        }
        message += '</p>';
    }

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
        }
    });
};

module.exports = ProjectSettings;
