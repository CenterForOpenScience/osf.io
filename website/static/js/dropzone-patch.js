/**
* Monkey-patch necessary for getting S3 uploads to works. Ensures that the XHR
* is opened only after options.method and options.url have been resolved.
*/
/*jshint ignore:start */

var Dropzone = require('dropzone');
var $osf = require('osf-helpers');
var $ = require('jquery');

__hasProp = {}.hasOwnProperty,
__extends = function(child, parent) {
    for (var key in parent) {
        if (__hasProp.call(parent, key)) child[key] = parent[key];
    }

    function ctor() {
        this.constructor = child;
    }
    ctor.prototype = parent.prototype;
    child.prototype = new ctor();
    child.__super__ = parent.prototype;
    return child;
},
__slice = [].slice;

extend = function() {
    var key, object, objects, target, val, _i, _len;
    target = arguments[0], objects = 2 <= arguments.length ? __slice.call(arguments, 1) : [];
    for (_i = 0, _len = objects.length; _i < _len; _i++) {
        object = objects[_i];
        for (key in object) {
            val = object[key];
            target[key] = val;
        }
    }
    return target;
};

/**
    * Dropzone has no business adding files from directories.
    *
    * NOTE: This is a hack to keep directories from uploading
    */
Dropzone.prototype._addFilesFromDirectory = function(directory, path) {
    directory.status = Dropzone.ERROR;
    return this.emit("error", directory, "Cannot upload directories, applications, or packages.");
};

/**
 * Get the url to use for the upload request.
 *
 * NOTE: This is a hack to get uploads via signed URLs to work.
 */
Dropzone.prototype.getUrl = function(file) {
    var self = this;
    if (file.signedUrlFrom) {
        var url = typeof file.signedUrlFrom === 'function' ?
            file.signedUrlFrom() :
            file.signedUrlFrom;
        return $.ajax({
            type: 'POST',
            url: url,
            data: JSON.stringify({
                name: file.destination || file.name,
                type: file.type,
                size: file.size,
            }),
            contentType: 'application/json',
            dataType: 'json'
        }).done(function(url) {
            return self.options.url = url;
        }).fail(function(xhr, textStatus, error) {
            var msg;
            try {
                msg = xhr.responseJSON.message_long;
            } catch(error) {
                msg = textStatus;
            }
            $osf.growl('Error:', msg);
        });
    } else {
        return file.url || this.options.url;
    }
};

