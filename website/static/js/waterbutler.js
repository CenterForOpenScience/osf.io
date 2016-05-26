'use strict';

var $ = require('jquery');
var $osf = require('./osfHelpers');

function getViewOnly() {
    return $osf.urlParams().view_only;
}

function getDefaultOptions(path, provider) {
    var options = {
        path: path,
        provider: provider
    };
    var viewOnly = getViewOnly();
    if (viewOnly) {
        options.view_only = viewOnly;
    }
    if (navigator.appVersion.indexOf('MSIE 9.') !== -1) {
        options.cookie = (document.cookie.match(window.contextVars.cookieName + '=(.+?);|$')[1] || '');
    }
    return options;
}

function buildUrl(suffix, path, provider, nid, options) {
    path = path || '/';
    var baseUrl = window.contextVars.waterbutlerURL + suffix;
    return baseUrl + $.param($.extend(getDefaultOptions(path, provider), {nid: nid}, options));
}

var buildCrudUrl = buildUrl.bind(this, 'file?');
var buildCopyUrl = buildUrl.bind(this, 'copy?');
var buildMoveUrl = buildUrl.bind(this, 'move?');
var buildMetadataUrl = buildUrl.bind(this, 'data?');
var buildRevisionsUrl = buildUrl.bind(this, 'revisions?');
var buildCreateFolderUrl = buildUrl.bind(this, 'folders?');


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

function toJsonBlob(item, options) {
    return $.extend(getDefaultOptions(item.data.path || '/', item.data.provider), {nid: item.data.nodeId}, options);
}

module.exports = {
    toJsonBlob: toJsonBlob,
    buildDeleteUrl: buildCrudUrl,
    buildUploadUrl: buildUploadUrl,
    buildDownloadUrl: function(path, provider, nid, options) {
        if (window.contextVars.accessToken) {
            options = $.extend(options || {}, {token: window.contextVars.accessToken});
        }
        return buildCrudUrl(path, provider, nid, options);
    },
    buildMetadataUrl: buildMetadataUrl,
    buildCreateFolderUrl: buildCrudUrl,
    buildRevisionsUrl: buildRevisionsUrl,
    buildTreeBeardUpload: buildFromTreebeardFile,
    buildTreeBeardCopy: buildFromTreebeard.bind(this, 'copy?'),
    buildTreeBeardMove: buildFromTreebeard.bind(this, 'move?'),
    buildTreeBeardDelete: buildFromTreebeard.bind(this, 'file?'),
    buildTreeBeardDownload: function(item, options) {
        if (window.contextVars.accessToken) {
            options = $.extend(options || {}, {token: window.contextVars.accessToken});
        }
        return buildFromTreebeard('file?', item, options);
    },
    buildTreeBeardMetadata: buildFromTreebeard.bind(this, 'data?'),
    buildTreeBeardDownloadZip: function(item, options) {
        if (window.contextVars.accessToken) {
            options = $.extend(options || {}, {token: window.contextVars.accessToken});
        }
        return buildFromTreebeard('zip?', item, options);
    },
    copyUrl: function(){return window.contextVars.waterbutlerURL + 'ops/copy';},
    moveUrl: function(){return window.contextVars.waterbutlerURL + 'ops/move';}
};
