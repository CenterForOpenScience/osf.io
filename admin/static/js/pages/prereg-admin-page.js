var $ = require('jquery');
require('bootstrap');

require('osf-style');

var $osf = require('js/osfHelpers');
var osfLanguage = require('js/osfLanguage');


$(document).ready(function() {
    $('.prereg-draft').click(function() {
        var $drafts = $('.prereg-draft');
        $drafts.removeClass('osf-box-lt');
        $drafts.addClass('osf-box');

        var $draft = $(this);
        $draft.removeClass('osf-box');        
        $draft.addClass('osf-box-lt');
    });

    $('.prereg-draft-save').click(function(e) {

        var $draftElement = $(this).closest('.prereg-draft') ;       
        var $form = $draftElement.find('.prereg-draft-form');
        var data = {};
        $.each($form.serializeArray(), function(_, item) {
            data[item.name] = item.value;
        });

        $osf.block('Saving...', $draftElement);
        $osf.putJSON(
            $form.attr('action'),
            {
                admin_settings: data
            }
        )
            .always($osf.unblock.bind(null, $draftElement))
            .done($osf.growl.bind(null, 'Save success', 'Draft saved successfully.', 'success'))
            .fail($osf.growl.bind(null, 'Problem saving draft', 'Sorry, we couldn\'t save this draft right now. ' + osfLanguage.REFRESH_OR_SUPPORT, 'danger'));
    });

    $('.prereg-draft-approve').click(function(e) {
        e.preventDefault();

        var $form = $(this).closest('form');
        $osf.dialog(
            'Please confirm',
            'Are you sure you want to approve this draft? This action is irreversible.',
            'Approve',
            {
                actionButtonClass: 'btn-warning'
            }
        ).done(function() {
            $form.submit();
        });
    });

    $('.prereg-draft-reject').click(function(e) {
        e.preventDefault();

        var $form = $(this).closest('form');
        $osf.dialog(
            'Please confirm',
            'Are you sure you want to reject this draft? This action is irreversible.',
            'Reject',
            {
                actionButtonClass: 'btn-danger'
            }
        ).done(function() {
            $form.submit();
        });
    });
});
