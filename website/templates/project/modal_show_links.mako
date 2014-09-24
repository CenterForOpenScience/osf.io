<div class="modal fade" id="showLinks">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Links to this project</h3>
            </div>

            <div class="modal-body">
                <table class="table table-striped">
                    <thead>
                        <th>Title</th>
                        <th>Authors</th>
                    </thead>
                    <tbody data-bind="foreach: links">
                        <tr>
                            <td>
                                <!-- ko if: url -->
                                    <a data-bind="text: title, attr: {href: url}"></a>
                                <!-- /ko -->
                                <!-- ko ifnot: url -->
                                    <span data-bind="text: title"></span>
                                <!-- /ko -->
                            </td>
                            <td data-bind="text: authorShort"></td>
                        </tr>
                    </tbody>
                </table>
            </div><!-- end modal-body -->

            <div class="modal-footer">
                <a href="#" class="btn btn-default" data-dismiss="modal">Done</a>
            </div><!-- end modal-footer -->
        </div><!-- end modal-content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->
