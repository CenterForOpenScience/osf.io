var GithubConfigHelper = (function() {

    var updateHidden = function(val) {
        var repoParts = val.split('/');
        $('#githubUser').val($.trim(repoParts[0]));
        $('#githubRepo').val($.trim(repoParts[1]));
    };

    var displayError = function(msg) {
        $('#addonSettingsGithub').find('.addon-settings-message')
            .text('Error: ' + msg)
            .removeClass('text-success').addClass('text-danger')
            .fadeOut(100).fadeIn();
    };

    var createRepo = function() {

        var $elm = $('#addonSettingsGithub');
        var $select = $elm.find('select');

        bootbox.prompt('Name your new repo', function(repoName) {

            // Return if cancelled
            if (repoName === null)
                return;

            if (repoName === '') {
                displayError('Your repo must have a name');
                return;
            }

            $.ajax({
                type: 'POST',
                url: '/api/v1/github/repo/create/',
                contentType: 'application/json',
                dataType: 'json',
                data: JSON.stringify({name: repoName}),
                success: function(response) {
                    var repoName = response.user + ' / ' + response.repo;
                    $select.append('<option value="' + repoName + '">' + repoName + '</option>');
                    $select.val(repoName);
                    updateHidden(repoName);
                },
                error: function() {
                    displayError('Could not create repository');
                }
            });
        });
    };

    $(document).ready(function() {

        $('#githubSelectRepo').on('change', function() {
            var value = $(this).val();
            if (value) {
                updateHidden(value);
            }
        });

        $('#githubCreateRepo').on('click', function() {
            createRepo();
        });

        $('#githubImportToken').on('click', function() {
            $.ajax({
                type: 'POST',
                url: nodeApiUrl + 'github/user_auth/',
                contentType: 'application/json',
                dataType: 'json',
                success: function(response) {
                    window.location.reload();
                }
            });
        });

        $('#githubCreateToken').on('click', function() {
            window.location.href = nodeApiUrl + 'github/oauth/';
        });

        $('#githubRemoveToken').on('click', function() {
            bootbox.confirm('Are you sure you want to remove this GitHub authorization?', function(confirm) {
                if (confirm) {
                    $.ajax({
                        type: 'DELETE',
                        url: nodeApiUrl + 'github/oauth/',
                        success: function(response) {
                            window.location.reload();
                        }
                    });
                }
            });
        });

        $('#addonSettingsGithub .addon-settings-submit').on('click', function() {
            if (!$('#githubRepo').val()) {
                return false;
            }
        });

    });

})();
