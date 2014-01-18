<div class="modal fade" id="addPointer">

    <div class="modal-dialog">

        <div class="modal-content">

            <div class="modal-header">
                <h3 data-bind="text:title"></h3>
            </div>

            <div class="modal-body">

                <form>
                    <input style="margin-bottom: 8px;" data-bind="value:query" />
                    <div>
                        <div class="btn-group">
                            <button class="btn btn-default" data-bind="click:function(){search(true)}">Search all projects</button>
                            <button class="btn btn-default" data-bind="click:function(){search(false)}">Search my projects</button>
                        </div>
                    </div>
                </form>

                <hr />

                <!-- Choose which to add -->
                <div class="row">

                    <div class="col-md-6"col-md->
                        <div>
                            <span class="modal-subheader">Results</span>
                            <a data-bind="click:addAll">Add all</a>
                        </div>
                        <div class="error" data-bind="if:errorMsg, text:errorMsg"></div>
                        <table class="table table-striped">
                            <tbody data-bind="foreach:{data:results, afterRender:addTips}">
                                <tr data-bind="if:!($root.selected($data))">
                                    <td>
                                        <a
                                                class="btn btn-default contrib-button"
                                                data-bind="click:$root.add"
                                                rel="tooltip"
                                                title="Add pointer"
                                            >+</a>
                                    </td>
                                    <td data-bind="text:title"></td>
                                    <td data-bind="text:$root.authorText($data)"></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <div class="col-md-6">
                        <div>
                            <span class="modal-subheader">Adding</span>
                            <a data-bind="click:removeAll">Remove all</a>
                        </div>
                        <table class="table table-striped">
                            <tbody data-bind="foreach:{data:selection, afterRender:addTips}">
                                <tr>
                                    <td>
                                        <a
                                                class="btn btn-default contrib-button"
                                                data-bind="click:$root.remove"
                                                rel="tooltip"
                                                title="Remove pointer"
                                            >-</a>
                                    </td>
                                    <td data-bind="text:title"></td>
                                    <td data-bind="text:$root.authorText($data)"></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                </div>

            </div><!-- end modal-body -->

            <div class="modal-footer">

                <a class="btn btn-default" data-dismiss="modal">Cancel</a>

                <span data-bind="if:selection().length">
                    <a class="btn btn-success" data-bind="click:submit">Submit</a>
                </span>

            </div><!-- end modal-footer -->

        </div><!-- end modal-content -->

    </div><!-- end modal-dialog -->

</div><!-- end modal -->
