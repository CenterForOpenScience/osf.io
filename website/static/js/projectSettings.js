(function () {


window.ProjectSettings = {};

/**
*  returns a random name from this list to use as a confirmation string
*/
function randomScientist() {
    var scientists = [
    'Anning',
    'Banneker',
    'Cannon',
    'Carver',
    'Chappelle',
    'Curie',
    'Divine',
    'Emeagwali',
    'Fahlberg',
    'Forssmann',
    'Franklin',
    'Herschel',
    'Hodgkin',
    'Hopper',
    'Horowitz',
    'Jemison',
    'Julian',
    'Kovalevsky',
    'Lamarr',
    'Lavoisier',
    'Lovelace',
    'Massie',
    'McClintock',
    'Meitner',
    'Mitchell',
    'Morgan',
    'Nosek',
    'Odum',
    'Pasteur',
    'Pauling',
    'Payne',
    'Pearce',
    'Pollack',
    'Rillieux',
    'Sanger',
    'Somerville',
    'Tesla',
    'Tyson',
    'Turing'
    ];

    return scientists[Math.floor(Math.random() * scientists.length)];
}


// Request the first 5 contributors, for display in the deletion modal
var contribs = [];
var moreContribs = 0;

var contribURL = nodeApiUrl + 'get_contributors/?limit=5';
var request = $.ajax({
    url: contribURL,
    type: 'get',
    dataType: 'json'
});
request.done(function(response) {
    var currentUserName = window.contextVars.currentUser.fullname;
    contribs = response.contributors.filter(function(contrib) { 
        return contrib.shortname !== currentUserName;
    });
    moreContribs = response.more;
});
request.fail(function(xhr, textStatus, err) {
    Raven.captureMessage('Error requesting contributors', {
        url: contribURL, textStatus: textStatus, err: err,
    });
});


/**
    * Pulls a random name from the scientist list to use as confirmation string
*  Ignores case and whitespace
*/
ProjectSettings.getConfirmationCode = function(nodeType) {
    var key = randomScientist();
    function successHandler(response) {
        // Redirect to either the parent project or the dashboard
        window.location.href = response.url;
    }

    var promptMsg = 'Are you sure you want to delete this ' + nodeType + '?' +
        '<div class="bootbox-node-deletion-modal"><p>It will no longer be available to other contributors on the project.';

    // It's possible that the XHR request for contributors has not finished before getting to this
    // point; only construct the HTML for the list of contributors if the contribs list is populated
    var contribsMsg = '';
    if (contribs.length) {
        // Build contributor unordered list
        var contriblist = '';
        $.each(contribs, function(i, b){
            contriblist += '<li>' + b.fullname + '</li>';
        });
        contribsMsg = ' Contributors include:</p>' +
            '<ol>' + contriblist +'</ol>' +
            '<p style="font-weight: normal; font-size: medium; line-height: normal;">' +
            ((moreContribs > 0) ? 'and <strong>' + moreContribs + '</strong> others.</p>' : '');
    }

    var promptMsgEnd = '<p style="font-weight: normal; font-size: medium; line-height: normal;">' +
        'If you want to continue, type <strong>' + key + '</strong> and click OK.</p></div>';

    var fullMsg = [promptMsg, contribsMsg, promptMsgEnd].join('');
    bootbox.prompt(
        fullMsg,
        function(result) {
            if (result != null) {
                result = result.toLowerCase();
            }
            if ($.trim(result) === key.toLowerCase()) {
                var request = $.ajax({
                    type: 'DELETE',
                    dataType: 'json',
                    url: nodeApiUrl
                });
                request.done(successHandler);
                request.fail($.osf.handleJSONError);
            } else if (result != null) {
                $.osf.growl('Incorrect confirmation',
                    'The confirmation string you provided was incorrect. Please try again.');
            }
        }
    );
};

$(document).ready(function() {

    // TODO: Knockout-ify me
    $('#commentSettings').on('submit', function() {
        var $commentMsg = $('#configureCommentingMessage');

        var $this = $(this);
        var commentLevel = $this.find('input[name="commentLevel"]:checked').val();

        $.osf.postJSON(
            nodeApiUrl + 'settings/comments/',
            {commentLevel: commentLevel}
        ).done(function() {
            $commentMsg.addClass('text-success');
            $commentMsg.text('Successfully updated settings.');
            window.location.reload();
        }).fail(function() {
            $.osf.growl('Could not set commenting configuration.', 'Please try again.');
        });

        return false;

    });


    // Set up submission for addon selection form
    $('#selectAddonsForm').on('submit', function() {

        var formData = {};
        $('#selectAddonsForm').find('input').each(function(idx, elm) {
            var $elm = $(elm);
            formData[$elm.attr('name')] = $elm.is(':checked');
        });
        var msgElm = $(this).find('.addon-settings-message');
        $.ajax({
            url: nodeApiUrl + 'settings/addons/',
            data: JSON.stringify(formData),
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json',
            success: function() {
                msgElm.text('Settings updated').fadeIn();
                window.location.reload();
            }
        });

        return false;

    });



    // Show capabilities modal on selecting an addon; unselect if user
    // rejects terms
    $('.addon-select').on('change', function() {
        var that = this,
            $that = $(that);
        if ($that.is(':checked')) {
            var name = $that.attr('name');
            var capabilities = $('#capabilities-' + name).html();
            if (capabilities) {
                bootbox.confirm(
                    capabilities,
                    function(result) {
                        if (!result) {
                            $(that).attr('checked', false);
                        }
                    }
                );
            }
        }
    });


});

}());
