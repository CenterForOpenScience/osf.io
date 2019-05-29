<div id="nodesDelete" class="modal fade">
    <div class="modal-dialog modal-md">
        <div style="display: none;" data-bind="visible: true">
            <!-- ko with: modal -->
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" data-bind="click: clear" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                    <h3 class="modal-title" data-bind="text:pageTitle"></h3>
                </div>
                <div class="modal-body">
                    <!-- select projects page -->
                    <div data-bind="if: page() === SELECT">
                        <div class="row">
                            <div class="col-md-10">
                                <div class="m-b-md box p-sm">
                                    <span data-bind="html:message"></span>
                                </div>
                            </div>
                        </div>
                        <div>
                            Select:&nbsp;
                            <a class="text-bigger" data-bind="click:selectAll">All components</a>
                            <span class="pull-right"><b><sup>*</sup></b><small>contains supplemental materials for a preprint</small></span>
                        </div>
                        <div class="tb-row-titles">
                            <div style="width: 100%" data-tb-th-col="0" class="tb-th">
                                <span class="m-r-sm"></span>
                            </div>
                        </div>
                        <div class="osf-treebeard">
                            <div id="nodesDeleteTreebeard">
                                <div class="spinner-loading-wrapper">
                                    <div class="ball-scale ball-scale-blue">
                                        <div></div>
                                    </div>
                                    <p class="m-t-sm fg-load-message"> Loading projects and components...  </p>
                                </div>
                            </div>
                            <div class="help-block" style="padding-left: 15px">
                                <p id="configureNotificationsMessage"></p>
                            </div>
                        </div>
                    </div>
                    <!-- end select projects page -->

                    <!-- projects changed warning page -->
                    <div data-bind="if: page() === CONFIRM">
                        <div data-bind="if: nodesChanged().length <= 100">
                            <div data-bind="if: nodesDeleted()">
                                <div data-bind="visible: nodesChanged().length > 0">
                                    <div class="panel panel-default">
                                        <div class="panel-heading clearfix">
                                            <h3 class="panel-title" data-bind="html:message"></h3>
                                        </div>
                                        <div class="panel-body">
                                            <ul data-bind="foreach: { data: nodesChanged, as: 'item' }">
                                                <li>
                                                    <h4 class="f-w-lg" data-bind="text: item"></h4>
                                                </li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                                <p data-bind="html:warning">
                                <p data-bind="css: {'text-danger' : (!canDelete() && atMaxLength())}">
                                    Type the following to continue: <strong data-bind="text: confirmationString"></strong>
                                </p>
                                <div contenteditable="true" data-bind="editableHTML: {observable: confirmInput, onUpdate: handleEditableUpdate}" class="form-control"></div>
                            </div>
                        </div>
                    </div><!-- end projects changed warning page -->

                    <div data-bind="if: page() === QUICKDELETE">
                        <div>
                            <p data-bind="html: message"></p>
                            <p data-bind="css: {'text-danger' : (!canDelete() && atMaxLength())}">
                                Type the following to continue: <strong data-bind="text: confirmationString"></strong>
                            </p>
                        </div>
                        <div contenteditable="true" data-bind="editableHTML: {observable: confirmInput, onUpdate: handleEditableUpdate}" class="form-control"></div>
                    </div><!-- end projects changed warning page -->
                </div><!-- end modal-body -->

                <div class="modal-footer">
                    <!--ordering puts back button before cancel -->
                    <span data-bind="if: page() == CONFIRM">
                        <a href="#" class="btn btn-default" data-bind="click: back" data-dismiss="modal">Back</a>
                    </span>
                    <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">Cancel</a>
                    <span data-bind="if: (page() === QUICKDELETE || (page() == CONFIRM && (nodesChanged().length <= 100)))">
                        <a href="#" class="btn btn-danger" data-bind="css: { disabled: !canDelete() }, click: confirmChanges, visible: nodesDeleted()" data-dismiss="modal">Delete</a>
                    </span>
                    <span data-bind="if: page() == SELECT">
                        <a class="btn btn-primary" data-bind="css: { disabled: !nodesDeleted() }, click:confirmWarning" >Continue</a>
                    </span>
                </div><!-- end modal-footer -->
            </div><!-- end modal-content -->
            <!-- /ko -->
        </div>

    </div><!-- end modal-dialog -->
</div><!-- end modal -->
