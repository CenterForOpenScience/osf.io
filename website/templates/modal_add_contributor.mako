<div class="modal fade" id="addContributors" role="dialog" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title">Add Contributors</h3>
            </div>
            <div class="modal-body">
                <!-- Search box -->
                <form class="form-inline">
                    <input data-bind="value:query" />
                    <button class="btn btn-default" data-bind="click:search">Search</button>
                </form>
                <div class="row">
                    <div class="col-md-6">
                        <h3>Search Results</h3>
                        <table>
                            <tbody data-bind="foreach:{data:results, afterRender:addTips}">
                                <tr class="search-contributor-result" data-bind="if:!($root.selected($data))">
                                    <td>
                                        <a
                                                class="btn btn-default contrib-button"
                                                data-bind="click:$root.add"
                                                rel="tooltip"
                                                title="Add contributor"
                                            >+</a>
                                    </td>
                                    <td>
                                        <img data-bind="attr:{src:$data.gravatar}" />
                                    </td>
                                    <td data-bind="text:user"></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <div class="col-md-6">
                        <h3>Contributors to Add</h3>
                        <table>
                            <tbody data-bind="foreach:{data:selection, afterRender:addTips}">
                                <tr class="search-contributor-result">
                                    <td>
                                        <a
                                                class="btn btn-default contrib-button"
                                                data-bind="click:$root.remove"
                                                rel="tooltip"
                                                title="Remove contributor"
                                            >-</a>
                                    </td>
                                    <td>
                                        <img data-bind="attr:{src:$data.gravatar}" />
                                    </td>
                                    <td data-bind="text:user"></td>
                                </tr>
                            </tbody>
                        </table>
                    </div><!-- end col-md -->
                </div>
            </div><!-- end modal-body -->
            <div class="modal-footer">
                <a href="#" class="btn btn-default" data-dismiss="modal">Cancel</a>
                <span data-bind="if:selection().length">
                    <a class="btn btn-primary" data-bind="click:submit">Add</a>
                </span>
            </div><!-- end modal-footer-->
        </div><!-- end modal-content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->
