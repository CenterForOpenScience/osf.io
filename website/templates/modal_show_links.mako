<div class="modal fade" id="showLinks">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h3></h3>
            </div>

            <div class="modal-body">
                <table>
                    <tr data-bind="foreach: links">
                        <td data-bind="text: title"></td>
                        <td data-bind="text: authorShort"></td>
                    </tr>
                </table>
            </div><!-- end modal-body -->

            <div class="modal-footer">
                <a href="#" class="btn btn-default" data-dismiss="modal">Done</a>
            </div><!-- end modal-footer -->
        </div><!-- end modal-content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->
