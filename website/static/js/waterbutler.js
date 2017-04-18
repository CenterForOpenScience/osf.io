'use strict';

var $ = require('jquery');
var $osf = require('./osfHelpers');

function buildUrl(path, provider, nid, options) {
    path = path || '/';
    if(path.charAt(0) !== '/'){
        path = '/' + path;
    }
    var baseUrl = window.contextVars.waterbutlerURL + 'v1/resources/' + nid + '/providers/' + provider + path + '?';
    return baseUrl + $.param($.extend(getDefaultOptions(), options));
}

function getDefaultOptions() {
    var options = {};
    var viewOnly = getViewOnly();
    if (viewOnly) {
        options.view_only = viewOnly;
    }
    if (navigator.appVersion.indexOf('MSIE 9.') !== -1) {
        options.cookie = (document.cookie.match(window.contextVars.cookieName + '=(.+?);|$')[1] || '');
    }
    return options;
}

function getViewOnly() {
    return $osf.urlParams().view_only;
}

function buildFromTreebeard(item, options) {
    return buildUrl(item.data.path, item.data.provider, item.data.nodeId, options);
}

function addToken(options) {
    var wb_options = $.extend({}, options || {}, {token: window.contextVars.accessToken});
    return wb_options;
}

function _promoteAttrs(obj_data) {
    var saved_attributes = obj_data.attributes;
    // delete before extending in case saved_attributes has its own
    // attributes property
    delete obj_data.attributes;
    $.extend(true, obj_data, saved_attributes);
    return obj_data;
}

// This function turns a WB structure into a TB structure
// WB returns a structure like:
//      data: { attributes: { name: 'foo', kind: 'file', ... } }
// TB wants a structure like:
//      data: { name: 'foo', kind: 'file', ... }
function wbLazyLoadPreprocess(obj) {
    if (!$.isArray(obj.data)) {
        obj.data = _promoteAttrs(obj.data);
        return obj;
    }
    for (var i = 0; i < obj.data.length; i++) {
        obj.data[i] = _promoteAttrs(obj.data[i]);
    }
    return obj;
}

module.exports = {
    buildDeleteUrl: buildUrl,
    buildDownloadUrl: buildUrl,
    buildUploadUrl: function _buildUploadUrl(path, provider, nid, options) {
        var wb_options = $.extend({}, options || {}, {kind: 'files'});
        return buildUrl(path, provider, nid, wb_options);
    },
    buildMetadataUrl: function _buildMetadataUrl(path, provider, nid, options) {
        var wb_options = $.extend({}, options || {}, {meta: null});
        return buildUrl(path, provider, nid, wb_options);
    },
    buildCreateFolderUrl: buildUrl,
    buildRevisionsUrl: function _buildRevisionsUrl(path, provider, nid, options) {
        var wb_options = $.extend({}, options || {}, {revisions: null});
        return buildUrl(path, provider, nid, wb_options);
    },
    // covers upload (parent item and file name) and update (item, no file name)
    buildTreeBeardUpload: function _buildTreeBeardUpload(item, options) {
        var wb_options = $.extend({}, options || {}, {kind: 'file'});
        return buildFromTreebeard(item, wb_options);
    },
    buildTreeBeardFileOp: buildFromTreebeard,
    buildTreeBeardDelete: buildFromTreebeard,
    buildTreeBeardMetadata: function _buildTreeBeardMetadata(item, options) {
        var wb_options = $.extend({}, options || {}, {meta: null});
        return buildFromTreebeard(item, wb_options);
    },
    buildTreeBeardDownload: function _buildTreeBeardDownload(item, options) {
        var wb_options = addToken(options);
        return buildFromTreebeard(item, wb_options);
    },
    buildTreeBeardDownloadZip: function _buildTreeBeardDownloadZip(item, options) {
        var wb_options = addToken(options);
        $.extend(wb_options, {zip: null});
        return buildFromTreebeard(item, wb_options);
    },
    wbLazyLoadPreprocess: wbLazyLoadPreprocess
};
