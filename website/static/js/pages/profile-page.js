/**
 * Initialization code for the profile page. Currently, this just loads the necessary
 * modules and puts the profile module on the global context.
 *
*/
var $ = require('jquery');
var m = require('mithril');

require('../project.js'); // Needed for nodelists to work
require('../components/logFeed.js'); // Needed for nodelists to work
var profile = require('../profile.js'); // Social, Job, Education classes
var publicNodes = require('../components/publicNodes.js');
var quickFiles = require('../components/quickFiles.js');

var ctx = window.contextVars;
// Instantiate all the profile modules
new profile.Social('#social', ctx.socialUrls, ['view'], false);
new profile.Jobs('#jobs', ctx.jobsUrls, ['view'], false);
new profile.Schools('#schools', ctx.schoolsUrls, ['view'], false);

$(document).ready(function () {
    m.mount(document.getElementById('publicProjects'), m.component(publicNodes.PublicNodes, {user: ctx.user, nodeType: 'projects'}));
    m.mount(document.getElementById('publicComponents'), m.component(publicNodes.PublicNodes, {user: ctx.user, nodeType: 'components'}));
    if(ctx.user.has_quickfiles) {
        m.mount(document.getElementById('quickFiles'), m.component(quickFiles.QuickFiles, {user: ctx.user}));
    }
});

