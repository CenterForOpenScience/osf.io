<!-- New Component Modal -->
<div class="modal fade" id="newWiki">
    <div class="modal-dialog">
        <div class="modal-content">
            <form class="form">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h3 class="modal-title">Add new wiki page</h3>
                </div><!-- end modal-header -->
                <div class="modal-body">
                    <div class='form-group'>
                        <input id="data" placeholder="New Wiki Name" type="text" class='form-control'>
                    </div>
                    <p id="alert" class="text-danger"> </p>
                </div><!-- end modal-body -->
                <div class="modal-footer">
                    <a id="close" href="#" class="btn btn-default" data-dismiss="modal">Cancel</a>
                    <button id="add-wiki-submit" type="submit" class="btn btn-success">Add</button>
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
                .text('Creating new wiki page');

            if ($.trim($data.val()) === '') {
                $alert.text('The new wiki page name cannot be empty');
                $submitForm
                    .removeAttr('disabled', 'disabled')
                    .text('Add');
            } else if ($data.val().length > 100) {
                $alert.text('The new wiki page name cannot be more than 100 characters.');
                $submitForm
                    .removeAttr('disabled', 'disabled')
                    .text('Add');

            } else if ($data.val().indexOf('/') != -1) {
                $alert.text('The new wiki page name cannot contain forward slashes.');
                $submitForm
                    .removeAttr('disabled', 'disabled')
                    .text('Add');
            } else {
                // TODO: helper to eliminate slashes in the url.
                var wikiName = $data.val();
                var request = $.ajax({
                    type: 'GET',
                    cache: false,
                    url: ${ urls['api']['base'] | sjson, n } + encodeURIComponent(wikiName) + '/validate/',
                    dataType: 'json'
                });
                request.done(function (response) {
                    window.location.href = ${ urls['web']['base'] | sjson, n } + encodeURIComponent(wikiName) + '/edit/';
                });
                request.fail(function (response, textStatus, error) {
                    if (response.status === 409) {
                        $alert.text('A wiki page with that name already exists.');
                    }
                    else if (response.status === 403){
                        $alert.text('You do not have permission to perform this action.');
                        Raven.captureMessage('Unauthorized user can view wiki add button', {
                            url: ${ urls['api']['base'] | sjson, n } + encodeURIComponent(wikiName) + '/validate/',
                            textStatus: textStatus,
                            error: error
                        });
                    }
                    else {
                        $alert.text('Could not validate wiki page. Please try again.'+response.status);
                        Raven.captureMessage('Error occurred while validating page', {
                            url: ${ urls['api']['base'] | sjson, n } + encodeURIComponent(wikiName) + '/validate/',
                            textStatus: textStatus,
                            error: error
                        });
                    }
                    $submitForm
                        .removeAttr('disabled', 'disabled')
                        .text('Add');
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
