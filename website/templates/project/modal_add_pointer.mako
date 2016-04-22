<div class="modal fade" id="addPointer">

    <div class="modal-dialog modal-lg">

        <div class="modal-content">

            <div class="modal-header">
                <h3>Add Links</h3>
            </div>

            <div class="modal-body">

                <form role='form'>
                    <div class="form-group">
                        <input class="form-control" placeholder="Search projects" style="margin-bottom: 8px;" data-bind="value:query" />

                        <div class="help-block">
                            <span class="text-danger" data-bind="html: searchWarningMsg"></span>
                        </div>
                    </div>
                    <div>
                      <button class="btn btn-default"
                          data-bind="click:searchAllProjects,
                          text: searchAllProjectsSubmitText(),
                          attr: {disabled: loadingResults()}">
                          Search all projects
                      </button>
                      <button class="btn btn-default"
                        data-bind="
                        click: searchMyProjects,
                        text: searchMyProjectsSubmitText(),
                        attr: {disabled: loadingResults()}">
                        Search my projects</button>
                    </div>
                </form>

                <hr />

                <!-- Choose which to add -->
                <div class="row">

                    <div class="col-md-6">
                        <div>
                            <span class="modal-subheader">Results</span>
                            <a data-bind="click:addAll">Add all</a>
                        </div>
                        <div class="error" data-bind="text:errorMsg"></div>
                        <table class="table table-striped">
                            <tbody data-bind="foreach:{data:results, afterRender:addTips}">
                                <tr data-bind="if:!($root.selected($data))">
                                    <td class="osf-icon-td">
                                        <a
                                                class="btn btn-success contrib-button"
                                                data-bind="click:$root.add, tooltip: {title: 'Add link'}"
                                            ><i class="fa fa-plus"></i></a>
                                    </td>
                                    <td data-bind="text:title" class="overflow"></td>
                                    <td style="width: 25%" data-bind="text:$root.authorText($data)"></td>
                                </tr>
                            </tbody>
                        </table>
                        <div class='help-block'>
                            <div data-bind='if: loadingResults'>
                                <div class="spinner-loading-wrapper">
                                    <div class="logo-spin logo-lg"></div>
                                    <p class="m-t-sm fg-load-message"> Loading results...  </p>
                                </div>
                            </div>

                            <div data-bind='if: foundResults'>
                                <ul class="pagination pagination-sm" data-bind="foreach: paginators">
                                    <li data-bind="css: style"><a href="#" data-bind="click: handler, text: text"></a></li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-6">
                        <div>
                            <span class="modal-subheader">Adding</span>
                            <a data-bind="click:removeAll">Remove all</a>
                        </div>
                        <table class="table table-striped">
                            <tbody data-bind="foreach:{data:selection, afterRender:addTips}">
                                <tr>
                                    <td class="osf-icon-td">
                                        <a
                                                class="btn btn-default contrib-button"
                                                data-bind="click:$root.remove, tooltip: {title: 'Remove link'}"
                                            ><i class="fa fa-minus"></i></a>
                                    </td>
                                    <td  data-bind="text:title" class="overflow"></td>
                                    <td style="width: 25%" data-bind="text:$root.authorText($data)"></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                </div>

            </div><!-- end modal-body -->

            <div class="modal-footer">

                <a class="btn btn-default" data-dismiss="modal">Cancel</a>

                <span data-bind="if:selection().length">
                    <a class="btn btn-success" data-bind="click:submit, css: {disabled: !submitEnabled() }">Add</a>
                </span>
                <div class="help-block">
                    <span class="text-danger" data-bind="html: submitWarningMsg"></span>
                </div>
            </div><!-- end modal-footer -->

        </div><!-- end modal-content -->

    </div><!-- end modal-dialog -->

</div><!-- end modal -->
