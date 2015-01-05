var $ = require('jquery');
var $osf = require('osfHelpers');
var settings = require('settings');


function getCookie() {
    match = document.cookie.match(/osf=(.*?)(;|$)/);
    return match ? match[1] : null;
}

function getViewOnly() {
  return $osf.urlParams().view_only;
}

function buildUrl(metadata, path, provider, file) {
    path = path || '/';
    var baseUrl = settings.WATERBUTLER_URL + (metadata ? 'data?': 'file?');

    if (file) {
        path += file.name;
    }

    return baseUrl + $.param({
        path: path,
        token: '',
        nid: nodeId,
        provider: provider,
        cookie: getCookie(),
        viewOnly: getViewOnly()
    });
}

function buildFromTreebeard(metadata, item, file) {
    return buildUrl(metadata, item.data.path, item.data.provider, file);
}

module.exports = {
    buildFileUrlFromPath: buildUrl.bind(this, false),
    buildFileUrl: buildFromTreebeard.bind(this, false),
    buildMetadataUrlFromPath: buildUrl.bind(this, true),
    buildMetadataUrl: buildFromTreebeard.bind(this, true),
};
