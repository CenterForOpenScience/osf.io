var bootbox = require('bootbox');
var $ = require('jquery');
var language = require('js/osfLanguage').Addons.github;

$(document).ready(function() {

    $('#githubAddKey').on('click', function() {
        window.location.href = '/api/v1/settings/github/oauth/';
    });

    $('#githubDelKey').on('click', function() {
        bootbox.confirm({
            title: 'Disconnect GitHub Account?',
            message: language.confirmDeauth,
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
            },
            buttons:{
                confirm:{
                    label:'Disconnect',
                    className:'btn-danger'
                }
            }
        });
    });
});