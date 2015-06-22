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
                      <span id="myNavBar"></span>

                      <div id='editor'></div>
                      <button id="save" type="button" class="btn btn-success">Save</button>
            </div>
          </div>
        </div>


    </form>

<%def name="javascript_bottom()">
    ${parent.javascript_bottom()}
    <script src="${'/static/public/js/register-page.js' | webpack_asset}"></script>
</%def>
