webpackJsonp([31],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

	var ForwardConfig = __webpack_require__(51);

	var url = window.contextVars.node.urls.api + 'forward/config/';
	new ForwardConfig('#forwardScope', url, window.contextVars.node.id);

/***/ },

/***/ 51:
/***/ function(module, exports, __webpack_require__) {

	'use strict';

	var ko = __webpack_require__(16);
	__webpack_require__(7);
	var koHelpers = __webpack_require__(70);
	var $ = __webpack_require__(14);
	var $osf = __webpack_require__(2);
	var Raven = __webpack_require__(15);

	ko.punches.enableAll();

	var MESSAGE_TIMEOUT = 5000;
	var MIN_FORWARD_TIME = 5;
	var MAX_FORWARD_TIME = 60;

	var DEFAULT_FORWARD_BOOL = true;
	var DEFAULT_FORWARD_TIME = 15;

	/**
	 * Knockout view model for the Forward node settings widget.
	 */
	var ViewModel = function(url, nodeId) {

	    var self = this;

	    self.boolOptions = [true, false];
	    self.boolLabels = {
	        true: 'Yes',
	        false: 'No'
	    };

	    // Forward configuration
	    self.url = ko.observable().extend({
	        ensureHttp: true,
	        url: true,
	        required: true
	    });
	    ko.validation.addAnonymousRule(
	        self.url,
	        koHelpers.makeRegexValidator(
	            new RegExp(nodeId, 'i'),
	            'Components cannot link to themselves',
	            false
	        )
	    );
	    self.label = koHelpers.sanitizedObservable();
	    self.redirectBool = ko.observable(DEFAULT_FORWARD_BOOL);
	    self.redirectSecs = ko.observable(DEFAULT_FORWARD_TIME).extend({
	        required: true,
	        min: MIN_FORWARD_TIME,
	        max: MAX_FORWARD_TIME
	    });

	    // Flashed messages
	    self.message = ko.observable('');
	    self.messageClass = ko.observable('text-info');

	    self.validators = ko.validatedObservable({
	        url: self.url,
	        redirectBool: self.redirectBool,
	        redirectSecs: self.redirectSecs
	    });

	    self.getBoolLabel = function(item) {
	        return self.boolLabels[item];
	    };

	    /**
	     * Update the view model from data returned from the server.
	     */
	    self.updateFromData = function(data) {
	        self.url(data.url);
	    self.label(data.label);
	        self.redirectBool(data.redirectBool);
	        self.redirectSecs(data.redirectSecs);
	    };

	    self.fetchFromServer = function() {
	        $.ajax({
	            type: 'GET',
	            url: url,
	            dataType: 'json'
	        }).done(function(response) {
	            self.updateFromData(response);
	        }).fail(function(xhr, textStatus, error) {
	            self.changeMessage('Could not retrieve Forward settings at ' +
	                'this time. Please refresh ' +
	                'the page. If the problem persists, email ' +
	                '<a href="mailto:support@osf.io">support@osf.io</a>.',
	                'text-warning');
	            Raven.captureMessage('Could not GET get Forward addon settings.', {
	                url: url,
	                textStatus: textStatus,
	                error: error
	            });
	        });
	    };

	    // Initial fetch from server
	    self.fetchFromServer();

	    function onSubmitSuccess() {
	        self.changeMessage(
	            'Successfully linked to <a href="' + self.url() + '">' + self.url() + '</a>.',
	            'text-success',
	            MESSAGE_TIMEOUT
	        );
	    }

	    function onSubmitError(xhr, status) {
	        self.changeMessage(
	            'Could not change settings. Please try again later.',
	            'text-danger'
	        );
	    }

	    /**
	     * Submit new settings.
	     */
	    self.submitSettings = function() {
	        $osf.putJSON(
	            url,
	            ko.toJS(self)
	        ).done(
	            onSubmitSuccess
	        ).fail(
	            onSubmitError
	        );
	    };

	    /** Change the flashed message. */
	    self.changeMessage = function(text, css, timeout) {
	        self.message(text);
	        var cssClass = css || 'text-info';
	        self.messageClass(cssClass);
	        if (timeout) {
	            // Reset message after timeout period
	            setTimeout(function() {
	                self.message('');
	                self.messageClass('text-info');
	            }, timeout);
	        }
	    };

	};

	// Public API
	function ForwardConfig(selector, url, nodeId) {
	    var self = this;
	    self.viewModel = new ViewModel(url, nodeId);
	    $osf.applyBindings(self.viewModel, selector);
	}

	module.exports = ForwardConfig;



/***/ },

