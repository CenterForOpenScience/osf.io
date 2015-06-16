<%inherit file="project/project_base.mako"/>
<%def name="title()">Register Component</%def>

<legend class="text-center">Register</legend>

    <form role="form">

        <!--<div class="help-block">${language.REGISTRATION_INFO}</div>-->

        <select class="form-control" id="select-registration-template">
            <option value="">Please select a registration form to initiate registration</option>
            % for option in options:
                <option value="${option['template_name']}">${option['template_name_clean']}</option>
            % endfor
        </select>

        <div class='container'>
          <div class='row'>
            <div class='span8 col-md-12 columns eight large-8'>
                      <h2 id="title">Select an option above</h2>
                      <nav>
                        <ul id="myNavBar" class="pagination">
     
                        </ul>
                      </nav>

                      <div id='editor'></div>
                      <button id="save" type="button" class="btn btn-success">Save</button>
            </div>
          </div>
        </div>


    </form>

    <script type="text/javascript">

        $('#select-registration-template').on('change', function() {
            var $tempName = '';
            var $this = $(this);
            var val = $this.val();
            if (val !== '') {
                document.getElementById("title").innerHTML = val;
                //var urlparse = window.location.href.split("#/");
                //console.log(urlparse[0]);
                //urlparse[0] += '/' + val;
                //window.location.href = urlparse.join("?")
                
            } else {
                document.getElementById("title").innerHTML = "Select an option above";
            }
        });

    </script>


<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src="${'/static/public/js/register-page.js' | webpack_asset}"></script>
</%def>
