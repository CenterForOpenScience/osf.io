(function() {

    function newBucket() {
        var isValidBucket = /^(?!.*(\.\.|-\.))[^.][a-z0-9\d.-]{2,61}[^.]$/;
        var $elm = $('#addonSettingsS3');
        var $select = $elm.find('select');

        bootbox.prompt('Name your new bucket', function(bucketName) {

            if (!bucketName) {
                return;
            } else if (isValidBucket.exec(bucketName) == null) {
                bootbox.confirm("Sorry, that's not a valid bucket name. Try another name?", function(result) {
                    if (result) {
                        newBucket();
                    }
                });
            } else {
                bucketName = bucketName.toLowerCase();
                $.ajax({
                    type: 'POST',
                    url: nodeApiUrl + 's3/newbucket/',
                    contentType: 'application/json',
                    dataType: 'json',
                    data: JSON.stringify({
                        bucket_name: bucketName
                    })
                }).done(function() {
                    $select.append('<option value="' + bucketName + '">' + bucketName + '</option>');
                    $select.val(bucketName);
                }).fail(function(xhr) {
                    var message = JSON.parse(xhr.responseText).message;
                    if(!message)
                        message = 'Looks like that name is taken. Try another name?';
                    bootbox.confirm(message, function(result) {
                        if (result) {
                            newBucket();
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
            dataType: 'json',
            success: function(response) {
                window.location.reload();
            },
            error: function(xhr) {
                //TODO Do something here
            }
        });
    };

    function importNodeAuth() {
        $.ajax({
            type: 'POST',
            url: nodeApiUrl + 's3/import-auth/',
            contentType: 'application/json',
            dataType: 'json',
            success: function(response) {
                window.location.reload();
            },
            error: function(xhr) {
                //TODO Do something here
            }
        });
    }

    $(document).ready(function() {

        $('#newBucket').on('click', function() {
            newBucket();
        });

        $('#s3RemoveToken').on('click', function() {
            bootbox.confirm(
                'Are you sure you want to remove this S3 authorization?', function(confirm) {
                    if (confirm) {
                        removeNodeAuth();
                    }
                }
            );
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
