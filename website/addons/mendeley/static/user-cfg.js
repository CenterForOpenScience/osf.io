/**
 * Created by lyndsy on 1/29/15.
 */
var $ = require('jquery');
var ko = require('knockout');

$(document).ready(function() {

    window.oauth_complete = function(success) {
        if(success) {
            console.log("successful auth");
        } else {
            console.log("bad auth");
        }
        console.log("Flow completed");
    }

    $('#mendeleyConnect').on('click', function() {
        window.open('/oauth/connect/mendeley/');
    });

    $('#githubDelKey').on('click', function() {
        bootbox.confirm({
            title: 'Remove access key?',
            message: 'Are you sure you want to remove your GitHub access key? This will ' +
                'revoke access to GitHub for all projects you have authorized ' +
                'and delete your access token from GitHub. Your OSF collaborators ' +
                'will not be able to write to GitHub repos or view private repos ' +
                'that you have authorized.',
            callback: function(result) {
                if(result) {
                    $.ajax({
                        url: '/api/v1/settings/github/oauth/',
                        type: 'DELETE',
                        success: function() {
                            window.location.reload();
                        }
                    });
                }
            }
        });
    });
});