/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';
var $ = require('jquery');

var assert = require('chai').assert;

var utils = require('tests/utils');
var faker = require('faker');

var githubNodeConfigVM = require('../githubNodeConfig')._githubNodeConfigViewModel;

var API_BASE = '/api/v1/12345/github';
var SETTINGS_URL = [API_BASE, 'settings', ''].join('/');
var URLS = {
    create_repo: [API_BASE, 'newrepo', ''].join('/'),
    import_auth: [API_BASE, 'user_auth', ''].join('/'),
    create_auth: [API_BASE, 'oauth', ''].join('/'),
    deauthorize: SETTINGS_URL,
    repo_list: [API_BASE, 'repos', ''].join('/'),
    set_repo: SETTINGS_URL,
    settings: '/settings/addons/'
};