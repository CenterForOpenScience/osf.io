    $(document).ready(function() {


        $('#figshareAddKey').on('click', function() {
            if($(this)[0].outerText == 'Authorize: Create Access Token')
                window.location.href = nodeApiUrl + 'figshare/oauth/';
            $.ajax({
                type: 'POST',
                url: nodeApiUrl + 'figshare/user_auth/',
                contentType: 'application/json',
                dataType: 'json',
                success: function(response) {
                    window.location.reload();
                }
            });

        });

        $('#figshareDelKey').on('click', function() {
            bootbox.confirm(
                'Are you sure you want to delete your Figshare access key? This will ' +
                'revoke the ability to modify and upload files to Figshare. If ' +
                'the associated repo is private, this will also disable viewing ' +
                'and downloading files from Figshare.',
                function(result) {
                    if (result) {
                        $.ajax({
                            url: nodeApiUrl + 'figshare/oauth/',
                            type: 'DELETE',
                            contentType: 'application/json',
                            dataType: 'json',
                            success: function() {
                                window.location.reload();
                            }
                        });
                    }
                }
            );
        });

        $('#figshareSelectProject').on('change', function() {
            var value = $(this).val();
            if (value) {
                $('#figshareId').val(value)
                $('#figshareTitle').val($('#figshareSelectProject option:selected').text())
            }
        });

        $('#addonSettingsFigshare .addon-settings-submit').on('click', function() {
            if ($('#figshareId').val() == '-----') {
                return false;
            }
        });

        $('#figshareCreateProject').on('click',function() {
            createProject();
        });

    });

    // var createProject = function() {

    //     var $elm = $('#addonSettingsFigshare');
    //     var $select = $elm.find('select');

    //     bootbox.prompt('Name your new project', function(projectName) {
    //         $.ajax({
    //             type: 'POST',
    //             url: nodeApiUrl + 'figshare/new/project/',
    //             contentType: 'application/json',
    //             dataType: 'json',
    //             data: JSON.stringify({project: projectName}),
    //             success: function(response) {
    //                 response.project_id = 'project_' + response.project_id;
    //                 $select.append('<option value="' + response.project_id + '">' + projectName + '</option>');
    //                 $select.val(response.project_id);
    //                 $('#figshareId').val(response.project_id)
    //                 $('#figshareTitle').val(projectName)
    //             },
    //             error: function() {
    //                 $('#addonSettingsFigshare').find('.addon-settings-message')
    //                     .text('Could not create project')
    //                     .removeClass('text-success').addClass('text-danger')
    //                     .fadeOut(100).fadeIn();
    //             }
    //         });
    //     });
    //};
