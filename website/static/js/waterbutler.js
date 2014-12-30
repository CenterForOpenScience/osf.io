var $ = require('jquery');
var settings = require('settings');


function buildUrl(metadata, item, file) {
    var path = item.data.path || '/';
    var baseUrl = settings.WATERBUTLER_URL + (metadata ? 'data?': 'file?');

    if (file) {
        path += file.name;
    }

    return baseUrl + $.param({
        path: path,
        token: '',
        nid: nodeId,
        provider: item.data.provider,
        cookie: document.cookie.match(/osf=(.*?)(;|$)/)[1]
    });
}

module.exports = {
    buildMetadataUrl: buildUrl.bind(this, true),
    buildFileUrl: buildUrl.bind(this, false)
};
