/**
 * Login page
 */
'use strict';
var $ = require('jquery');
var ko = require('knockout');

var $osf = require('js/osfHelpers');
var SignUp = require('js/signUp');
var LogInForm = require('js/signIn');

ko.punches.enableAll();

var registerUrl = window.contextVars.registerUrl;


var activateToggleBox = function () {
    var el = $(this);

    if (el.hasClass('toggle-box-muted')) {
        $('.toggle-box-active').removeClass('toggle-box-active').addClass('toggle-box-muted');
        el.removeClass('toggle-box-muted').addClass('toggle-box-active');
    }
};


var InstitutionViewModel = function() {
    var self = this;
    self.inst_names = ko.observableArray([]);
    self.insts = {};
    $osf.ajaxJSON(
        'GET',
        window.contextVars.apiV2Prefix + 'institutions/',
        {
            isCors: true
        }
    ).done( function(response){
        for (var i = 0; i < response.data.length; i++){
            var name = response.data[i].attributes.name;
            self.inst_names.push(name);
            self.insts[name] = response.data[i].attributes.auth_url;
        }
    }).fail(function(response){
    });

    self.instLogin = function(){
        var key = $('#selected_inst').val();
        window.location = self.insts[key];
    };
};


$(document).ready(function() {
    var self = this;
    self.campaign = $('#campaign').val();
    if (self.campaign === 'institution'){
        self.viewModel = new InstitutionViewModel();
        $osf.applyBindings(self.viewModel, '#inst');
    } else {
        new LogInForm.SignIn('#logInForm');
        new SignUp('#signUpScope', registerUrl, $('#campaign').val());
    }
});

$('.toggle-box').on('click', activateToggleBox);
$('.toggle-box').on('focus', '*', function() {
    activateToggleBox.apply( $(this).parents('.toggle-box') );
});

