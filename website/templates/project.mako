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
            % if node_category == 'project':
              <div class="pull-right">
                  % if user_can_edit:
                  <a class="btn btn-default" data-toggle="modal" data-target="#newComponent">
                  % else:
                  <a class="btn btn-default disabled">
                  % endif
                    Add Component
                  </a>
              </div>
              <%include file="modal_add_component.mako"/>
            % endif
              <h1>Components</h1>
          </div>
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
          <div mod-meta='{
                  "tpl": "util/render_file_tree.mako",
                  "uri": "${node_api_url}get_files/",
                  "view_kwargs": {
                      "dash": true
                  },
                  "replace": true
              }'></div>
        </div>
      </section>
    </div>
    <div class="col-md-5">
        <input name="node-tags" id="node-tags" value="${','.join([tag for tag in node_tags]) if node_tags else ''}" />
            <div id='logScope'>
                <div data-bind="if:tzname">
                    All times displayed at
                    <span data-bind="text:tzname"></span>
                    <a href="http://en.wikipedia.org/wiki/Coordinated_Universal_Time" target="_blank">UTC</a> offset.
                </div>
                 <dl class="dl-horizontal activity-log"
                    data-bind="foreach: {data: logs, as: 'log'}">
                    <dt><span class="date log-date" data-bind="text: log.localDatetime, tooltip: {title: log.utcDatetime}"></span></dt>
                  <dd class="log-content">
                    <a data-bind="text: log.userFullName || log.apiKey, attr: {href: log.userURL}"></a>
                    <!-- log actions are the same as their template name -->
                    <span data-bind="template: {name: log.action, data: log}"></span>
                  </dd>

                </dl><!-- end foreach logs -->
            </div>
            ## Hide More widget until paging for logs is implemented
            ##<div class="paginate pull-right">more</div>
        </section>
    </div>
  </div>

<%include file="log_templates.mako"/>

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
