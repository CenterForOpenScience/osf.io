function trackView(doi) {

    const payload = {
        n: 'view',
        u: window.location.href,
        i: window.contextVars.dataciteTrackerRepoId,
        p: doi,
    };
    const r = new XMLHttpRequest();
    r.open('POST', `https://analytics.datacite.org/api/metric`, true);
    r.setRequestHeader('Content-Type', 'application/json');
    r.send(JSON.stringify(payload));
    r.onreadystatechange = () => {
        if (r.readyState !== 4)
            return;
        if (r.status === 400) {
            console.error('[DataCiteTracker] ' + r.responseText);
        }

    };
}

module.exports = {
    trackView: trackView,
};
