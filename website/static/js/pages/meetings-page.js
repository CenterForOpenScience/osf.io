var $ = require('jquery');
var Meetings = require('../meetings.js');
var Submissions = require('../submissions.js');

new Meetings(window.contextVars.meetings);

var request = $.getJSON('/api/v1/meetings/submissions/');

request.always(function() {
    $('#allMeetingsLoader').hide();
});
request.done(function(data) {
    new Submissions(data.submissions);
});
