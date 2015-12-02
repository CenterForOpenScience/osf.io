<link rel="stylesheet" href='/static/css/pages/remove-contributor-page.css'>
<div id="removeContributor" class="modal fade">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                <h3 class="modal-title" data-bind="text:pageTitle"></h3>
            </div>

            <div class="modal-body">
                {{ko.toJSON($data)}}
                <!-- remove page -->
                <div data-bind='if:page() === "remove"'>
                        <div class="form-group" data-bind="if:contributorToRemove">
                           <span>Do you want to remove {{contributorToRemove()["fullname"]}} from  <span class="f-w-lg" data-bind="text: title"></span>, or from <span class="f-w-lg" data-bind="text: title"></span> and every component in it.</span>
                        </div>
                        <div id="remove-page-radio-buttons" data-bind="if:contributorToRemove" class="col-md-8" align="left">
                            <div class="radio" data-bind="visible:nodeHasChildren">
                                <label><input type="radio" name="radioBoxGroup" data-bind="checked:deleteAll, checkedValue: false" checked>Remove  <span class="f-w-lg" >{{contributorToRemove()["fullname"]}}</span> from  <span class="f-w-lg" data-bind="text: title"></span></label>
                            </div>
                            <div class="radio" data-bind="visible:nodeHasChildren">
                                <label><input  type="radio" name="radioBoxGroup" data-bind="checked: deleteAll, checkedValue: true" >Remove <span class="f-w-lg" >{{contributorToRemove()["fullname"]}}</span> from <span class="f-w-lg" data-bind="text: title"></span> and every component in it.</label>
                            </div>
                        </div>

                </div><!-- end remove page -->

                <!-- remove page -->
                <div data-bind='if:page() === "removeAll"'>
                        <div class="form-group" data-bind="if:contributorToRemove">
                           <span><b>{{contributorToRemove()["fullname"]}}</b> will be removed from the following projects and/or components.</span>
                        </div>
                        <div class="col-md-8" align="left">
                            <ul data-bind="foreach: { data: titlesToRemove(), as: 'item' }">
                                <li>
                                    <h4 class="f-w-lg" data-bind="text: item"></h4>
                                </li>
                            </ul>
                        </div>

                </div><!-- end invite user page -->

            </div><!-- end modal-body -->

            <div class="modal-footer">
                    <span data-bind="if: page() === 'remove'">
                    <div>
                        <div class="row">
                            <div  class="col-md-4 remove-page-buttons">
                                <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">Cancel</a>
                                <a class="btn btn-danger" data-bind="click:submit, visible: !deleteAll()">Remove</a>
                                <a class="btn btn-default" data-bind="click:deleteAllNodes, visible: deleteAll">Continue</a>
                            </div>
                    </div>
                    </div>
                </span>
                    <span data-bind="if: page() === 'removeAll'">
                    <div>
                        <div class="row">
                           <div  class="col-md-4 remove-page-buttons" align="right">
                                <a href="#" class="btn btn-default" data-bind="click: back" data-dismiss="modal">Back</a>
                                <a href="#" class="btn btn-default" data-bind="click: clear" data-dismiss="modal">Cancel</a>
                                <a class="btn btn-danger" data-bind="click:submit">Remove</a>
                            </div>
                    </div>
                    </div>
                </span>
                </div>

            </div><!-- end modal-footer -->
        </div><!-- end modal-content -->
</div><!-- end modal -->

