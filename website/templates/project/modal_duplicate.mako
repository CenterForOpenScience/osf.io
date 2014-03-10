<div class="modal fade" id="duplicateModal">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-body row">
                <div class="col-md-4">
                    <h4>
                        <div class="input-group">
                            <a class="btn btn-primary form-control">Link to this Project</a>
                            <a class="btn btn-default input-group-addon" href="#showLinks" data-toggle="modal" data-dismiss="modal">
                                ${ node['points'] }
                            </a>
                        </div>
                    </h4>
                    <p>Linking to this projet will reference it in another project, without creating a copy. The link will always point to the most up-to-date version.</p>
                </div>
                <div class="col-md-4">
                    <h4>
                        <div class="input-group">
                            <a class="btn btn-primary form-control" data-dismiss="modal" onclick="NodeActions.useAsTemplate();">Copy Project Structure</a>
                            <a class="btn btn-default disabled input-group-addon">${ node['templated_count'] }</a>
                        </div>
                    </h4>
                    <p>This option will create a new project, using this project as a template. The new project will be structured in the same way, but contain no data.</p>
                </div>
                <div class="col-md-4">
                    <h4>
                        <div class="input-group">
                            <a class="btn btn-primary form-control" data-dismiss="modal" onclick="NodeActions.forkNode();">Fork this Project</a>
                            <a class="btn btn-default input-group-addon" href="${ node['url'] }forks/">${ node['fork_count'] }</a>
                        </div>
                    </h4>
                    <p>Fork this project if you plan to build upon it in your own work. The new project will be an exact duplicate of this project's current state, with you as the only contributor.</p>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>
            </div>
        </div><!-- /.modal-content -->
    </div><!-- /.modal-dialog -->
</div><!-- /.modal -->