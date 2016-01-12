<link rel="stylesheet" href='/static/css/pages/remove-contributor-page.css'>
<div id="removeContributor" class="modal fade">
    <div data-bind="css: modalSize">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                <h3 class="modal-title" data-bind="text:pageTitle"></h3>
            </div>
            <div class="modal-body" >

                <div data-bind="if: canRemoveNode() && !pageChanged()">
                    <!-- remove page -->
                    <div data-bind='if:page() === REMOVE'>
                        <div class="form-group">
                            <span data-bind="visible:removeSelf()">Do you want to remove yourself from <b>{{title}}</b>, or from <b>{{title}}</b> and every component in it.</span>
                            <span data-bind="visible:!removeSelf()">Do you want to remove <b>{{contributorToRemove()["fullname"]}}</b> from <b>{{title}}</b>, or from <b>{{title}}</b> and every component in it.</span>
                        </div>
                        <div data-bind="visible:removeSelf()" id="remove-page-radio-buttons" class="col-md-8" align="left">
                            <div class="radio">
                                <label><input type="radio" name="radioBoxGroup" data-bind="checked:deleteAll, checkedValue: false" checked>
                                    Remove yourself from  <span class="f-w-lg" data-bind="text: title"></span></label>
                            </div>

                            <div class="radio">
                                <label><input  type="radio" name="radioBoxGroup" data-bind="checked: deleteAll, checkedValue: true" >
                                    Remove yourself from <span class="f-w-lg" data-bind="text: title"></span> and every component in it.</label>
                            </div>
                        </div>

                        <div data-bind="visible:!removeSelf()" id="remove-page-radio-buttons" class="col-md-8" align="left">
                            <div class="radio">
                                <label><input type="radio" name="radioBoxGroup" data-bind="checked:deleteAll, checkedValue: false" checked>
                                    Remove <span class="f-w-lg" >{{contributorToRemove()["fullname"]}}</span> from  <span class="f-w-lg" data-bind="text: title"></span></label>
                            </div>

                            <div class="radio">
                                <label><input  type="radio" name="radioBoxGroup" data-bind="checked: deleteAll, checkedValue: true" >
                                    Remove <span class="f-w-lg" >{{contributorToRemove()["fullname"]}}</span> from <span class="f-w-lg" data-bind="text: title"></span> and every component in it.</label>
                            </div>
                        </div>

                    </div><!-- end remove page -->
                    <!-- removeNoChildren page -->
                    <div data-bind='if:page() === REMOVE_NO_CHILDREN'>
                        <div class="form-group" data-bind="if:contributorToRemove">
                            <span data-bind="visible:removeSelf()">Remove yourself from {{title}}?</span>
                            <span data-bind="visible:!removeSelf()">Remove <b>{{contributorToRemove()["fullname"]}}</b> from {{title}}?</span>
                        </div>

                    </div><!-- end removeNoChildren page -->

                    <!-- removeAll page -->
                    <div data-bind='if:page() === REMOVE_ALL'>
                        <div data-bind="visible:titlesToRemove().length">
                            <div class="panel panel-default">
                                <div class="panel-body">
                                    <div class="form-group" data-bind="if:contributorToRemove">
                                        <span data-bind="visible:removeSelf()">You removed from the following projects and/or components.</span>
                                        <span data-bind="visible:!removeSelf()"><b>{{contributorToRemove()["fullname"]}} will be</b> removed from the following projects and/or components.</span>
                                    </div>
                                    <div class="col-md-8" align="left">
                                        <ul data-bind="foreach: { data: titlesToRemove(), as: 'item' }">
                                            <li>
                                                <h4 class="f-w-lg" data-bind="text: item"></h4>
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div data-bind="visible:titlesToKeep().length">
                            <div class="panel panel-default">
                                <div class="panel-body">
                                    <div class="form-group" data-bind="if:contributorToRemove">
                                        <span data-bind="visible:removeSelf()"><b>You cannot</b> be removed from the following projects and/or components.</span>
                                        <span data-bind="visible:!removeSelf()"><b>{{contributorToRemove()["fullname"]}} cannot</b> be removed from the following projects and/or components.</span>
                                    </div>
                                    <div class="col-md-8" align="left">
                                        <ul data-bind="foreach: { data: titlesToKeep(), as: 'item' }">
                                            <li>
                                                <h4 class="f-w-lg" data-bind="text: item"></h4>
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div><!-- end removeAll page -->
                </div>
                <div data-bind="if: !canRemoveNode() && !pageChanged()">
                    <span><b>{{contributorToRemove()["fullname"]}}</b> cannot be removed as a contributor.  You need at least one administrator, bibliographic contributor, and one registered user.</span>
                </div>
                <div data-bind="if: pageChanged()">
                    <span>Please save or discard your existing changes before removing a contributor.</span>
                </div>
            </div>
            <!-- end modal-body -->

            <div class="modal-footer">
                <div data-bind="if:canRemoveNode() && !pageChanged()" align="right">
                        <span data-bind="if: page() === REMOVE">
                                <div class="row">
                                    <div  class="col-md-4 remove-page-buttons">
                                        <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">Cancel</a>
                                        <a class="btn btn-danger" data-bind="click:submit, visible: !deleteAll()">Remove</a>
                                        <a class="btn btn-default" data-bind="click:deleteAllNodes, visible: deleteAll">Continue</a>
                                    </div>
                                </div>
                        </span>
                        <span data-bind="if: page() === REMOVE_NO_CHILDREN">
                            <div>
                                <div class="row">
                                    <div  class="col-md-12 remove-page-buttons" align="right">
                                        <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">Cancel</a>
                                        <a class="btn btn-danger" data-bind="click:submit">Remove</a>
                                    </div>
                                </div>
                            </div>
                        </span>
                        <span data-bind="if: page() === REMOVE_ALL" align="right">
                                <div class="row">
                                    <div class="col-md-12 remove-page-buttons">
                                        <a href="#" class="btn btn-default" data-bind="click: back" data-dismiss="modal">Back</a>
                                        <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">Cancel</a>
                                        <a class="btn btn-danger" data-bind="click:submit">Remove</a>
                                    </div>
                                </div>
                        </span>
                </div>
                <div data-bind="if:!canRemoveNode() || pageChanged()">
                    <div class="row">
                        <div  class="col-md-12 remove-page-buttons" align="right">
                            <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">Cancel</a>
                        </div>
                    </div>
                </div>
            </div><!-- end modal-footer -->
        </div><!-- end modal-content -->
    </div><!-- end modal-size -->
</div><!-- end modal -->

