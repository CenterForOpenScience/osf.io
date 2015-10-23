webpackJsonp([20],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

'use strict';

var $ = __webpack_require__(38);
__webpack_require__(358);
var AddonHelper = __webpack_require__(359);

$(window.contextVars.githubSettingsSelector).on('submit', AddonHelper.onSubmitSettings);


/***/ },

/***/ 358:
/***/ function(module, exports, __webpack_require__) {

'use strict';

var $ = __webpack_require__(38);
var bootbox = __webpack_require__(138);
var $osf = __webpack_require__(47);

var nodeApiUrl = window.contextVars.node.urls.api;

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

        bootbox.prompt({
            title: 'Name your new repo',
            placeholder: 'Repo name',
            callback: function (repoName) {
                // Return if cancelled
                if (repoName === null) {
                    return;
                }

                if (repoName === '') {
                    displayError('Your repo must have a name');
                    return;
                }

                $osf.postJSON(
                    '/api/v1/github/repo/create/',
                    {name: repoName}
                ).done(function (response) {
                        var repoName = response.user + ' / ' + response.repo;
                        $select.append('<option value="' + repoName + '">' + repoName + '</option>');
                        $select.val(repoName);
                        updateHidden(repoName);
                    }).fail(function () {
                        displayError('Could not create repository');
                    });
            },
            buttons:{
                confirm:{
                    label: 'Save',
                    className:'btn-success'
                }
            }
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
                    if($osf.isIE()){
                        window.location.hash = "#configureAddonsAnchor";
                    }
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
                title: 'Disconnect GitHub Account?',
                message: 'Are you sure you want to remove this GitHub account?',
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
                },
                buttons:{
                    confirm:{
                        label: 'Disconnect',
                        className: 'btn-danger'
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


/***/ },

/***/ 359:
/***/ function(module, exports, __webpack_require__) {

// TODO: Deprecate me
var $ = __webpack_require__(38);
var $osf = __webpack_require__(47);

var AddonHelper = (function() {

    /**
     * Convert an HTML form to a JS object.
     *
     * @param {jQuery} form
     * @return {Object} The parsed data
     */
    function formToObj(form) {
        var rv = {};
        $.each($(form).serializeArray(), function(_, value) {
            rv[value.name] = value.value;
        });
        return rv;
    }

    /**
     * Submit add-on settings.
     */
    function onSubmitSettings() {
        var $this = $(this);
        var addon = $this.attr('data-addon');
        var owner = $this.find('span[data-owner]').attr('data-owner');
        var msgElm = $this.find('.addon-settings-message');

        var url = owner === 'user' ? '/api/v1/settings/' + addon + '/' : nodeApiUrl + addon + '/settings/';

        $osf.postJSON(
            url,
            formToObj($this)
        ).done(function() {
            msgElm.text('Settings updated')
                .removeClass('text-danger').addClass('text-success')
                .fadeOut(100).fadeIn();
        }).fail(function(response) {
            var message = '';
            response = JSON.parse(response.responseText);
            if (response && response.message) {
                message = response.message;
            } else {
                message = 'Settings not updated.';
            }
            msgElm.text(message)
                .removeClass('text-success').addClass('text-danger')
                .fadeOut(100).fadeIn();
        });

        return false;

    }

    // Expose public methods
    exports = {
        formToObj: formToObj,
        onSubmitSettings: onSubmitSettings,
    };

    if (true) {
        module.exports = exports; 
    } 
    return exports;
})();


/***/ }

});
//# sourceMappingURL=node-cfg.js.map