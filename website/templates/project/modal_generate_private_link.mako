<div class="modal fade" id="private-link">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h3 data-bind="text:pageTitle"></h3>
            </div>

            <div class="modal-body">

                <div >

                    <div>
                        Would you like to add a label for this private link?
                        <div class="form-group">
                            <input type="text" class="form-control private-link-label" placeholder="New Label" data-bind="value:label"/>
                        </div>
                    </div>

                    <hr />

                    <div style="margin-bottom:10px;">
                        Would you like to apply the link privilege to any children of
                        the current component?
                    </div>

                    <div class="row">

                        <div class="col-md-6">
                            <input type="checkbox" checked disabled />
                            <span data-bind="text:title"></span> (current component)
                            <div data-bind="foreach:nodes">
                                <div data-bind="style:{'margin-left':margin}">
                                    <input type="checkbox" data-bind="checked:$parent.nodesToChange, value:id" />
                                    <span data-bind="text:title"></span>
                                </div>
                            </div>
                        </div>

                        <div class="col-md-6">
                            <div>
                                <a data-bind="click:selectNodes, css:{disabled:cantSelectNodes()}">Select all</a>
                            </div>
                            <div>
                                <a data-bind="click:deselectNodes, css:{disabled:cantDeselectNodes()}">De-select all</a>
                            </div>
                        </div>

                    </div>

                </div>

            </div><!-- end modal-body -->

            <div class="modal-footer">

                <a href="#" class="btn btn-default" data-dismiss="modal">Cancel</a>
                <a class="btn btn-success" data-bind="click:submit">Submit</a>

            </div><!-- end modal-footer -->
        </div><!-- end modal-content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->