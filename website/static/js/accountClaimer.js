/**
* Module that enables account claiming on the project page. Makes unclaimed
* usernames show popovers when clicked, where they can input their email.
*
* Sends HTTP requests to the claim_user_post endpoint.
*/
'use strict';

var $ = require('jquery');
var $osf = require('osf-helpers');
var bootbox = require('bootbox');

var currentUserId = window.contextVars.currentUser.id;

function AccountClaimer (selector) {
    this.selector = selector;
    this.element = $(selector);  // Should select all span elements for
                                // unreg contributor names
    this.init();
}

function getClaimUrl() {
    var uid = $(this).data('pk');
    var pid = global.nodeId;
    return '/api/v1/user/' + uid + '/' + pid +  '/claim/email/';
}

function alertFinished(email) {
    $osf.growl('Email will arrive shortly', ['Please check <em>', email, '</em>'].join(''), 'success');
}

function onClickIfLoggedIn() {
    var pk = $(this).data('pk');
    if (pk !== currentUserId) {
        bootbox.confirm({
            title: 'Claim as ' + global.contextVars.currentUser.username + '?',
            message: 'If you claim this account, a contributor of this project ' +
                    'will be emailed to confirm your identity.',
            callback: function(confirmed) {
                if (confirmed) {
                    $osf.postJSON(
                        getClaimUrl(),
                        {
                            claimerId: currentUserId,
                            pk: pk
                        }
                    ).done(function(response) {
                        alertFinished(response.email);
                    }).fail(
                        $osf.handleJSONError
                    );
                }
            }
        });
    }
}

AccountClaimer.prototype = {
    constructor: AccountClaimer,
    init: function() {
        var self = this;
        self.element.tooltip({
            title: 'Is this you? Click to claim'
        });
        if (currentUserId.length) { // If user is logged in, ask for confirmation
            self.element.on('click', onClickIfLoggedIn);
        } else {
            self.element.editable({
                type: 'text',
                value: '',
                ajaxOptions: {
                    type: 'post',
                    contentType: 'application/json',
                    dataType: 'json'  // Expect JSON response
                },
                success: function(data) {
                    alertFinished(data.email);
                },
                error: $osf.handleEditableError,
                display: function(value, sourceData){
                    if (sourceData && sourceData.fullname) {
                        $(this).text(sourceData.fullname);
                    }
                },
                // Send JSON payload
                params: function(params) {
                    return JSON.stringify(params);
                },
                title: 'Claim Account',
                placement: 'bottom',
                placeholder: 'Enter email...',
                validate: function(value) {
                    var trimmed = $.trim(value);
                    if (!$osf.isEmail(trimmed)) {
                        return 'Not a valid email.';
                    }
                },
                url: getClaimUrl.call(this),
            });
        }
    }
};

module.exports = AccountClaimer;
