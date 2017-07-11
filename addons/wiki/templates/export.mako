<!-- Export Wiki Page Modal -->
<div class="modal fade" id="exportWiki">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                <h3 class="modal-title">Export wiki page</h3>
            </div><!-- end modal-header -->
            <div class="modal-body">
                <div style="padding-bottom:10px">Please select your PDF export option.
                    <div class="radio">
                        <label>
                            <input type="radio" id="exportCurrent" name="exportLevel" value="current" checked>
                            Current Page
                        </label>
                    </div>
                    <div class="radio">
                        <label>
                            <input type="radio" id="exportProject" name="exportLevel" value="project">
                            Project Pages
                        </label>
                    </div>
                </div>
            </div><!-- end modal-body -->
            <div class="modal-footer">
                % if wiki_content:
                    <a id="export-wiki" class="btn btn-success" data-dismiss="modal" style="margin-left: 200px;">Export</a>
                % else:
                    <a disabled id="export-wiki" class="btn btn-success" data-dismiss="modal" style="margin-left: 200px;">Export</a>
                % endif
                <a id="close" href="#" class="btn btn-default" data-dismiss="modal">Cancel</a>
            </div><!-- end modal-footer -->
        </div><!-- end modal- content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

<script type="text/javascript">

    $(document).ready(function() {
        var $WikiForm = $('#pageName');

        $('#export-wiki').on('click', function () {
            if (document.getElementById('exportCurrent').checked)
                window.open(${ urls['api']['base'] | sjson, n } + encodeURIComponent($WikiForm.text()) + '/pdf/');
            else if (document.getElementById('exportProject').checked)
                window.open(${ urls['api']['base'] | sjson, n } + 'pdf/');
        });
    });
</script>