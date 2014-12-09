var $osf = require('osf-helpers');
var $ = require('jquery');
var bootbox = require('bootbox');

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

            $osf.postJSON(
                '/api/v1/github/repo/create/',
                {name: repoName}
            ).done(function(response) {
                var repoName = response.user + ' / ' + response.repo;
                $select.append('<option value="' + repoName + '">' + repoName + '</option>');
                $select.val(repoName);
                updateHidden(repoName);
            }).fail(function() {
                displayError('Could not create repository');
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
            $osf.postJSON(
                nodeApiUrl + 'github/user_auth/',
                {}
            ).done(function() {
                window.location.reload();
            }).fail(
                $osf.handleJSONError
            );
        });

        $('#githubCreateToken').on('click', function() {
            window.location.href = nodeApiUrl + 'github/oauth/';
        });

        $('#githubRemoveToken').on('click', function() {
            bootbox.confirm({
                title: 'Deauthorize GitHub?',
                message: 'Are you sure you want to remove this GitHub authorization?',
                callback: function(confirm) {
                    if(confirm) {
                        $.ajax({
                        type: 'DELETE',
                        url: nodeApiUrl + 'github/oauth/'
                    }).done(function() {
                        window.location.reload();
                    }).fail(
                        $osf.handleJSONError
                    );
                    }
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

module.exports = GithubConfigHelper;