<!-- New Component Modal -->
<div class="modal fade" id="newComponent">
    <div class="modal-dialog">
        <div class="modal-content">
            <form class="form" role="form" action="${node['url']}newnode/" method="post" id="componentForm">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h3 class="modal-title">Add Component</h3>
                </div><!-- end modal-header -->
                <div class="modal-body">
                    <div class="form-group">
                        <input id="title" maxlength="200" placeholder="Component Title" name="title"  type="text" class='form-control'>
                        <div class="modal-alert"></div>
                    </div>
                    <div class="form-group">
                        <select id="category" name="category" class="form-control">
                            <option disabled selected value=''>-- Category--</option>
                            ## TODO: Remove hardcoded category values here and use the values from Node.CATEGORY_MAP
                            %for key, value in node_categories.iteritems():
                            <option value="${key}">${value}</option>
                            %endfor
                        </select>
                    </div>
                </div><!-- end modal-body -->
                <div class="modal-footer">
                    <a id="confirm" href="#" class="btn btn-default" data-dismiss="modal">Cancel</a>
                    <button id="add-component-submit" type="submit" class="btn btn-success">Add</button>
                </div><!-- end modal-footer -->
            </form>
        </div><!-- end modal- content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->
