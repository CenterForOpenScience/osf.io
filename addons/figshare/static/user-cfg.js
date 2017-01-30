var $ = require('jquery');
var bootbox = require('bootbox');
var language = require('js/osfLanguage').Addons.figshare;
require('js/osfToggleHeight')

 $(document).ready(function() {
        $('#figshare-header').osfToggleHeight({height: 150});

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