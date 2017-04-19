<div class="modal fade" id="addPointer">

    <div class="modal-dialog modal-lg">

        <div class="modal-content">

            <div class="modal-header">
                <h3>Link other OSF projects</h3>
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

                <br>
                <div>
                  <ul class="nav nav-tabs">
                    <li id="getLinksNodesTab" class="active"><a data-bind="click: nodeView">Projects</a></li>
                    <li id="getLinksRegistrationsTab"><a data-bind="click: registrationView">Registrations</a></li>
                  </ul>
                </div>
                <br>

                <!-- Choose which to add -->
                <div class="row">

                    <div class="col-md-12">
                        <div>
                            <span data-bind="if: (inputType() == 'nodes' && includePublic)" class="modal-subheader">Results: All Projects</span>
                            <span data-bind="if: (inputType() == 'nodes' && !includePublic())" class="modal-subheader">Results: My Projects</span>
                            <span data-bind="if: (inputType() != 'nodes' && includePublic)" class="modal-subheader">Results: All Registrations</span>
                            <span data-bind="if: (inputType() != 'nodes' && !includePublic())" class="modal-subheader">Results: My Registrations</span>
                        </div>
                        <div class="error" data-bind="text:errorMsg"></div>
                        <table class="table table-striped">
                            <tbody data-bind="foreach:{data:results}">
                                <tr class="pointer-tow">
                                    <td class="osf-icon-td">
                                        <div data-bind="if:!($root.selected($data))">
                                            <a
                                                  class="btn btn-success contrib-button"
                                                  data-bind="click:$root.add.bind($root)"
                                              ><i class="fa fa-plus"></i></a>
                                        </div>
                                        <div data-bind="if:($root.selected($data))">
                                            <a
                                              class="btn btn-default contrib-button"
                                              data-bind="click:$root.remove.bind($root)"
                                              ><i class="fa fa-minus"></i></a>
                                        </div>
                                    </td>
                                    <td data-bind="text:attributes.title" class="overflow"></td>
                                    <td class="node-dates" data-bind="text:$root.getDates($data)"></td>
                                    <td style="width: 20%" data-bind="text:$root.authorText($data)"></td>
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
                </div>

            </div><!-- end modal-body -->

            <div class="modal-footer">

                <a class="btn btn-default" data-bind='click:done' data-dismiss="modal">Done</a>
                <div class="help-block">
                    <span class="text-danger" data-bind="html: submitWarningMsg"></span>
                </div>
            </div><!-- end modal-footer -->

        </div><!-- end modal-content -->

    </div><!-- end modal-dialog -->

</div><!-- end modal -->
