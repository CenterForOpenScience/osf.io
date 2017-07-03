'use strict';

var DryadConfig = require('./dryadNodeConfig').DryadNodeConfig;

var api_url = window.contextVars.node.urls.api;
var url = api_url+'dryad/settings';


var config = new DryadConfig('#DryadStatusScope', url, '#dryadGrid');
config.viewModel.fetch();

var dryad_browser_init=false;
$('#DryadBrowserScope .panel-heading').click(function(){
    if(!dryad_browser_init){
        config.viewModel.browseTo(20,0);
        dryad_browser_init=true;
    }
});
var dryad_citation_init = false;
$('#DryadCitationScope .panel-heading').click(function(){
    if(!dryad_citation_init){
        config.viewModel.fetchCitation();
        dryad_citation_init=true;
    }
});
