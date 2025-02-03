let dataciteConfig = {};
function init(repoId){
    dataciteConfig.repoId=repoId;
}

function getRepoId() {
    if (dataciteConfig.repoId) {
        return dataciteConfig.repoId;
    } else {
        return window.contextVars.dataciteTracker.repoId;
    }
}

function trackView(metricName, doi) {
    if (!doi || doi.trim().length === 0) {
        return;
    }
    const repoID = getRepoId();

    const payload = {
        n: metricName,
        u: window.location.href,
        i: repoID,
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
    init: init
};