/***/ 70:
/***/ function(module, exports, __webpack_require__) {

	'use strict';

	var ko = __webpack_require__(16);

	var makeExtender = function(interceptor) {
	    return function(target, options) {
	        var result = ko.computed({
	            read: target,
	            write: function(value) {
	                var current = target();
	                var toWrite = interceptor(value, options);
	                if (current !== toWrite) {
	                    target(toWrite);
	                } else {
	                    if (current !== value) {
	                        target.notifySubscribers(toWrite);
	                    }
	                }
	            }
	        }).extend({
	            notify: 'always'
	        });
	        result(target());
	        return result;
	    };
	};

	var addExtender = function(label, interceptor) {
	    ko.extenders[label] = makeExtender(interceptor);
	};

	var makeRegexValidator = function(regex, message, match) {
	    match = match || match === undefined;
	    return {
	        validator: function(value) {
	            if (ko.validation.utils.isEmptyVal(value)) {
	                return true;
	            }
	            return match === regex.test(ko.utils.unwrapObservable(value));
	        },
	        message: message
	    };
	};

	addExtender('cleanup', function(value, cleaner) {
	    return !!value ? cleaner(value) : '';
	});

	addExtender('ensureHttp', function(value) {
	    if (!value || value.search(/^https?:\/\//i) === 0) {
	        return value;
	    }
	    return 'http://' + value;
	});

	var sanitize = function(value) {
	    return value.replace(/<\/?[^>]+>/g, '');
	};

	var sanitizedObservable = function(value) {
	    return ko.observable(value).extend({
	        cleanup: sanitize
	    });
	};

	// Add custom validators

	ko.validation.rules.minDate = {
	    validator: function (val, minDate) {
	        // Skip if values empty
	        var uwVal = ko.utils.unwrapObservable(val);
	        var uwMin = ko.utils.unwrapObservable(minDate);
	        if (uwVal === null || uwMin === null) {
	            return true;
	        }
	        // Skip if dates invalid
	        var dateVal = new Date(uwVal);
	        var dateMin = new Date(uwMin);
	        if (dateVal.toString() === 'Invalid Date' || dateMin.toString() === 'Invalid Date') {
	            return true;
	        }
	        // Check if end date is ongoing
	        if (uwVal === 'ongoing') {
	            return true;
	        }
	        // Compare dates
	        return dateVal >= dateMin;
	    },
	    message: 'End date must be greater than or equal to the start date.'
	};

	ko.validation.rules.pyDate = {
	    validator: function (val) {
	        // Skip if values empty
	        var uwVal = ko.utils.unwrapObservable(val);
	        if (uwVal === null) {
	            return true;
	        }
	        // Skip if dates invalid
	        var dateVal = new Date(uwVal);
	        if (dateVal.toString() === 'Invalid Date') {
	            return true;
	        }
	        // Compare years
	        return parseInt(uwVal) >= 1900;
	    },
	    message: 'Date must be greater than or equal to 1900.'
	};

	ko.validation.rules.notInFuture = {
	    validator: function (val) {
	        // Skip if values empty
	        var uwVal = ko.utils.unwrapObservable(val);
	        if (uwVal === null || uwVal === undefined) {
	            return true;
	        }

	        //Skip if dates invalid
	        var dateVal = new Date(uwVal);

	        if (dateVal.toString() === 'Invalid Date') {
	            return true;
	        }
	        // Compare dates
	        var now = new Date();
	        return dateVal <= now;

	    },
	    message: 'Please enter a date prior to the current date.'
	};


	ko.validation.rules.year = makeRegexValidator(
	    new RegExp('^\\d{4}$'),
	    'Please enter a valid year.'
	);


	ko.validation.rules.url = makeRegexValidator(
	    new RegExp(
	        '^(?:http|ftp)s?://' +
	            '(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\\.)+(?:[A-Z]{2,6}\\.?|[A-Z0-9-]{2,}\\.?)|' +
	            'localhost|' +
	            '\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}|' +
	            '\\[?[A-F0-9]*:[A-F0-9:]+\\]?)' +
	            '(?::\\d+)?' +
	            '(?:/?|[/?]\\S+)$',
	        'i'
	    ),
	    'Please enter a valid URL.'
	);

	// Expose public utilities

	module.exports = {
	    makeExtender: makeExtender,
	    addExtender: addExtender,
	    makeRegexValidator: makeRegexValidator,
	    sanitizedObservable: sanitizedObservable
	};


/***/ }

});