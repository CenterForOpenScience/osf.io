<div class="modal fade" id="duplicateModal">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-body">
                <div class="row">
                    <div class="col-md-4">
                        <h4 class="f-w-lg">Links To This Project
                                 <span class="btn btn-default disabled  pull-right">
                                    ${ node['points'] }
                                </span>
                        </h4>
                        ${ language.LINK_DESCRIPTION | n }
                        % if node['points'] > 0:

                        <a class="btn btn-info btn-block" href="#showLinks"
                                                        data-toggle="modal"
                                                        data-dismiss="modal"
                                                    >View Links </a>
                        % endif

                    </div>
                    <div class="col-md-4">
                        <h4 class="f-w-lg">Templated From
                            <span class="btn btn-default disabled pull-right">
                                ${ node['templated_count'] }
                            </span>
                        </h4>
                        ${ language.TEMPLATE_DESCRIPTION | n }
                        <a class="btn btn-primary form-control${'' if user_name and (user['is_contributor'] or node['is_public']) else ' disabled'}"
                           data-dismiss="modal"
                           onclick="NodeActions.useAsTemplate();"
                        >
                            ${ language.TEMPLATE_ACTION | n }
                        </a>

                    </div>
                    <div class="col-md-4">
                        <h4 class="f-w-lg">Forks
                            <button class="btn btn-default disabled pull-right"
                            >
                                ${ node['fork_count'] }
                            </button>
                        </h4>
                        % if not disk_saving_mode:
                            ${ language.FORK_DESCRIPTION | n }
                        % else:
                            ${ language.DISK_SAVING_MODE | n }
                        % endif
                        % if not disk_saving_mode:
                            <a class="btn btn-primary form-control${ '' if user_name and (user['is_contributor'] or node['is_public']) else ' disabled'}"
                               data-dismiss="modal"
                               onclick="NodeActions.forkNode();"
                            >
                                ${ language.FORK_ACTION | n }
                            </a>
                            <a class="btn btn-info btn-block m-t-xs" href="${ node['url'] }forks/">View Forks</a>
                        % endif
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
            </div>
        </div><!-- /.modal-content -->
    </div><!-- /.modal-dialog -->
</div><!-- /.modal -->

