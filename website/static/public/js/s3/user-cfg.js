webpackJsonp([9],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

	var AddonHelper = __webpack_require__(54);
	var $ = __webpack_require__(14);
	var bootbox = __webpack_require__(11);

	$('#s3RemoveAccess').on('click', function() {
	    bootbox.confirm({
	        title: 'Remove access key?',
	        message: 'Are you sure you want to remove your Amazon Simple Storage Service access key? ' +
	                'This will revoke access to Amazon S3 for all projects you have authorized and ' +
	                'delete your access token from Amazon S3. Your OSF collaborators will not be able ' +
	                'to write to Amazon S3 buckets or view private buckets that you have authorized.',
	        callback: function(result) {
	            if(result) {
	                deleteToken();
	            }
	        }
	    });
	});

	function deleteToken() {
	    var $this = $(this),
	    addon = $this.attr('data-addon'),
	    msgElm = $this.find('.addon-settings-message');
	    $.ajax({
	        type: 'DELETE',
	        url: '/api/v1/settings/s3/',
	        contentType: 'application/json',
	        dataType: 'json',
	        success: function(response) {
	            msgElm.text('Keys removed')
	                .removeClass('text-danger').addClass('text-success')
	                .fadeOut(100).fadeIn();
	            window.location.reload();
	        },
	        error: function(xhr) {
	            var response = JSON.parse(xhr.responseText);
	            if (response && response.message) {
	                if(response.message === 'reload')
	                    window.location.reload();
	                else
	                    message = response.message;
	            } else {
	                message = 'Error: Keys not removed';
	            }
	            msgElm.text(message)
	                .removeClass('text-success').addClass('text-danger')
	                .fadeOut(100).fadeIn();
	        }
	    });
	    return false;
	}

	$(document).ready(function() {
	    $(window.contextVars.addonSettingsSelector).on('submit', AddonHelper.onSubmitSettings);
	});


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




/***/ }

});