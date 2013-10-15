<div mod-meta='{"tpl": "header.mako", "replace": true}'></div>
<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>

## TODO: Move to header.mako
<!-- Import jQuery tags -->
<link rel="stylesheet" type="text/css" href="/static/css/jquery.tagsinput.css" />
<script src="/static/js/jquery.tagsinput.min.js"></script>

<script>
    $(function(){
        $('#node-tags').tagsInput({
            width: "100%",
            interactive:${'true' if user_can_edit else 'false'},
            onAddTag:function(tag){
                $.ajax({
                    url:"${node_api_url}" + "addtag/" + tag,
                    type:"GET",
                });
            },
            onRemoveTag:function(tag){
                $.ajax({
                    url:"${node_api_url}" + "removetag/" + tag,
                    type:"GET",
                });
            },
        });
        // Remove delete UI if not contributor
        % if not user_can_edit:
            $('a[title="Removing tag"]').remove();
            $('span.tag span').each(function(idx, elm) {
                $(elm).text($(elm).text().replace(/\s*$/, ''))
            });
        % endif
    });
</script>
  <div class="row">
    <div class="col-md-7" id='containment'>
      <section id="Wiki Home">
        <div>
        %if wiki_home:
            ${ wiki_home }
            <p><a href="${node_url}/wiki/home">read more</a></p>
        %else:
            <p>No content</p>
        %endif
        </div>
      </section>
       %if not node:
      <section id="Nodes">

          <div class="page-header">
              <div class="pull-right">
                  % if user_can_edit:
                  <a class="btn btn-default" data-toggle="modal" data-target="#newComponent">
                  % else:
                  <a class="btn btn-default disabled">
                  % endif
                    Add Component
                  </a>
              </div>
              <h1>Components</h1>
          </div>
          <!-- New Component Modal -->
          <div class="modal fade" id="newComponent">
            <div class="modal-dialog">
                <div class="modal-content">
                <form class="form" role="form" action="${node_url}newnode/" method="post">
                    <div class="modal-header">
                        <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                      <h3 class="modal-title">Add Component</h3>
                    </div><!-- end modal-header -->
                    <div class="modal-body">
                            <div class='form-group'>
                                <input placeholder="Title" name="title" type="text" class='form-control'>
                            </div>
                            <div class='form-group'>
                                <select id="category" name="category" class='form-control'>
                                    <option disabled selected value=''>-- Category--</option>
                                    %for i in ["Project", "Hypothesis", "Methods and Measures", "Procedure", "Instrumentation", "Data", "Analysis", "Communication", "Other"]:
                                    <option>${i}</option>
                                    %endfor
                                </select>
                            </div>
                    </div><!-- end modal-body -->
                    <div class="modal-footer">
                       <a href="#" class="btn btn-default" data-dismiss="modal">Close</a>
                      <button type="submit" class="btn btn-primary">OK</button>
                    </div><!-- end modal-footer -->
                </form>
                </div><!-- end modal- content -->
              </div><!-- end modal-dialog -->
            </div><!-- end modal -->

          <script type="text/javascript">
            //$('#addContributor').modal('hide')
          </script>
          % if node_children:
              <div mod-meta='{
                      "tpl" : "util/render_nodes.mako",
                      "uri" : "${node_api_url}get_children/",
                      "replace" : true,
                      "kwargs" : {"sortable" : true}
                  }'></div>
          % else:
              <p>No components have been added to this project.</p>
          % endif
      </section>
      %endif
      <section id="Files">
        <div>
          <div class="page-header">
              <h1>Files</h1>
          </div>
          <ul id="browser" class="filetree">
              <div mod-meta='{
                      "tpl": "util/render_file_tree.mako",
                      "uri": "${node_api_url}get_files/",
                      "replace": true
                  }'></div>
          </ul>
        </div>
      </section>
    </div>
    <div class="col-md-5">
        <div style="margin-right:12px;">
        <input name="node-tags" id="node-tags" value="${','.join([tag for tag in node_tags]) if node_tags else ''}" />
        </div>
            <div id='main-log'>
                <div mod-meta='{
                        "tpl": "util/render_logs.mako",
                        "uri": "${node_api_url}log/",
                        "view_kwargs": {
                            "count": 10
                        },
                        "replace": true
                    }'></div>
            </div>
            <div class="paginate pull-right">more</div>
        </section>
    </div>
  </div>

<div mod-meta='{"tpl": "footer.mako", "replace": true}'></div>
