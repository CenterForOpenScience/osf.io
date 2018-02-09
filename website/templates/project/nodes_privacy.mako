<div id="nodesPrivacy" class="modal fade">
    <div class="modal-dialog modal-md">
        <div style="display: none;" data-bind="visible: true">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" data-bind="click: clear" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                    <h3 class="modal-title" data-bind="text:pageTitle"></h3>
                </div>

                <div class="modal-body">
                    <!-- warning page -->
                    <div data-bind="if: page() == WARNING">
                      <span data-bind="html:message"></span>
                    </div>
                    <!-- end warning page -->

                    <!-- select projects page -->
                    <div data-bind="visible:page() === SELECT">
                        <div class="row">
                            <div class="col-md-10">
                                <div class="m-b-md box p-sm">
                                    <span data-bind="html:message"></span>
                                </div>
                            </div>
                        </div>
                        <div>
                            Select:&nbsp;
                            <a class="text-bigger" data-bind="click:selectAll">Make all public</a>
                            &nbsp;|&nbsp;
                            <a class="text-bigger" data-bind="click:selectNone">Make all private</a>
                        </div>
                        <div class="tb-row-titles">
                            <div style="width: 100%" data-tb-th-col="0" class="tb-th">
                                <span class="m-r-sm"></span>
                            </div>
                        </div>
                        <div class="osf-treebeard">
                            <div id="nodesPrivacyTreebeard">
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
                        <div data-bind="if: nodesChangedPublic().length + nodesChangedPrivate().length <= 100">

                            <div data-bind="if: nodesChanged()">
                                <div data-bind="visible: nodesChangedPublic().length > 0">
                                    <div class="panel panel-default">
                                        <div class="panel-heading clearfix">
                                            <h3 class="panel-title" data-bind="html:message()['nodesPublic']"></h3>
                                        </div>
                                        <div class="panel-body">
                                            <ul data-bind="foreach: { data: nodesChangedPublic, as: 'item' }">
                                                <li>
                                                    <h4 class="f-w-lg" data-bind="text: item"></h4>
                                                </li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                                <div data-bind="visible: nodesChangedPrivate().length > 0">
                                    <div class="panel panel-default">
                                        <div class="panel-heading clearfix">
                                            <h3 class="panel-title" data-bind="html:message()['nodesPrivate']"></h3>
                                        </div>
                                        <div class="panel-body">
                                            <ul data-bind="foreach: { data: nodesChangedPrivate, as: 'item' }">
                                                <li>
                                                    <h4 class="f-w-lg" data-bind="text: item"></h4>
                                                </li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div data-bind="ifnot: nodesChanged()">
                            <span data-bind="html:message()['nodesNotChangedWarning']"></span>
                        </div>
                        <div data-bind="if: nodesChangedPublic().length + nodesChangedPrivate().length > 100">
                            <span data-bind="html:message()['tooManyNodesWarning']"></span>
                        </div>
                    </div><!-- end projects changed warning page -->
                </div><!-- end modal-body -->

                <div class="modal-footer">
                    <!--ordering puts back button before cancel -->
                <span data-bind="if: page() == CONFIRM">
                    <a href="#" class="btn btn-default" data-bind="click: back" data-dismiss="modal">Back</a>
                </span>

                    <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">Cancel</a>

                    <span data-bind="if: page() == WARNING">
                      <span data-bind="if: parentIsEmbargoed">
                        <a class="btn btn-primary" data-bind="click: makeEmbargoPublic">Confirm</a>
                      </span>
                      <span data-bind="ifnot: parentIsEmbargoed">
                        <a class="btn btn-primary" data-bind="visible: hasChildren(), click:selectProjects">Continue</a>
                        <a class="btn btn-primary" data-bind="visible: !hasChildren(), click:confirmChanges">Confirm</a>
                      </span>
                    </span>

                    <span data-bind="if: page() == SELECT">
                      <a class="btn btn-primary" data-bind="click:confirmWarning">Continue</a>
                    </span>

                    <span data-bind="if: page() == CONFIRM && (nodesChangedPublic().length + nodesChangedPrivate().length <= 100)">
                      <a href="#" class="btn btn-primary" data-bind="click: confirmChanges, visible: nodesChanged()" data-dismiss="modal">Confirm</a>
                    </span>
                </div><!-- end modal-footer -->
            </div><!-- end modal-content -->
        </div>
    </div><!-- end modal-dialog -->
</div><!-- end modal -->
