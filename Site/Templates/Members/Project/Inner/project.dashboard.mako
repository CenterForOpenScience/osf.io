<% 
  from Framework import getUser 
  is_contributor = node_to_use.is_contributor(user)
%>
<%inherit file="project.view.mako" />
<%namespace file="_print_logs.mako" import="print_logs"/>
<%namespace file="_node_list.mako" import="node_list"/>
<%namespace file="_file_tree.mako" import="file_tree"/>
<link rel="stylesheet" type="text/css" href="/static/css/jquery.tagsinput.css" />
<script src="/static/js/jquery.tagsinput.min.js"></script>
<script>
    $(function(){
        $('#node-tags').tagsInput({
            width: "100%",
            interactive:${'true' if is_contributor else 'false'},
            onAddTag:function(tag){
                $.ajax({
                    url:"${node_to_use.url()}" + "/addtag/" + tag,
                    type:"GET",
                });
            },
            onRemoveTag:function(tag){
                $.ajax({
                    url:"${node_to_use.url()}" + "/removetag/" + tag,
                    type:"GET",
                });
            },
        });
    });
</script>
  <div class="row">
    <div class="span7">
      <section id="Wiki Home">
        <div>
        ${wiki_home}
        <p><a href="${node_to_use.url()}/wiki/home">read more</a></p>
        </div>
      </section>
       %if not node:
      <section id="Nodes">
          
          <div class="page-header">
              <div style="float:right;"><a class="btn" data-toggle="modal" href="#newComponent" >Add Component</a></div>
              <h1>Components</h1>
          </div>
          <div class="modal hide fade" id="newComponent">
          <form class="form-horizontal form-horizontal-narrow" action="/project/${project.id}/newnode" method="post">
            <div class="modal-header">
              <h3 class='img-add'>Add Component</h3>
            </div>
            <div class="modal-body">
                    <div class='control-group'>
                        <label for='title' class='control-label'>Title</label>
                        <input name="title" type="text" class='controls'>
                    </div>
                    <div class='control-group'>
                        <label for='category' class='control-label'>Category</label>
                        <select id="category" name="category" class='controls'>
                            <option disabled selected value=''>-- Choose--</option>
                            %for i in ["Project", "Hypothesis", "Methods and Measures", "Procedure", "Instrumentation", "Data", "Analysis", "Communication", "Other"]:
                            <option>${i}</option>
                            %endfor
                        </select>
                    </div>
            </div>
                <div class="modal-footer">
                   <a href="#" class="btn" data-dismiss="modal">Close</a>
                  <button type="submit" class="btn btn-primary">OK</button>
                </div>
            </form>
            </div>
              
          <script type="text/javascript">
            //$('#addContributor').modal('hide')
          </script>
          % if project.nodes:
            ${node_list(project.nodes.objects())}
          %else:
            <p>No components have been added to this project.</p>
          %endif
      </section>
      %endif
      <section id="Files">
        <div>
          <div class="page-header">
              <h1>Files</h1>
          </div>
          <ul id="browser" class="filetree">
          ${file_tree(files)}
          </ul>
        </div>
      </section>
    </div>
    <div class="span5">
        <div style="margin-right:12px;">
        <input name="node-tags" id="node-tags" value="${','.join(node_to_use.tags) if node_to_use.tags else ''}" />
        </div>
            <div>
                ${print_logs(reversed(node_to_use.logs.objects()), n=10)}
            </div>
            <div class="paginate" style="float:right;">more</div>
        </section>
    </div>
  </div>