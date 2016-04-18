<!-- New Component Modal -->
<div class="modal fade" id="newComponent">
    <div class="modal-dialog">
        <div class="modal-content">
            <form class="form" role="form" action="${node['url']}newnode/" method="post" id="componentForm">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h3 class="modal-title">Add component</h3>
                </div><!-- end modal-header -->
                <div class="modal-body">
                    <div class="form-group">
                        <input id="title" maxlength="200" placeholder="Component Title" name="title"  type="text" class='form-control'>
                        <div class="help-block">
                          <span class="modal-alert text-danger"></span>
                        </div>
                    </div>
                    <div class="form-group">
                        <select id="category" name="category" class="form-control">
                            <option disabled selected value=''>-- Category--</option>
                            %for key, value in node_categories.iteritems():
                            <option value="${key}">${value}</option>
                            %endfor
                        </select>
                    </div>
                    %if (len(node['contributors']) > 1) and user['can_edit']:
                        <div class="form-group">
                            <label class="f-w-md"><input id="inherit_contributors"
                                          name="inherit_contributors"
                                          value="True"
                                          type="checkbox"/> Add contributors from <b>${node['title']}</b></label>
                        </div>
                    %endif
                </div><!-- end modal-body -->
                <div class="modal-footer">
                    <a id="confirm" href="#" class="btn btn-default" data-dismiss="modal">Cancel</a>
                    <button id="add-component-submit" type="submit" class="btn btn-success">Add</button>
                </div><!-- end modal-footer -->
            </form>
        </div><!-- end modal- content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->
