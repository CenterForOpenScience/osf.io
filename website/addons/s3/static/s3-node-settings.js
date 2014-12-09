var $osf = require('osf-helpers');
var bootbox = require('bootbox');
var $ = require('jquery');

(function() {

    function newBucket() {
        var isValidBucket = /^(?!.*(\.\.|-\.))[^.][a-z0-9\d.-]{2,61}[^.]$/;
        var $elm = $('#addonSettingsS3');
        var $select = $elm.find('select');

        bootbox.prompt('Name your new bucket', function(bucketName) {

            if (!bucketName) {
                return;
            } else if (isValidBucket.exec(bucketName) == null) {
                bootbox.confirm({
                    title: 'Invalid bucket name',
                    message: "Sorry, that's not a valid bucket name. Try another name?",
                    callback: function(result) {
                        if(result) {
                            newBucket();
                        }
                    }
                });
            } else {
                bucketName = bucketName.toLowerCase();
                $osf.postJSON(
                    nodeApiUrl + 's3/newbucket/',
                    {bucket_name: bucketName}
                ).done(function() {
                    $select.append('<option value="' + bucketName + '">' + bucketName + '</option>');
                    $select.val(bucketName);
                }).fail(function(xhr) {
                    var message = JSON.parse(xhr.responseText).message;
                    if(!message) {
                        message = 'Looks like that name is taken. Try another name?';
                    }
                    bootbox.confirm({
                        title: 'Duplicate bucket name',
                        message: message,
                        callback: function(result) {
                            if(result) {
                                newBucket();
                            }
                        }
                    });
                });
            }
        });
    }

    var removeNodeAuth = function() {
        $.ajax({
            type: 'DELETE',
            url: nodeApiUrl + 's3/settings/',
            contentType: 'application/json',
            dataType: 'json'
        }).done(function() {
            window.location.reload();
        }).fail(
            $osf.handleJSONError
        );
    };

    function importNodeAuth() {
        $osf.postJSON(
            nodeApiUrl + 's3/import-auth/',
            {}
        ).done(function() {
            window.location.reload();
        }).fail(
            $osf.handleJSONError
        );
    }

    $(document).ready(function() {

        $('#newBucket').on('click', function() {
            newBucket();
        });

        $('#s3RemoveToken').on('click', function() {
            bootbox.confirm({
                title: 'Deauthorize S3?',
                message: 'Are you sure you want to remove this S3 authorization?',
                callback: function(confirm) {
                    if(confirm) {
                        removeNodeAuth();
                    }
                }
            });
        });

        $('#s3ImportToken').on('click', function() {
            importNodeAuth();
        });

        $('#addonSettingsS3 .addon-settings-submit').on('click', function() {
            var $bucket = $('#s3_bucket');
            if ($bucket.length && !$bucket.val()) {
                return false;
            }
        });

    });

})();
