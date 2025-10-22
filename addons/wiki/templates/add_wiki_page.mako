<!-- New Component Modal -->
<div class="modal fade" id="newWiki">
    <div class="modal-dialog">
        <div class="modal-content">
            <form class="form">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h3 class="modal-title">${_("Add new wiki page")}</h3>
                </div><!-- end modal-header -->
                <div class="modal-body">
                    <div class='form-group wiki-radio-group'>
                        <div class="wiki-radio-item">
                            <label>
                                <input type="radio" name="addHierarchy" value="same" checked>
                                ${_("Add to same hierarchy")}
                            </label>
                        </div>
                        <div class="wiki-radio-item">
                            <label>
                                <input type="radio" name="addHierarchy" value="false">
                                <input id="parent-wiki-name-when-add-child" type="hidden" value="${wiki_name}">
                                ${_("Add to child hierarchy")}
                            </label>
                        </div>
                    </div>
                    <div class='form-group'>
                        <input id="data" placeholder="${_('New Wiki Name')}" type="text" class='form-control'>
                        <input id="parent-wiki-name" type="hidden" value="${parent_wiki_name}">
                    </div>
                    <p id="alert" class="text-danger"> </p>
                </div><!-- end modal-body -->
                <div class="modal-footer">
                    <a id="close" href="#" class="btn btn-default" data-dismiss="modal">${_("Cancel")}</a>
                    <button id="add-wiki-submit" type="submit" class="btn btn-success">${_("Add")}</button>
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
            var $parentWikiName = $newWikiForm.find('#parent-wiki-name');

            $submitForm
                .attr('disabled', 'disabled')
                .text('${_("Creating new wiki page")}');

            if ($.trim($data.val()) === '') {
                $alert.text('${_("The new wiki page name cannot be empty")}');
                $submitForm
                    .removeAttr('disabled', 'disabled')
                    .text('${_("Add")}');
            } else if ($data.val().length > 100) {
                $alert.text('${_("The new wiki page name cannot be more than 100 characters.")}');
                $submitForm
                    .removeAttr('disabled', 'disabled')
                    .text('${_("Add")}');

            } else if ($data.val().indexOf('/') != -1) {
                $alert.text('${_("The new wiki page name cannot contain forward slashes.")}');
                $submitForm
                    .removeAttr('disabled', 'disabled')
                    .text('${_("Add")}');
            } else {
                // TODO: helper to eliminate slashes in the url.
                var wikiName = $data.val();
                var validateUrl = "";
                var addHierarchy = $newWikiForm.find('input:radio[name="addHierarchy"]:checked').val();
                if (addHierarchy === "same"){
                    var parent_wiki_name = $newWikiForm.find('#parent-wiki-name').val();
                    if (parent_wiki_name){
                        validateUrl = ${ urls['api']['base'] | sjson, n } + encodeURIComponent(wikiName) + '/parent/' + encodeURIComponent(parent_wiki_name) + '/validate/';
                    } else {
                        validateUrl = ${ urls['api']['base'] | sjson, n } + encodeURIComponent(wikiName) + '/validate/';
                    }
                } else {
                    var parent_wiki_name = $newWikiForm.find('#parent-wiki-name-when-add-child').val();
                    validateUrl = ${ urls['api']['base'] | sjson, n } + encodeURIComponent(wikiName) + '/parent/' + encodeURIComponent(parent_wiki_name) + '/validate/';
                }
                var request = $.ajax({
                    type: 'GET',
                    cache: false,
                    url: validateUrl,
                    dataType: 'json'
                });
                request.done(function (response) {
                    window.location.href = ${ urls['web']['base'] | sjson, n } + encodeURIComponent(wikiName) + '/?view=preview&menu';
                });
                request.fail(function (response, textStatus, error) {
                    if (response.status === 409) {
                        $alert.text('${_("A wiki page with that name already exists.")}');
                    }
                    else if (response.status === 404){
                        $alert.text('${_("The parent wiki page does not exist.")}');
                    }
                    else if (response.status === 403){
                        $alert.text('${_("You do not have permission to perform this action.")}');
                        Raven.captureMessage('${_("Unauthorized user can view wiki add button")}', {
                            extra: {
                                url: ${ urls['api']['base'] | sjson, n } + encodeURIComponent(wikiName) + '/validate/',
                                textStatus: textStatus,
                                error: error
                            }
                        });
                    }
                    else {
                        $alert.text('${_("Could not validate wiki page. Please try again.")}'+response.status);
                        Raven.captureMessage('${_("Error occurred while validating page")}', {
                            extra: {
                                url: ${ urls['api']['base'] | sjson, n } + encodeURIComponent(wikiName) + '/validate/',
                                textStatus: textStatus,
                                error: error
                            }
                        });
                    }
                    $submitForm
                        .removeAttr('disabled', 'disabled')
                        .text('${_("Add")}');
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
