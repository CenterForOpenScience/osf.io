

var $ = require('jquery');
var AddonHelper = require('js/addonHelper');
$(document).ready(function() {

        $('#figshareAddKey').on('click', function() {
                window.location.href = '/api/v1/settings/figshare/oauth/';
        });

        $('#figshareDelKey').on('click', function() {
            bootbox.confirm({
                title: 'Disconnect figshare Account?',
                message: language.confirmDeauth,
                callback: function(result) {
                    if(result) {
                        $.ajax({
                            url: '/api/v1/settings/figshare/oauth/',
                            type: 'DELETE',
                            contentType: 'application/json',
                            dataType: 'json',
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