/**
 * Knockout extender that adds password complexity checking to observables.
 *
 * Usage:
 *    require('js/knockoutPassword');
 *    var password = ko.observable('').extend({passwordChecking: true});
 *    password('password')
 *    password.passwordComplexity()  // output a complexity score from 1-5
 *    password.passwordFeedback() // output an object with warnings and suggestions
 */
'use strict';
var ko = require('knockout');
var zxcvbn = require('zxcvbn');

ko.extenders.passwordChecking = function(observable, option) {

    observable.passwordComplexity = ko.observable(0);
    observable.passwordFeedback = ko.observable({});

    function check(newValue) {
        if (observable()) {
            // Truncate the password to first 100 characters for efficiency
             var passwordInfo = zxcvbn(newValue.slice(0, 100));
             observable.passwordComplexity(passwordInfo.score + 1);
             observable.passwordFeedback(passwordInfo.feedback);
        }
    }

    observable.subscribe(check);
    return observable;
};
