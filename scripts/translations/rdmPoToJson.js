'use strict';
var gettextParser = require('gettext-parser');
var fs = require('fs');
var acceptLanguages = ['en','ja'];
var translationsBaseDir = 'translations';
var getTextDomain = 'messages';
var jsRelativePath = './website/static/js/' +  translationsBaseDir + '/';
var localeDir = 'LC_MESSAGES';
var langCode;
var input;
var po;
    for(var i=0 ; i<acceptLanguages.length ; i++){
            langCode = acceptLanguages[i];
            input = fs.readFileSync(jsRelativePath + langCode + '/' + localeDir + '/' + getTextDomain + '.po');
            po = gettextParser.po.parse(input);
            fs.writeFileSync(jsRelativePath + '/' + langCode + '.json' , JSON.stringify(po));
    }
    