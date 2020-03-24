<link rel="stylesheet" href='/static/css/pages/remove-contributor-page.css'>
<div id="removeContributor" class="modal fade">
    <div data-bind="css: modalSize">
        <div class="modal-content scripted">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                <h3 class="modal-title" data-bind="text:pageTitle"></h3>
            </div>
            <div class="modal-body" >

                <div data-bind="if: canRemoveNode() && !pageChanged()">
                    <!-- remove page -->
                    <div data-bind='if:page() === REMOVE'>
                        <div class="form-group">
                            ${_('<span>Do you want to remove <b %(removedContributor)s></b> from\
                                <b %(textTitle)s></b>, or from <b %(textTitle)s></b> and every component in it?</span>') % dict(removedContributor='data-bind="text:removeSelf() ? \'yourself\' : contributorToRemove()[\'fullname\']"',textTitle='data-bind="text: title"') | n}
                        </div>
                        <div id="remove-page-radio-buttons" class="col-md-8" align="left">
                            <div class="radio">
                                <label><input type="radio" name="radioBoxGroup" data-bind="checked:deleteAll, checkedValue: false" checked>
                                    ${_('Remove <b %(removedContributor)s></b> from\
                                    <span %(textTitle)s></span>.') % dict(removedContributor='data-bind="text:removeSelf() ? \'yourself\' : contributorToRemove()[\'fullname\']"',textTitle='class="f-w-lg" data-bind="text: title"') | n}
                                </label>
                            </div>

                            <div class="radio">
                                <label><input  type="radio" name="radioBoxGroup" data-bind="checked: deleteAll, checkedValue: true" >
                                    ${_('Remove <b %(removedContributor)s></b> from\
                                    <span %(textTitle)s></span> and every component in it.') % dict(removedContributor='data-bind="text:removeSelf() ? \'yourself\' : contributorToRemove()[\'fullname\']"',textTitle='"f-w-lg" data-bind="text: title"') | n}</label>
                            </div>
                        </div>

                    </div><!-- end remove page -->
                    <!-- removeNoChildren page -->
                    <div data-bind='if:page() === REMOVE_NO_CHILDREN'>
                        <div class="form-group" data-bind="if:contributorToRemove">
                            <span>${_('Remove <b %(removedContributor)s></b> from <span %(textTitle)s></span>?') % dict(removedContributor='data-bind="text:removeSelf() ? \'yourself\' : contributorToRemove()[\'fullname\']"',textTitle='data-bind="text: title"') | n}</span>
                        </div>

                    </div><!-- end removeNoChildren page -->

                    <!-- removeAll page -->
                    <div data-bind='if:page() === REMOVE_ALL'>
                        <div data-bind="visible:titlesToRemove().length">
                            <div class="panel panel-default">
                                <div class="panel-body">
                                    <div class="form-group" data-bind="if:contributorToRemove">
                                        <span>${_('<b %(removedContributor)s>\
                                        </b> will be removed from the following projects and/or components.') % dict(removedContributor='data-bind="text:removeSelf() ? \'You\' : contributorToRemove()[\'fullname\']"') | n}</span>
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
                                        <span>${_('<b %(removedContributor)s>\
                                        </b> cannot be removed from the following projects and/or components.') % dict(removedContributor='data-bind="text:removeSelf() ? \'You\' : contributorToRemove()[\'fullname\']"') | n}</span>
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
                    <span>${_('<b %(removedContributor)s></b> cannot be\
                        removed as a contributor.  You need at least one administrator, bibliographic contributor, and registered user.') % dict(removedContributor=_('data-bind="text:removeSelf() ? \'You\' : contributorToRemove()[\'fullname\']"')) | n}</span>
                </div>
                <div data-bind="if: pageChanged()">
                    <span>${_("Please save or discard your existing changes before removing a contributor.")}</span>
                </div>
            </div>
            <!-- end modal-body -->

            <div class="modal-footer">
                <div data-bind="if:canRemoveNode() && !pageChanged()" align="right">
                    <span data-bind="if: page() === REMOVE">
                        <div class="row">
                            <div  class="remove-page-buttons">
                                <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">${_("Cancel")}</a>
                                <a class="btn btn-danger" data-bind="click:submit, visible: !deleteAll()">${_("Remove")}</a>
                                <a class="btn btn-default" data-bind="click:deleteAllNodes, visible: deleteAll">${_("Continue")}</a>
                            </div>
                        </div>
                    </span>
                    <span data-bind="if: page() === REMOVE_NO_CHILDREN">
                        <div class="row">
                            <div  class="remove-page-buttons" align="right">
                                <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">${_("Cancel")}</a>
                                <a class="btn btn-danger" data-bind="click:submit">${_("Remove")}</a>
                            </div>
                        </div>
                    </span>
                    <span data-bind="if: page() === REMOVE_ALL" align="right">
                        <div class="row">
                            <div class="remove-page-buttons">
                                <a href="#" class="btn btn-default" data-bind="click: back" data-dismiss="modal">${_("Back")}</a>
                                <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">${_("Cancel")}</a>
                                <a class="btn btn-danger" data-bind="click:submit">${_("Remove")}</a>
                            </div>
                        </div>
                    </span>
                </div>
                <div data-bind="if:!canRemoveNode() || pageChanged()">
                    <div class="row">
                        <div  class="remove-page-buttons" align="right">
                            <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">${_("Cancel")}</a>
                        </div>
                    </div>
                </div>
            </div><!-- end modal-footer -->
        </div><!-- end modal-content -->
    </div><!-- end modal-size -->
</div><!-- end modal -->

