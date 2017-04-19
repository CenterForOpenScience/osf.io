var $ = require('jquery');
var Meetings = require('../meetings.js');
var Submissions = require('../submissions.js');

var tracker = 0; 
for (var i = 0; i < window.contextVars.meetings.length; i++) {
    if (window.contextVars.meetings[i].name === 'Psi Chi' || window.contextVars.meetings[i].name === 'Time-sharing Experiments for the Social Sciences') {
        window.contextVars.meetings.splice(i, 1);
        i = i - 1;
        tracker = tracker + 1;
        if (tracker === 2) { // Once we have removed both of the non meetings meetings, the for loop can break
            break;
         }
    }
}
new Meetings(window.contextVars.meetings);

var request = $.getJSON('/api/v1/meetings/submissions/');

request.always(function() {
    $('#allMeetingsLoader').hide();
});

request.done(function(data) {
     console.log(data.submissions);
    for (var i = 0; i < data.submissions.length; i++) {
        if (data.submissions[i].confName === 'Psi Chi' || data.submissions[i].confName === 'Time-sharing Experiments for the Social Sciences') {
            data.submissions.splice(i, 1);
            i = i - 1;
        }
    }
    new Submissions(data.submissions);
 });