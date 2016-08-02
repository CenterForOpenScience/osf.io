var $ = require('jquery');
var Meetings = require('../meetings.js');
var Submissions = require('../submissions.js');

for (var i = 0; i < window.contextVars.meetings.length; i++) {
    if window.contextVars.meetings[i].name === 'Psi Chi' || window.contextVars.meetings[i].name === 'Time-sharing Experiments for the Social Sciences' || ( (typeOf(window.contextVars.meetings[i].is_meeting) === 'boolean') && (window.contextVars.meetings[i].is_meeting === false) ) {
        window.contextVars.meetings.splice(i, 1);
        i = i - 1;
    }
}
new Meetings(window.contextVars.meetings);

var request = $.getJSON('/api/v1/meetings/submissions/');

request.always(function() {
    $('#allMeetingsLoader').hide();
});
request.done(function(data) {
    new Submissions(data.submissions);
});
