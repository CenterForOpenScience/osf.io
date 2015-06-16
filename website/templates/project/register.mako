<%inherit file="project/project_base.mako"/>
<%def name="title()">Register Component</%def>

<legend class="text-center">Register</legend>

% if schema:
    <%include file="metadata/register_${str(metadata_version)}.mako" />
% else:

    <form role="form">

        <div class="help-block">${language.REGISTRATION_INFO}</div>

        <div class='container'>
          <div class='row'>
            <div class='span8 col-md-12 columns eight large-8'>
                      <h2>Registration</h2>
                      <nav>
                        <ul class="pagination">
                          <li>
                            <a id="prev" href="#" aria-label="Previous">
                              <span aria-hidden="true">&laquo;</span>
                            </a>
                          </li>
                          <li><a id="project_info_button" href="#">Project Info</a></li>
                          <li><a id="your_info_button" href="#">Your Info</a></li>
                          <li><a id="interesting_button" href="#">Interesting Questions</a></li>
                          <li>
                            <a id="next" href="#" aria-label="Next">
                              <span aria-hidden="true">&raquo;</span>
                            </a>
                          </li>
                        </ul>
                      </nav>

                      <div id='editor'></div>
                      <button id="save" type="button" class="btn btn-primary">Save</button>
            </div>
          </div>
        </div>

        <select class="form-control" id="select-registration-template">
            <option value="">Please select a registration form to initiate registration</option>
            % for option in options:
                <option value="${option['template_name']}">${option['template_name_clean']}</option>
            % endfor
        </select>
    </form>


    <script type="text/javascript">
        $('#select-registration-template').on('change', function() {
            var $this = $(this);
            var val = $this.val();
            if (val !== '') {
                var urlparse = window.location.href.split("?");
                urlparse[0] += '/' + val;
                window.location.href = urlparse.join("?")
            }
        });
    </script>

% endif

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    % if schema:
    <script src="${'/static/public/js/register_{0}-page.js'.format(metadata_version) | webpack_asset}"></script>
    % endif
</%def>
