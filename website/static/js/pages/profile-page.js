/**
 * Initialization code for the profile page. Currently, this just loads the necessary
 * modules and puts the profile module on the global context.
 *
*/

var profile = require('../profile.js'); // Social, Job, Education classes
require('../project.js'); // Needed for nodelists to work
require('../components/logFeed.js'); // Needed for nodelists to work

var ctx = window.contextVars;
// Instantiate all the profile modules
new profile.Social('#social', ctx.socialUrls, ['view']);
new profile.Jobs('#jobs', ctx.jobsUrls, ['view']);
new profile.Schools('#schools', ctx.schoolsUrls, ['view']);

window.activeAjaxCount = 0;

function isAllXhrComplete(){
    window.activeAjaxCount--;
    if (window.activeAjaxCount === 0){
        $('meta[name=prerender-status-code]').attr('content', '200');
        window.prerenderReady = true;
    }

}

(function(open) {
    XMLHttpRequest.prototype.open = function(method, url, async, user, pass) {
        this.addEventListener('load', isAllXhrComplete);
        open.call(this, method, url, async, user, pass);
    };
})(XMLHttpRequest.prototype.open);


(function(send) {
    XMLHttpRequest.prototype.send = function (data) {
        window.activeAjaxCount++;
        send.call(this, data);
    };
})(XMLHttpRequest.prototype.send);