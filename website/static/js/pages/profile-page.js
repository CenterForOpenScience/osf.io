/**
 * Initialization code for the profile page. Currently, this just loads the necessary
 * modules and puts the profile module on the global context.
 *
*/

var profile = require('../profile.js'); // Social, Job, Education classes
require('../project.js'); // Needed for nodelists to work
require('../logFeed.js'); // Needed for nodelists to work

var ctx = window.contextVars;
// Instantiate all the profile modules
new profile.Social('#social', ctx.socialUrls, ['edit', 'view']);
new profile.Jobs('#jobs', ctx.jobsUrls, ['edit', 'view']);
new profile.Schools('#schools', ctx.schoolsUrls, ['edit', 'view']);
