webpackJsonp([22],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

	var AddonHelper = __webpack_require__(54);
	var $ = __webpack_require__(14);
	__webpack_require__(59);

	if (!window.contextVars.currentUser.hasAuth) {

	    $(document).ready(function () {

	        $(window.contextVars.s3SettingsSelector).on('submit', function (evt) {
	            evt.preventDefault();
	            var $this = $(this);
	            var addon = $this.attr('data-addon');
	            var msgElm = $this.find('.addon-settings-message');
	            var url = window.contextVars.node.urls.api + addon + '/authorize/';

	            $.ajax({
	                url: url,
	                data: JSON.stringify(AddonHelper.formToObj($this)),
	                type: 'POST',
	                contentType: 'application/json',
	                dataType: 'json'
	            }).done(function () {
	                msgElm.text('S3 access keys loading...')
	                        .removeClass('text-danger').addClass('text-info')
	                        .fadeIn(1000);
	                setTimeout(function(){
	                    window.location.reload();
	                }, 5000);
	            }).fail(function (xhr) {
	                var message = 'Error: ';
	                var response = JSON.parse(xhr.responseText);
	                if (response && response.message) {
	                    message += response.message;
	                } else {
	                    message += 'Settings not updated.';
	                }
	                msgElm.text(message)
	                    .removeClass('text-success').addClass('text-danger')
	                    .fadeOut(100).fadeIn();
	            });

	            return false;

	        });

	    });

	} else {
	    $(document).ready(function () {
	        $(window.contextVars.s3SettingsSelector).on('submit', AddonHelper.onSubmitSettings);
	    });
	}


/***/ },

/***/ 54:
/***/ function(module, exports, __webpack_require__) {

	// TODO: Deprecate me
	var $osf = __webpack_require__(2);
	var $ = __webpack_require__(14);

	var AddonHelper = (function() {

	    /**
	     * Convert an HTML form to a JS object.
	     *
	     * @param {jQuery} form
	     * @return {Object} The parsed data
	     */
	    function formToObj(form) {
	        var rv = {};
	        $.each($(form).serializeArray(), function(_, value) {
	            rv[value.name] = value.value;
	        });
	        return rv;
	    }

	    /**
	     * Submit add-on settings.
	     */
	    function onSubmitSettings() {
	        var $this = $(this);
	        var addon = $this.attr('data-addon');
	        var owner = $this.find('span[data-owner]').attr('data-owner');
	        var msgElm = $this.find('.addon-settings-message');

	        var url = owner == 'user'
	            ? '/api/v1/settings/' + addon + '/'
	            : nodeApiUrl + addon + '/settings/';

	        $osf.postJSON(
	            url,
	            formToObj($this)
	        ).done(function() {
	            msgElm.text('Settings updated')
	                .removeClass('text-danger').addClass('text-success')
	                .fadeOut(100).fadeIn();
	        }).fail(function(response) {
	            var message = 'Error: ';
	            var response = JSON.parse(response.responseText);
	            if (response && response.message) {
	                message += response.message;
	            } else {
	                message += 'Settings not updated.'
	            }
	            msgElm.text(message)
	                .removeClass('text-success').addClass('text-danger')
	                .fadeOut(100).fadeIn();
	        });

	        return false;

	    }

	    // Expose public methods
	    exports = {
	        formToObj: formToObj,
	        onSubmitSettings: onSubmitSettings,
	    };

	    if (true) {
	        module.exports = exports; 
	    } 
	    return exports;
	})();




/***/ },

/***/ 59:
/***/ function(module, exports, __webpack_require__) {

	var $osf = __webpack_require__(2);
	var bootbox = __webpack_require__(11);
	var $ = __webpack_require__(14);

	(function() {

	    function newBucket() {
	        var isValidBucket = /^(?!.*(\.\.|-\.))[^.][a-z0-9\d.-]{2,61}[^.]$/;
	        var $elm = $('#addonSettingsS3');
	        var $select = $elm.find('select');

	        bootbox.prompt('Name your new bucket', function(bucketName) {

	            if (!bucketName) {
	                return;
	            } else if (isValidBucket.exec(bucketName) == null) {
	                bootbox.confirm({
	                    title: 'Invalid bucket name',
	                    message: "Sorry, that's not a valid bucket name. Try another name?",
	                    callback: function(result) {
	                        if(result) {
	                            newBucket();
	                        }
	                    }
	                });
	            } else {
	                bucketName = bucketName.toLowerCase();
	                $osf.postJSON(
	                    nodeApiUrl + 's3/newbucket/',
	                    {bucket_name: bucketName}
	                ).done(function() {
	                    $select.append('<option value="' + bucketName + '">' + bucketName + '</option>');
	                    $select.val(bucketName);
	                }).fail(function(xhr) {
	                    var message = JSON.parse(xhr.responseText).message;
	                    if(!message) {
	                        message = 'Looks like that name is taken. Try another name?';
	                    }
	                    bootbox.confirm({
	                        title: 'Duplicate bucket name',
	                        message: message,
	                        callback: function(result) {
	                            if(result) {
	                                newBucket();
	                            }
	                        }
	                    });
	                });
	            }
	        });
	    }

	    var removeNodeAuth = function() {
	        $.ajax({
	            type: 'DELETE',
	            url: nodeApiUrl + 's3/settings/',
	            contentType: 'application/json',
	            dataType: 'json'
	        }).done(function() {
	            window.location.reload();
	        }).fail(
	            $osf.handleJSONError
	        );
	    };

	    function importNodeAuth() {
	        $osf.postJSON(
	            nodeApiUrl + 's3/import-auth/',
	            {}
	        ).done(function() {
	            window.location.reload();
	        }).fail(
	            $osf.handleJSONError
	        );
	    }

	    $(document).ready(function() {

	        $('#newBucket').on('click', function() {
	            newBucket();
	        });

	        $('#s3RemoveToken').on('click', function() {
	            bootbox.confirm({
	                title: 'Deauthorize S3?',
	                message: 'Are you sure you want to remove this S3 authorization?',
	                callback: function(confirm) {
	                    if(confirm) {
	                        removeNodeAuth();
	                    }
	                }
	            });
	        });

	        $('#s3ImportToken').on('click', function() {
	            importNodeAuth();
	        });

	        $('#addonSettingsS3 .addon-settings-submit').on('click', function() {
	            var $bucket = $('#s3_bucket');
	            if ($bucket.length && !$bucket.val()) {
	                return false;
	            }
	        });

	    });

	})();


/***/ }

});