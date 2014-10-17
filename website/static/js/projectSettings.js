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
    'Turing',
    ];

    return scientists[Math.floor(Math.random() * scientists.length)];
}

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
    bootbox.prompt(
        '<div>Delete this ' + nodeType + '? This is IRREVERSIBLE.</div>' +
        '<p style="font-weight: normal; font-size: medium; line-height: normal;">' +
        'If you want to continue, type <strong>' + key + '</strong> and click OK.</p>',
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
                bootbox.alert({
                    title: 'Incorrect confirmation',
                    message: 'The confirmation string you provided was incorrect. Please try again.'
                });
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
            bootbox.alert('Could not set commenting configuration. Please try again.');
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
