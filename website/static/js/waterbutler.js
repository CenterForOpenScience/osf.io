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

function getDefaultOptions(path, provider) {
    var nid = window.nodeId || contextVars.node.id;

    return {
        nid: nid,
        token: '',
        path: path,
        provider: provider,
        cookie: getCookie(),
        viewOnly: getViewOnly()
    };
}

function buildUrl(suffix, path, provider, options) {
    path = path || '/';
    var baseUrl = settings.WATERBUTLER_URL + suffix;

    return baseUrl + $.param($.extend(getDefaultOptions(path, provider), options));
}

var buildCrudUrl = buildUrl.bind(this, 'file?');
var buildMetadataUrl = buildUrl.bind(this, 'data?');


function buildUploadUrl(path, provider, file, options) {
    path = (path || '/') + file.name;
    return buildUrl('file?', path, provider, options);
}

function buildFromTreebeard(suffix, item, options) {
    return buildUrl(suffix, item.data.path, item.data.provider, options);
}

function buildFromTreebeardFile(item, file, options) {
    return buildUploadUrl(item.data.path, item.data.provider, file, options);
}

module.exports = {
    buildDeleteUrl: buildCrudUrl,
    buildUploadUrl: buildUploadUrl,
    buildDownloadUrl: buildCrudUrl,
    buildMetadataUrl: buildMetadataUrl,
    buildTreeBeardUpload: buildFromTreebeardFile,
    buildTreeBeardDelete: buildFromTreebeard.bind(this, 'file?'),
    buildTreeBeardDownload: buildFromTreebeard.bind(this, 'file?'),
    buildTreeBeardMetadata: buildFromTreebeard.bind(this, 'data?'),
};
