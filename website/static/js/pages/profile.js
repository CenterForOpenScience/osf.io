/**
 * Initialization code for the profile page. Currently, this just loads the necessary
 * modules and puts the profile module on the global context. 
 *
 * The profile classes, e.g. Social, Jobs, etc., currently depend on the mako context, so
 * they are instantiated in profile.mako at the moment. Eventually we'll want to refactor
 * that code so that the initialization can happen in this file.
 * */
var profile = require('../profile.js'); // Social, Job, Education classes
require('../project.js'); // Needed for nodelists to work
require('../logFeed.js'); // Needed for nodelists to work

// Export profile classes to the global context so they can be instantiated in the
// profile.mako file
window.profile = profile;
