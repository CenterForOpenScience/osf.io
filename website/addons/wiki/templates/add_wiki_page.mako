<%page expression_filter="h"/>

<!-- New Component Modal -->
<div class="modal fade" id="newWiki">
    <div class="modal-dialog">
        <div class="modal-content">
            <form class="form">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h3 class="modal-title">Add New Wiki Page</h3>
                </div><!-- end modal-header -->
                <div class="modal-body">
                    <div id="alert" style="padding-bottom:10px;color:blue;"></div>
                    <div class='form-group'>
                        <input id="data" placeholder="New Wiki Name" type="text" class='form-control'>
                    </div>
                </div><!-- end modal-body -->
                <div class="modal-footer">
                    <a id="close" href="#" class="btn btn-default" data-dismiss="modal">Close</a>
                    <button id="add-wiki-submit" type="submit" class="btn btn-primary">OK</button>
                </div><!-- end modal-footer -->
            </form>
        </div><!-- end modal- content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

<script type="text/javascript">
    $(function () {
        var $newWikiForm = $('#newWiki form');

        $newWikiForm.on('submit', function (e) {
            e.preventDefault();

            var $data = $newWikiForm.find('#data');
            var $submitForm = $newWikiForm.find('#add-wiki-submit');
            var $alert = $newWikiForm.find('#alert');

            $submitForm
                .attr('disabled', 'disabled')
                .text('Creating New Wiki page');

            if ($.trim($data.val()) === '') {
                $alert.text('The new wiki page name cannot be empty');
                $submitForm
                    .removeAttr('disabled', 'disabled')
                    .text('OK');
            } else if ($data.val().length > 100) {
                $alert.text('The new wiki page name cannot be more than 100 characters.');
                $submitForm
                    .removeAttr('disabled', 'disabled')
                    .text('OK');
            } else {
                // TODO: helper to eliminate slashes in the url.
                var wikiName = $data.val().split('/').join(' ');
                var request = $.ajax({
                    type: 'GET',
                    cache: false,
                    url: '${urls['api']['base']}' + encodeURIComponent(wikiName) + '/validate/',
                    dataType: 'json'
                });
                request.done(function (response) {
                    window.location.href = '${urls['web']['base']}' + encodeURIComponent(wikiName) + '/edit/';
                });
                request.fail(function (response, textStatus, error) {
                    if (response.status === 409) {
                        $alert.text('A wiki page with that name already exists.');
                    } else {
                        $alert.text('Could not validate wiki page. Please try again.');
                        Raven.captureMessage('Error occurred while validating page', {
                            url: '${urls['api']['base']}' + encodeURIComponent(wikiName) + '/validate/',
                            textStatus: textStatus,
                            error: error
                        });
                    }
                    $submitForm
                        .removeAttr('disabled', 'disabled')
                        .text('OK');
                });
            }
        });

        $newWikiForm.find('#close').on('click', function () {
            var $data = $newWikiForm.find('#data');
            var $alert = $newWikiForm.find('#alert');

            $alert.text('');
            $data.val('');
        });
    });
</script>
