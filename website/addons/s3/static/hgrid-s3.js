
(function(FileBrowser) {

    // Private stuff

    // Public stuff
    FileBrowser.cfg.github = {
        listeners: [
            {
                on: 'change',
                selector: '.github-branch-select',
                callback: function(){}
            }
        ],
        uploadUrl: function(row) {
            return $.ajax({
                type: 'put',
                url: '/path/to/signed/link',
            });
        }
    };

})(FileBrowser);


//TODO Dir
function unused(file)
{
  $.ajax({
      url:  uplUrl + 's3/getsigned/',
      type: 'POST',
      data: JSON.stringify({name:file.name,type:file.type}),
      contentType: 'application/json',
      dataType: 'json'
        }).success(function(url) {

            xhr = new XMLHttpRequest();

            if (xhr.withCredentials != null) {
                xhr.open('PUT', url, true);
            } else if (typeof XDomainRequest !== "undefined") {
                xhr = new XDomainRequest();
                xhr.open('PUT', url);
            } else {
                xhr = null;
            }
            xhr.onload = function() {
                if (xhr.status === 200) {
                    console.log("completed")
                } else {
                    console.log('Upload error: ' + xhr.status);
                }
            };
            xhr.onerror = function() {
                console.log('XHR error.', file);
            };
            xhr.upload.onprogress = function(e) {
                var percentLoaded;
                if (e.lengthComputable) {
                    percentLoaded = Math.round((e.loaded / e.total) * 100);
                    console.log(percentLoaded)
                }
            };

            type = file.type || 'application/octet-stream';

            xhr.setRequestHeader('Content-Type', type);
            xhr.setRequestHeader('x-amz-acl', 'private');
            return xhr.send(file);

        });
};