Dropzone.prototype.uploadFiles = function(files) {
    var file, formData, handleError, headerName, headerValue, headers, input, inputName, inputType, key, option, progressObj, response, updateProgress, value, xhr, _i, _j, _k, _l, _len, _len1, _len2, _len3, _len4, _m, _ref, _ref1, _ref2, _ref3, _ref4,
        _this = this, wasSigned = files[0].signedUrlFrom;
    xhr = new XMLHttpRequest();
    for (_i = 0, _len = files.length; _i < _len; _i++) {
        file = files[_i];
        file.xhr = xhr;
    }

    // Defer sending the xhr until the URL has been resolved.
    // NOTE: This will only work with multipleUploads turned off
    $.when(_this.getUrl(files[0])).done(function(uploadUrl) {
            xhr.open(
                files[0].method || _this.options.method,
                uploadUrl,
                true
            );
            xhr.withCredentials = !! _this.options.withCredentials;
            response = null;
            handleError = function() {
                var _j, _len1, _results;
                _results = [];
                for (_j = 0, _len1 = files.length; _j < _len1; _j++) {
                    file = files[_j];
                    _results.push(_this._errorProcessing(files, response || _this.options.dictResponseError.replace("{{statusCode}}", xhr.status), xhr));
                }
                return _results;
            };
            updateProgress = function(e) {
                var allFilesFinished, progress, _j, _k, _l, _len1, _len2, _len3, _results;
                if (e != null) {
                    progress = 100 * e.loaded / e.total;
                    for (_j = 0, _len1 = files.length; _j < _len1; _j++) {
                        file = files[_j];
                        file.upload = {
                            progress: progress,
                            total: e.total,
                            bytesSent: e.loaded
                        };
                    }
                } else {
                    allFilesFinished = true;
                    progress = 100;
                    for (_k = 0, _len2 = files.length; _k < _len2; _k++) {
                        file = files[_k];
                        if (!(file.upload.progress === 100 && file.upload.bytesSent === file.upload.total)) {
                            allFilesFinished = false;
                        }
                        file.upload.progress = progress;
                        file.upload.bytesSent = file.upload.total;
                    }
                    if (allFilesFinished) {
                        return;
                    }
                }
                _results = [];
                for (_l = 0, _len3 = files.length; _l < _len3; _l++) {
                    file = files[_l];
                    _results.push(_this.emit("uploadprogress", file, progress, file.upload.bytesSent));
                }
                return _results;
            };
            xhr.onload = function(e) {
                var _ref;
                if (files[0].status === Dropzone.CANCELED) {
                    return;
                }
                if (xhr.readyState !== 4) {
                    return;
                }
                response = xhr.responseText;
                if (xhr.getResponseHeader("content-type") && ~xhr.getResponseHeader("content-type").indexOf("application/json")) {
                    try {
                        response = JSON.parse(response);
                    } catch (_error) {
                        e = _error;
                        response = "Invalid JSON response from server.";
                    }
                }
                updateProgress();
                if (!((200 <= (_ref = xhr.status) && _ref < 300))) {
                    return handleError();
                } else {
                    return _this._finished(files, response, e);
                }
            };
            xhr.onerror = function() {
                if (files[0].status === Dropzone.CANCELED) {
                    return;
                }
                return handleError();
            };
            progressObj = (_ref = xhr.upload) != null ? _ref : xhr;
            progressObj.onprogress = updateProgress;
            headers = {
                "Accept": "application/json",
                "Cache-Control": "no-cache",
                "X-Requested-With": "XMLHttpRequest"
            };
            if (_this.options.headers) {
                extend(headers, _this.options.headers);
            }
            for (headerName in headers) {
                headerValue = headers[headerName];
                xhr.setRequestHeader(headerName, headerValue);
            }

            formData = new FormData();
            if (_this.options.params) {
                _ref1 = _this.options.params;
                for (key in _ref1) {
                    value = _ref1[key];
                    formData.append(key, value);
                }
            }
            for (_j = 0, _len1 = files.length; _j < _len1; _j++) {
                file = files[_j];
                _this.emit("sending", file, xhr, formData);
            }
            if (_this.options.uploadMultiple) {
                _this.emit("sendingmultiple", files, xhr, formData);
            }
            if (wasSigned) {
                //S3 SPECIFIC
                //Used for single file uploads only
                return xhr.send(files[0]);
            } else {
            if (_this.element.tagName === "FORM") {
                _ref2 = _this.element.querySelectorAll("input, textarea, select, button");
                for (_k = 0, _len2 = _ref2.length; _k < _len2; _k++) {
                    input = _ref2[_k];
                    inputName = input.getAttribute("name");
                    inputType = input.getAttribute("type");
                    if (input.tagName === "SELECT" && input.hasAttribute("multiple")) {
                        _ref3 = input.options;
                        for (_l = 0, _len3 = _ref3.length; _l < _len3; _l++) {
                            option = _ref3[_l];
                            if (option.selected) {
                                formData.append(inputName, option.value);
                            }
                        }
                    } else if (!inputType || ((_ref4 = inputType.toLowerCase()) !== "checkbox" && _ref4 !== "radio") || input.checked) {
                        formData.append(inputName, input.value);
                    }
                }
            }
            for (_m = 0, _len4 = files.length; _m < _len4; _m++) {
                file = files[_m];
                formData.append("" + _this.options.paramName + (_this.options.uploadMultiple ? "[]" : ""), file, file.name);
            }
            return xhr.send(formData);
        }
    });
};

module.exports = Dropzone;
/*jshint ignore:end */
