<div class="modal fade" id="addPrivateLink">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h3 data-bind="text:pageTitle"></h3>
            </div>

            <div class="modal-body">

                <div>
                    <div>
                        <div class="form-group">
                            <label for="privateLinkName">Link name</label>
                            <input data-bind="value:name"
                                id="privateLinkName"
                                type="text"
                                class="form-control private-link-name"
                                placeholder='Optional link name (e.g., For peer review, Sharing data, Share project)' />
                        </div>
                    </div>

                    <hr />

                    <div class="checkbox">
                        <label>
                            <input type="checkbox" data-bind="checked: anonymous"/>
                            <strong>Anonymize</strong> contributor list for this link (e.g., for blind peer review).
                            <br>
                            <i>Ensure the files and registration supplements you have created and uploaded do not contain identifying information.</i>
                        </label>
                    </div>

                    <hr />

                    <div style="margin-bottom:10px;">
                        Anyone with the private link can view&mdash;but not edit&mdash;the
                        components associated with the link.
                        <strong>Which components would you like to associate with this link?
                    </strong>                    </div>



                    <div class="row">

                        <div class="col-md-6" >
                            <div class="list-overflow">
                            <input type="checkbox" checked disabled />
                            <span data-bind="text:title"></span> (current component
                                <span data-bind="if: isPublic">, public</span>)
                            <div data-bind="foreach:nodes">
                                <div data-bind="style:{'marginLeft': margin}">
                                    <input type="checkbox" data-bind="checked:$parent.nodesToChange, value:id" />
                                    <span data-bind="text:$data.title"></span>
                                    <span data-bind="if: $data.is_public">(public)</span>
                                </div>
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
                <a class="btn btn-success" data-bind="click:submit, css:{disabled: disableSubmit}, text: submitText"></a>

            </div><!-- end modal-footer -->
        </div><!-- end modal-content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->
