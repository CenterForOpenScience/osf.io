'use strict';

var Gettext = require('node-gettext');
var $osf = require('js/osfHelpers');

var acceptLanguages = ['en','ja','fr'];
var defaultLanguage = 'en';
var translationsBaseDir = 'translations';
var osfLanguageProfileBaseName = 'osfLanguage';
var getTextDomain = 'messages';
var browserLanguage;

var getBrowserLang = function() {
    var language = defaultLanguage;
    var langCode = defaultLanguage;
    var applyLanguage = false;
    var endIndex;

    if(window.navigator.languages){
        for(var i=0 ; i<window.navigator.languages.length ; i++) {
            browserLanguage = (window.navigator.languages && window.navigator.languages[i]);
            langCode = browserLanguage.split('-')[0];

            for(var j=0 ; j<acceptLanguages.length ; j++) {
                if(langCode === acceptLanguages[j]) {
                    language = langCode;
                    applyLanguage = true;
                    break;
                }
            }
            if (applyLanguage) break;
        }
    }
    return language;
};

var rdmGettext = function() {
    var gt = new Gettext();
    var currentlanguage = getBrowserLang();
    for(var i = 0; i < acceptLanguages.length; i++) {
        var translation = require('js/translations/' + acceptLanguages[i] + '.json');
        gt.addTranslations(acceptLanguages[i], getTextDomain, translation);
    }
    gt.setLocale(currentlanguage);
    return gt;
};

var OsfLanguage = function() {
    var defaultDomain = [].slice.call(arguments);
    this.languages = {};
    for(var i = 0; i < acceptLanguages.length; i++) {
        var language = require('js/translations/' + osfLanguageProfileBaseName + '_' + acceptLanguages[i]);
        for(var j = 0; j < defaultDomain.length; j++) {
            language = language[defaultDomain[j]];
        }
        this.languages[acceptLanguages[i]] = language;
    }

    this.t = function() {
        var msgid = [].slice.call(arguments);
        var browserlanguage = getBrowserLang();
        var msgstr = this.languages[browserlanguage];
        for(var i = 0; i < msgid.length; i++) {
            msgstr = msgstr[msgid[i]];
        }
        return msgstr;
    };
};

var _ = function(msgid) {
        var gt = rdmGettext();
        return gt.gettext(msgid);
};

module.exports = {
    rdmGettext: rdmGettext,
    getBrowserLang: getBrowserLang,
    OsfLanguage: OsfLanguage,
    _: _
};
