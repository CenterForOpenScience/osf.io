'use strict';

var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');

var _myProjects = require('js/myProjects.js');
var Projects = _myProjects.MyProjects;
var LinkObject = _myProjects.LinkObject;
var InstitutionNodes = require('js/institutionNodes.js');

var _ = require('js/rdmGettext')._;
var agh = require('agh.sprintf');

$(document).ready(function() {
    var institutionId = window.contextVars.institution.id;
    var query = {
      //If we are not on the osf.io we are requesting data anonymously which can be cached for a long time
      //So push the page size to the max for better UX
      'page[size]': window.contextVars.isOnRootDomain ? 10 : 100,
      'embed': 'contributors',
      'related_counts': 'children',
    };
    var instNodes = $osf.apiV2Url('institutions/' + institutionId + '/nodes/', {query: query});
    var instRegs = $osf.apiV2Url('institutions/' + institutionId + '/registrations/', {query: query});
    new InstitutionNodes('#inst', window.contextVars);
    m.mount(document.getElementById('fileBrowser'), m.component(Projects, {
        wrapperSelector : '#fileBrowser',
        systemCollections:[
            new LinkObject('collection', { link : instNodes, query : { 'related_counts' : true, 'page[size]'  : 12, 'embed' : 'contributors'}, nodeType : 'nodes'}, _('All Projects')),
        ],
        viewOnly: true,
        projectOrganizerOptions: {
            resolveToggle: function(){
                return '';
            }
        },
        institutionId: institutionId,
    }));
    setTimeout(function(){
        if($('#inst .spinner-loading-wrapper').length > 0) {
            var OSF_SUPPORT_EMAIL = window.contextVars.osfSupportEmail;
            $('#inst').append('<div class="text-danger text-center text-bigger">' + agh.sprintf(_('This is taking longer than normal. <br>  Try reloading the page. If the problem persist, please contact us at %1$s.') , OSF_SUPPORT_EMAIL) + '</div>');
        }
    }, 10000);
});
