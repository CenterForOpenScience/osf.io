//From https://github.com/elasticsales/s3upload-coffee-javascript

(function() {
  window.S3Upload = (function() {
    S3Upload.prototype.s3_sign_put_url = '';

    S3Upload.prototype.file_dom_selector = '';

    S3Upload.prototype.onFinishS3Put = function(public_url, file) {
      return console.log('base.onFinishS3Put()', public_url, file);
    };

    S3Upload.prototype.onProgress = function(percent, status, public_url, file) {
      return console.log('base.onProgress()', percent, status, public_url, file);
    };

    S3Upload.prototype.onError = function(status, file) {
      return console.log('base.onError()', status, file);
    };

    function S3Upload(options) {
      if (options == null) {
        options = {};
      }
      $.extend(this, options);
      if (this.file_dom_selector) {
        this.handleFileSelect($(this.file_dom_selector).get(0));
      }
    }

    S3Upload.prototype.handleFileSelect = function(file_element) {
      var f, files, output, _i, _len, _results;
      this.onProgress(0, 'Upload started.');
      files = file_element.files;
      output = [];
      _results = [];
      for (_i = 0, _len = files.length; _i < _len; _i++) {
        f = files[_i];
        _results.push(this.uploadFile(f));
      }
      return _results;
    };

    S3Upload.prototype.createCORSRequest = function(method, url) {
      var xhr;
      xhr = new XMLHttpRequest();
      if (xhr.withCredentials != null) {
        xhr.open(method, url, true);
      } else if (typeof XDomainRequest !== "undefined") {
        xhr = new XDomainRequest();
        xhr.open(method, url);
      } else {
        xhr = null;
      }
      return xhr;
    };

    S3Upload.prototype.executeOnSignedUrl = function(file, callback, opts) {

      $.ajax({
              url: '/eha9r/s3/getsigned/',
              type: 'POST',
              data: JSON.stringify({name:file.name,type:file.type}),
              contentType: 'application/json',
              dataType: 'json'
          }).complete(function(r) {
              console.log(r)
              result = JSON.parse(r.responseText);
               return callback(result.signed_request, result.url);

          }).error(function(x,e) {
              console.log(x + " " + e)
          });
    };

    S3Upload.prototype.uploadToS3 = function(file, url, public_url, opts) {
      var this_s3upload, type, xhr;
      this_s3upload = this;
      type = opts && opts.type || file.type || "application/octet-stream";
      xhr = this.createCORSRequest('PUT', url);
      if (!xhr) {
        this.onError('CORS not supported');
      } else {
        xhr.onload = function() {
          if (xhr.status === 200) {
            this_s3upload.onProgress(100, 'Upload completed.', public_url, file);
            return this_s3upload.onFinishS3Put(public_url, file);
          } else {
            return this_s3upload.onError('Upload error: ' + xhr.status, file);
          }
        };
        xhr.onerror = function() {
          return this_s3upload.onError('XHR error.', file);
        };
        xhr.upload.onprogress = function(e) {
          var percentLoaded;
          if (e.lengthComputable) {
            percentLoaded = Math.round((e.loaded / e.total) * 100);
            console.log(percentLoaded)
            return this_s3upload.onProgress(percentLoaded, (percentLoaded === 100 ? 'Finalizing.' : 'Uploading.'), public_url, file);
          }
        };
      }
      xhr.setRequestHeader('Content-Type', type);
      xhr.setRequestHeader('x-amz-acl', 'public-read');
      return xhr.send(file);
    };

    S3Upload.prototype.validate = function(file) {
      return null;
    };

    S3Upload.prototype.uploadFile = function(file, opts) {
      var error, this_s3upload;
      error = this.validate(file);
      if (error) {
        this.onError(error, file);
        return null;
      }
      this_s3upload = this;
      return this.executeOnSignedUrl(file, function(signedURL, publicURL) {
        return this_s3upload.uploadToS3(file, signedURL, publicURL, opts);
      }, opts);
    };

    return S3Upload;

  })();

}).call(this);