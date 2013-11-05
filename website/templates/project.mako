<%inherit file="base.mako"/>
<%def name="title()">Project</%def>


<%def name="content()">
  <div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

  <div class="row">
    <div class="col-md-7" id='containment'>
      <section id="Wiki Home">
        <div>
            ${ wiki_home }
            <p><a href="${node_url}wiki/home">read more</a></p>
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
                                <input placeholder="Component Title" name="title" type="text" class='form-control'>
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
        <input name="node-tags" id="node-tags" value="${','.join([tag for tag in node_tags]) if node_tags else ''}" />
            <div id='logScope'>
                <dl class="dl-horizontal activity-log"
                    data-bind="foreach: {data: logs, as: 'log'}">
                  <div data-bind="template: {name: 'logTemplate', data: log}"></div>
                </dl><!-- end foreach logs -->
            </div>
            ## Hide More widget until paging for logs is implemented
            ##<div class="paginate pull-right">more</div>
        </section>
    </div>
  </div>

<%include file="log_template.mako"/>

##<!-- Include Knockout and view model -->
##<div mod-meta='{
##        "tpl": "metadata/knockout.mako",
##        "replace": true
##    }'></div>
##
##<!-- Render comments -->
##<div mod-meta='{
##        "tpl": "metadata/comment_group.mako",
##        "kwargs": {
##            "guid": "${node_id}",
##            "top": true
##        },
##        "replace": true
##    }'></div>
##
##<!-- Boilerplate comment JS -->
##<div mod-meta='{
##        "tpl": "metadata/comment_js.mako",
##        "replace": true
##    }'></div>

</%def>

<%def name="javascript_bottom()">
<script>
    $(document).ready(function() {

        ### Editable Title ###
        %if user_can_edit:
                $(function() {
                    $('#node-title-editable').editable({
                       type:  'text',
                       pk:    '${node_id}',
                       name:  'title',
                       url:   '${node_api_url}edit/',
                       title: 'Edit Title',
                       placement: 'bottom',
                       value: "${ '\\\''.join(node_title.split('\'')) }",
                       success: function(data){
                            document.location.reload(true);
                       }
                    });
                });
        %endif

        ### Tag Input ###

        $('#node-tags').tagsInput({
            width: "100%",
            interactive:${'true' if user_can_edit else 'false'},
            onAddTag:function(tag){
                $.ajax({
                    url:"${node_api_url}" + "addtag/" + tag + "/",
                    type:"POST",
                    contentType: "application/json"
                });
            },
            onRemoveTag:function(tag){
                $.ajax({
                    url:"${node_api_url}" + "removetag/" + tag + "/",
                    type:"POST",
                    contentType: "application/json"
                });
            },
        });
        % if not user_can_edit:
            // Remove delete UI if not contributor
            $('a[title="Removing tag"]').remove();
            $('span.tag span').each(function(idx, elm) {
                $(elm).text($(elm).text().replace(/\s*$/, ''))
            });
        % endif

        // Initiate LogsViewModel
        $logScope = $("#logScope");
        ko.cleanNode($logScope[0]);
        ko.applyBindings(new LogsViewModel($logScope.data("target")), $logScope[0]);
    });
</script>
</%def>
