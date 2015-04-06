var profile = require('../profile.js');

var ctx = window.contextVars;

new profile.Names('#names', ctx.nameUrls, ['edit']);
new profile.Social('#social', ctx.socialUrls, ['edit']);
new profile.Jobs('#jobs', ctx.jobsUrls, ['edit']);
new profile.Schools('#schools', ctx.schoolsUrls, ['edit']);
