'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var ko = require('knockout');

var ProjectSettings = require('js/projectSettings.js');
var NodesDelete = require('js/nodesDelete.js');
var InstitutionProjectSettings = require('js/institutionProjectSettings.js');

var $osf = require('js/osfHelpers');
require('css/addonsettings.css');

var ctx = window.contextVars;


// Initialize treebeard grid for notifications
var ProjectNotifications = require('js/notificationsTreebeard.js');
var $notificationsMsg = $('#configureNotificationsMessage');
var notificationsURL = ctx.node.urls.api  + 'subscriptions/';
// Need check because notifications settings don't exist on registration's settings page
if ($('#grid').length) {
    $.ajax({
        url: notificationsURL,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        new ProjectNotifications(response);
    }).fail(function(xhr, status, error) {
        $notificationsMsg.addClass('text-danger');
        $notificationsMsg.text('Could not retrieve notification settings.');
        Raven.captureMessage('Could not GET notification settings.', {
            extra: { url: notificationsURL, status: status, error: error }
        });
    });
}

//Initialize treebeard grid for wiki
var ProjectWiki = require('js/wikiSettingsTreebeard.js');
var wikiSettingsURL = ctx.node.urls.api  + 'wiki/settings/';
var $wikiMsg = $('#configureWikiMessage');

if ($('#wgrid').length) {
    $.ajax({
        url: wikiSettingsURL,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        new ProjectWiki(response);
    }).fail(function(xhr, status, error) {
        $wikiMsg.addClass('text-danger');
        $wikiMsg.text('Could not retrieve wiki settings.');
        Raven.captureMessage('Could not GET wiki settings.', {
            extra: { url: wikiSettingsURL, status: status, error: error }
        });
    });
}

$(document).ready(function() {
    // Apply KO bindings for Project Settings
    if ($('#institutionSettings').length) {
        new InstitutionProjectSettings.InstitutionProjectSettings('#institutionSettings', window.contextVars);
    }
    var categoryOptions = [];
    var keys = Object.keys(window.contextVars.nodeCategories);
    for (var i = 0; i < keys.length; i++) {
        categoryOptions.push({
            label: window.contextVars.nodeCategories[keys[i]],
            value: keys[i]
        });
    }
    // need check because node category doesn't exist for registrations
    if ($('#projectSettings').length) {
        var projectSettingsVM = new ProjectSettings.ProjectSettings( {
            currentTitle: ctx.node.title,
            currentDescription: ctx.node.description,
            category: ctx.node.category,
            categoryOptions: categoryOptions,
            node_id: ctx.node.id,
            updateUrl:  $osf.apiV2Url('nodes/' + ctx.node.id + '/'),
        });
        ko.applyBindings(projectSettingsVM, $('#projectSettings')[0]);
    }

    if(ctx.node.childExists){
        new NodesDelete.NodesDelete('#nodesDelete', ctx.node);
    }else{
        $('#deleteNode').on('click', function() {
            ProjectSettings.getConfirmationCode(ctx.node.nodeType, ctx.node.isPreprint);
        });
    }

    // TODO: Knockout-ify me
    $('#commentSettings').on('submit', function() {
        var $commentMsg = $('#configureCommentingMessage');

        var $this = $(this);
        var commentLevel = $this.find('input[name="commentLevel"]:checked').val();

        $osf.postJSON(
            ctx.node.urls.api + 'settings/comments/',
            {commentLevel: commentLevel}
        ).done(function() {
            $commentMsg.text('Successfully updated settings.');
            $commentMsg.addClass('text-success');
            if($osf.isSafari()){
                //Safari can't update jquery style change before reloading. So delay is applied here
                setTimeout(function(){window.location.reload();}, 100);
            } else {
                window.location.reload();
            }

        }).fail(function() {
            bootbox.alert({
                message: 'Could not set commenting configuration. Please try again.',
                buttons:{
                    ok:{
                        label:'Close',
                        className:'btn-default'
                    }
                }
            });
        });

        return false;

    });
});


var subscribeViewModel = function(viewModel, options) {
    /**
     * @param {Object} options: Options including `messageObservable`, `name` (the name of the setting),
     *                          `updateUrl` (endpoint used to make the update request), and `objectToUpdate`
     **/
    viewModel.enabled.subscribe(function(newValue) {
        var self = this;
        var payload = {};
        payload[options.objectToUpdate] = newValue;
        $osf.postJSON(ctx.node.urls.api + options.updateUrl, payload
        ).done(function(response) {
            if (newValue) {
                viewModel[options.messageObservable](options.name + ' Enabled');
            }
            else {
                viewModel[options.messageObservable](options.name + ' Disabled');
            }
            //Give user time to see message before reload.
            setTimeout(function(){window.location.reload();}, 1500);
        }).fail(function(xhr, status, error) {
            $osf.growl('Error', 'Unable to update wiki');
            Raven.captureMessage('Could not update wiki.', {
                extra: {
                    url: ctx.node.urls.api + options.updateUrl, status: status, error: error
                }
            });
            setTimeout(function(){window.location.reload();}, 1500);
        });
        return true;
    }, viewModel);
};


var WikiSettingsViewModel = {
    enabled: ko.observable(ctx.wiki.isEnabled), // <- this would get set in the mako template, as usual
    wikiMessage: ko.observable('')
};

subscribeViewModel(WikiSettingsViewModel, {
    messageObservable: 'wikiMessage',
    name: 'Wiki',
    updateUrl: 'settings/addons/',
    objectToUpdate:'wiki'
});

if ($('#selectWikiForm').length) {
    $osf.applyBindings(WikiSettingsViewModel, '#selectWikiForm');
}

var RequestAccessSettingsViewModel = {
    enabled: ko.observable(ctx.node.requestProjectAccessEnabled), // <- this would get set in the mako template, as usual
    requestAccessMessage: ko.observable('')
};

subscribeViewModel(RequestAccessSettingsViewModel, {
    messageObservable: 'requestAccessMessage',
    name: 'Request Access',
    updateUrl: 'settings/requests/',
    objectToUpdate: 'accessRequestsEnabled'
});

if ($('#enableRequestAccessForm').length) {
    $osf.applyBindings(RequestAccessSettingsViewModel, '#enableRequestAccessForm');
}
