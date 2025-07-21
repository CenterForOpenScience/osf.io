<!-- Delete Wiki Page Modal -->
<div class="modal fade" id="deleteWiki">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                <h3 class="modal-title">${_("Delete wiki page")}</h3>
            </div><!-- end modal-header -->
            <div class="modal-body">
                <div id="alert" style="padding-bottom:10px">${_("This wiki page and all content under it will be deleted. This action is irreversible.")}</div>
            </div><!-- end modal-body -->
            <div class="modal-footer">
                <a id="close" href="#" class="btn btn-default" data-dismiss="modal">${_("Cancel")}</a>
                <a id="delete-wiki" class="btn btn-danger">${_("Delete")}</a>
            </div><!-- end modal-footer -->
        </div><!-- end modal- content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

<script type="text/javascript">
    $(document).ready(function() {
        $('#delete-wiki').on('click', function () {

            window.contextVars.wiki.triggeredDelete = true;
            $.ajax({
                type:'DELETE',
                url: ${ urls['api']['delete'] | sjson, n },
                success: function(response) {
                    window.location.href = ${ urls['web']['home'] | sjson, n };
                }
            })
        });
    });
</script>
