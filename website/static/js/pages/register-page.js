'use strict';
var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');

var language = require('js/osfLanguage').registrations;
var registrationUtils = require('js/registrationUtils');
var registrationEmbargo = require('js/registrationEmbargo');

var ctx = window.contextVars;

require('pikaday-css');

$(function() {
    // opt into tooltip
    $('[data-toggle="tooltip"]').tooltip();

    // if registering draft
    if (ctx.draft) {
        var draft = new registrationUtils.Draft(ctx.draft);
        $osf.applyBindings({
            draft: draft
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
