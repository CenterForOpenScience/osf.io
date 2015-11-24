'use strict';
var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');

var language = require('js/osfLanguage').registrations;
var registrationUtils = require('js/registrationUtils');
var registrationEmbargo = require('js/registrationEmbargo');

var ctx = window.contextVars;
var node = ctx.node;
var nodeApiUrl = node.urls.api;

require('pikaday-css');

$(function() {
    // opt into tooltip
    $('[data-toggle="tooltip"]').tooltip();

    // if registering draft
    if (ctx.draft) {
        var draft = new registrationUtils.Draft(ctx.draft);
        var editor = new registrationUtils.RegistrationEditor({
            schemas: '/api/v1/project/schemas/',
            create: node.urls.api + 'drafts/',
            submit: node.urls.api + 'drafts/{draft_pk}/submit/',
            update: node.urls.api + 'drafts/{draft_pk}/',
            get: node.urls.api + 'drafts/{draft_pk}/',
            draftRegistrations: node.urls.web + 'registrations/#drafts'
        });
        editor.init(draft, true);
        $osf.applyBindings({
            draft: draft,
            editor: editor
        }, '#draftRegistrationScope');
    }
    // if viewing registered metadata
    else {
        var metaSchema = new registrationUtils.MetaSchema(ctx.node.registrationMetaSchema);

        var metaDataViewModel = {
            metaSchema: metaSchema,
            schemaData: ctx.node.registrationMetaData[metaSchema.id] || {}
        };
        $osf.applyBindings(metaDataViewModel, '#registrationMetaDataScope');
    }

});
