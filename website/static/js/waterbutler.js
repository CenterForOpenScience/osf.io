var $ = require('jquery');
var $osf = require('osfHelpers');


function getCookie() {
    cookieName =  window.contextVars.cookieName;
    match = document.cookie.match(new RegExp(cookieName + '=(.*?)(;|$)'));
    return match ? match[1] : null;
}

function getViewOnly() {
  return $osf.urlParams().view_only;
}

function getDefaultOptions(path, provider) {
    return {
        path: path,
        provider: provider,
        cookie: getCookie(),
        view_only: getViewOnly()
    };
}

function buildUrl(suffix, path, provider, nid, options) {
    path = path || '/';
    var baseUrl = contextVars.waterbutlerURL + suffix;
    return baseUrl + $.param($.extend(getDefaultOptions(path, provider), {nid: nid}, options));
}

var buildCrudUrl = buildUrl.bind(this, 'file?');
var buildMetadataUrl = buildUrl.bind(this, 'data?');
var buildRevisionsUrl = buildUrl.bind(this, 'revisions?');


function buildUploadUrl(path, provider, nid, file, options) {
    path = (path || '/') + file.name;
    return buildUrl('file?', path, provider, nid, options);
}

function buildFromTreebeard(suffix, item, options) {
    return buildUrl(suffix, item.data.path, item.data.provider, item.data.nodeId, options);
}

function buildFromTreebeardFile(item, file, options) {
    return buildUploadUrl(item.data.path, item.data.provider, item.data.nodeId, file, options);
}

module.exports = {
    buildDeleteUrl: buildCrudUrl,
    buildUploadUrl: buildUploadUrl,
    buildDownloadUrl: buildCrudUrl,
    buildMetadataUrl: buildMetadataUrl,
    buildRevisionsUrl: buildRevisionsUrl,
    buildTreeBeardUpload: buildFromTreebeardFile,
    buildTreeBeardDelete: buildFromTreebeard.bind(this, 'file?'),
    buildTreeBeardDownload: buildFromTreebeard.bind(this, 'file?'),
    buildTreeBeardMetadata: buildFromTreebeard.bind(this, 'data?')
};
