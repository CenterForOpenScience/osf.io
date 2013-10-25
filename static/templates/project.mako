<%inherit file="base.mako"/>
<%def name="title()">Project</%def>

<%def name="stylesheets()">
<link rel="stylesheet" type="text/css" href="/static/css/jquery.tagsinput.css" />
</%def>

<%def name="javascript()">
<script src="//cdnjs.cloudflare.com/ajax/libs/knockout/2.3.0/knockout-min.js"></script>
</%def>

<%def name="javascript_bottom()">
<script src="/static/js/jquery.tagsinput.min.js"></script>
## Import Bootbox
<script src="//cdnjs.cloudflare.com/ajax/libs/bootbox.js/4.0.0/bootbox.min.js"></script>
<script>
    var addContributorModel = function(initial) {

        var self = this;

        self.query = ko.observable('');
        self.results = ko.observableArray(initial);
        self.selection = ko.observableArray([]);

        self.search = function() {
            $.getJSON(
                '/api/v1/user/search/',
                {query: self.query()},
                function(result) {
                    self.results(result);
                }
            )
        };

        self.addTips = function(elements, data) {
            elements.forEach(function(element) {
                $(element).find('.contrib-button').tooltip();
            });
        };

        self.add = function(data, element) {
            self.selection.push(data);
            // Hack: Hide and refresh tooltips
            $('.tooltip').hide();
            $('.contrib-button').tooltip();
        };

        self.remove = function(data, element) {
            self.selection.splice(
                self.selection.indexOf(data), 1
            );
            // Hack: Hide and refresh tooltips
            $('.tooltip').hide();
            $('.contrib-button').tooltip();
        };

        self.selected = function(data) {
            for (var idx=0; idx < self.selection().length; idx++) {
                if (data.id == self.selection()[idx].id)
                    return true;
            }
            return false;
        };

        self.submit = function() {
            var user_ids = self.selection().map(function(elm) {
                return elm.id;
            });
            $.ajax(
                '${node_api_url}addcontributors/',
                {
                    type: 'post',
                    data: JSON.stringify({user_ids: user_ids}),
                    contentType: 'application/json',
                    dataType: 'json',
                    success: function(response) {
                        if (response.status === 'success') {
                            window.location.reload();
                        }
                    }
                }
            )
        };

        self.clear = function() {
            self.query('');
            self.results([]);
            self.selection([]);
        };

    };

    var $addContributors = $('#addContributors');

    viewModel = new addContributorModel();
    ko.applyBindings(viewModel, $addContributors[0]);

    // Clear user search modal when dismissed; catches dismiss by escape key
    // or cancel button.
    $addContributors.on('hidden', function() {
        viewModel.clear();
    });
    $(function(){
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
</%def>

<%def name="content()">
<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>

  <div class="row">
    <div class="span7" id='containment'>
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
              <div style="float:right;">
                  % if user_can_edit:
                  <a class="btn" data-toggle="modal" href="#newComponent">
                  % else:
                  <a class="btn disabled">
                  % endif
                    Add Component
                  </a>
              </div>
              <h1>Components</h1>
          </div>
          <div class="modal hide fade" id="newComponent">
          <form class="form-horizontal form-horizontal-narrow" action="${node_url}newnode/" method="post">
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
    <div class="span5">
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
            <div class="paginate" style="float:right;">more</div>
        </section>
    </div>
  </div>
</%def>
