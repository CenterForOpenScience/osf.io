'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');

var oop = require('js/oop');

// Private, cached user
var currentUser = null;

/**
 * Utility for getting info for the currently logged-in user.
 * Use the getCurrentUser() method to get the profile of the currently logged
 * in user.
 *
 * Usage:
 *
 *      var promise = Auth.getCurrentUser();
 *
 *      promise.done(function(user) {
 *          console.log(user);  // => {id: 'ab123', ...}
 *      }
 */
var Auth = oop.defclass({
    constructor: function(profileUrl) {
        var self = this;
        self.profileUrl = profileUrl;
    },
    ///**
    // * Returns a promise for the current user profile.
    // * If no user is logged in, resolves to null.
    // */
    getCurrentUser: function () {
        var self = this;
        var ret = $.Deferred();
        // Resolve to cached user if possible
        if (currentUser) {
            ret.resolve(currentUser);
        } else { // Request for user, resolve to the user, and cache it
            self._requestUser().done(function (user) {
                ret.resolve(user);
            })
            .fail(function (xhr, error, status) {
                ret.reject(xhr, error, status);
            });
        }
        return ret.promise();
    },
    /**
     * Sets the user to a private module level variable.
     */
    _setUser: function (user) {
        currentUser = user;
    },
    /**
     * Sends a request to the /profile endpoint, which returns the
     * profile of the current user, or null.
     */
    _requestUser: function () {
        var self = this;
        return $.ajax({
            url: self.profileUrl,
            dataType: 'json',
            beforeSend: $osf.setXHRAuthorization
        }).done(function (resp) {
            self._setUser(resp);
        });
    }
});

module.exports = Auth;
