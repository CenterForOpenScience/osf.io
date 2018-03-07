'use strict';
var $ = require('jquery');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');
var Cookie = require('js-cookie');
var ctx = window.contextVars;

var changeAddonSettingsSuccess = function () {
    $osf.growl('Success', 'Your add-on settings have been successfully changed.', 'success');
    location.reload();
};

var changeAddonSettingsFailure = function () {
    var msg = 'Sorry, we had trouble saving your settings. If this persists please contact <a href="mailto: support@osf.io">support@osf.io</a>';
    $osf.growl('Failure', msg, 'danger');
};

$(function(){
    // Make zotero group library message permanently dismissible
    var zoteroPersistKey = 'zoteroGroupDismiss';
    var $zoteroPersist = $('#zoteroWarningCancel').click(function() {
        Cookie.set(zoteroPersistKey, '1', {path: '/'});
    });
    var dismissed = Cookie.get(zoteroPersistKey) === '1';
    if (!dismissed) {
        $('#zotero-group-library-alert').show();
    }
});


$('.addon-container').each(function(ind, elm) {
    elm = $(elm);
    if(elm.attr('status') === 'enabled'){
        elm.find('a').bind('click', function () {
            var data = {};
            data[elm.attr('name')] = false;
            bootbox.confirm({
                title: 'Disable Add-on?',
                message: 'Are you sure you want to disable this add-on?',
                callback: function (result) {
                    if (result) {
                        var request = $osf.postJSON(ctx.node.urls.api + 'settings/addons/', data);
                        request.done(changeAddonSettingsSuccess);
                        request.fail(changeAddonSettingsFailure);
                    }
                },
                buttons: {
                    confirm: {
                        label: 'Disable',
                        className: 'btn-danger'
                    }
                }
            });
        });
    } else {
        elm.find('a').bind('click', function () {
            var data = {};
            var name = elm.attr('name');
            data[name] = true;
            var capabilities = $('#capabilities-' + name).html();
            bootbox.confirm({
                message: capabilities,
                callback: function(result) {
                    if (result) {
                        var request = $osf.postJSON(ctx.node.urls.api + 'settings/addons/', data);
                        request.done(changeAddonSettingsSuccess);
                        request.fail(changeAddonSettingsFailure);
                    }
                },
                buttons:{
                    confirm:{
                        label:'Confirm'
                    }
                }
            });
        });
    }
});

var filterAddons = function(event) {
    var input = document.getElementById('filter-addons');
    var filter = input.value.toUpperCase();
    var containers = document.getElementsByClassName('addon-container');
    var active_category;
    if(event.target.localName === 'input'){
        active_category =  document.querySelectorAll('.addon-categories.active')[0].getAttribute('name');
    } else {
        active_category = event.target.getAttribute('name');
    }
    for (var i = 0; i < containers.length; i++) {
        if (containers[i].getAttribute('full_name').toUpperCase().indexOf(filter) > -1 &&
                (containers[i].getAttribute('categories').toUpperCase().indexOf(active_category.toUpperCase()) > -1 ||
                active_category === 'All' ))
        {
            containers[i].style.display = '';
        } else {
            containers[i].style.display = 'none';
        }
    }
};

$('#filter-addons').keyup(filterAddons);
$('.addon-categories').click(filterAddons);
