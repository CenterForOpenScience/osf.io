'use strict';
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var m = require('mithril');
require('js/qToggle');
require('js/components/autocomplete');
require('js/projectsSelect.js');

$(function(){
    $('.prereg-button').qToggle();
    $('.prereg-button').click(function(){
        var target = $(this).attr('data-qToggle-target');
        var input = $(target).find('input').first().focus();
    });

    // New projects
    $('#newProject, #newProjectXS').click( function() {
        var title = $(this).parent().find('.new-project-title').val();
        if (!title) {
            return;
        }
        $osf.postJSON('/api/v1/project/new/', {
            title: title,
            campaign: 'prereg'
        }).done(function(response) {
            window.location = response.projectUrl + 'registrations/?campaign=prereg';
        }).fail(function() {
            $osf.growl('Project creation failed. Reload the page and try again.');
        });
    });

    // Existing Nodes
    var allNodes = [];
    function onSelectProject (event, data) {
        var link = data.links.html + 'registrations/';
        $('#existingProject .projectRegButton').removeClass('disabled').attr('href', link);
        $('#existingProjectXS .projectRegButton').removeClass('disabled').attr('href', link);
    }
    // Get all projects with multiple calls to get all pages
    function collectProjects (url) {
        var promise = $.ajax({
            method: 'GET',
            url: url,
            xhrFields: {
                withCredentials: true
            }
        });
        promise.done(function(result){
            // loop through items and check for admin permission first
            result.data.forEach(function(item){
                item.formattedDate = new $osf.FormattableDate(item.attributes.date_modified);
                if(item.attributes.current_user_permissions.indexOf('admin') > -1){
                    allNodes.push(item);
                }
            });
            if(result.links.next){
                collectProjects(result.links.next);
            }
            else {
                $('#projectSearch').projectsSelect({data : allNodes, complete : onSelectProject});
                $('#projectSearchXS').projectsSelect({data : allNodes, complete : onSelectProject});
            }
        });
        promise.fail(function(xhr, textStatus, error) {
            Raven.captureMessage('Next page load failed for user nodes.', {
                extra: { url: url, textStatus: textStatus, error: error }
            });
        });
    }
    var nodeLink = $osf.apiV2Url('users/me/nodes/', { query : { 'page[size]' : 100}});
    collectProjects(nodeLink);

    function onSelectRegistrations (event, data) {
        $('#existingPrereg .regDraftButton').removeClass('disabled').attr('href', data.url);
        $('#existingPreregXS .regDraftButton').removeClass('disabled').attr('href', data.url);
    }

    // Existing Draft Registrations
    $.getJSON('/api/v1/prereg/draft_registrations/').then(function(response){
        if (response.draftRegistrations.length) {
            $('#regDraftSearch').projectsSelect({data : response.draftRegistrations, type : 'registration', complete : onSelectRegistrations});
            $('#regDraftSearchXS').projectsSelect({data : response.draftRegistrations, type : 'registration', complete : onSelectRegistrations});
        }
    });
});
