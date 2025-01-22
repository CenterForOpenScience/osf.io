const {Tracker} = require('@datacite/datacite-tracker');

var tracker;

function init (repoId) {
    if (repoId){
    tracker = Tracker({repoId});
    } else {
        tracker = Tracker();
    }
}

function trackView(doi) {
    if (tracker) {
        tracker.trackMetric('view', {doi: doi});
    }
}

module.exports = {
    init: init,
    trackView: trackView
};
