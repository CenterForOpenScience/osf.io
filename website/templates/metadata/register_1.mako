<div class="col-md-6 col-md-offset-3" id="registration_template">

    <%include file="metadata_1.html" />

    <form class="form">

        % if not registered:

            <div id="embargo-addon" data-bind="with: $root.embargoAddon, ">
                <hr />

                <p class="help-block">${language.REGISTRATION_EMBARGO_INFO}</p>
                <select data-bind="options: registrationOptions, selectedOptions: registrationChoice, event: {change: checkShowEmbargoDatePicker}"></select>

              <div data-bind="visible: showEmbargoDatePicker">
                    <select class="col-md-3" data-bind="options: dayOptions, value: dayChoice"></select>
                    <select class="col-md-3" data-bind="options: monthOptions, value: monthChoice"></select>
                    <select class="col-md-3" data-bind="options: yearOptions, value: yearChoice"></select>
              </div>
                <hr />
##              <div><pre data-bind="text: ko.toJSON($data, null, 2)"></pre></div>
            </div>

            <div id="register-show-submit" data-bind="visible:$root.isLast()">

                <hr />

                <p class="help-block">${language.BEFORE_REGISTRATION_INFO}</p>

                <div class="form-group">
                    <label>
                        Type "register" if you are sure you want to continue
                    </label>
                    <div class="controls">
                        <input class="form-control" data-bind="value:$root.continueText, valueUpdate: 'afterkeydown'" />
                    </div>
                </div>
            </div>

        % endif

        % if not registered:
            <button id="register-submit" class="btn btn-success" data-bind="visible:$root.continueFlag, focus:$root.continueFlag">
                Register Now
            </button>
        % endif

    </form>

</div><!-- end #registration_template -->

<% import json %>
<script type="text/javascript">
    ## Make Mako variables accessible to JS modules.
    ## TODO: This information should be fetched from a JSON endpoint.
    window.contextVars = window.contextVars || {};
    window.contextVars.node = window.contextVars.node || {};
    window.contextVars.node.urls = window.contextVars.node.urls || {};
    window.contextVars.node.urls.api = ${json.dumps(node['api_url'])};
    window.contextVars.node.id = ${json.dumps(str(node['id']))};
    window.contextVars.node.children = ${[str(each) for each in children_ids]};
    window.contextVars.regTemplate = ${json.dumps(template_name or '')};
    window.contextVars.regSchema = ${schema};
    window.contextVars.regPayload = ${json.dumps(payload)};
    window.contextVars.registered = ${json.dumps(int(registered))};
</script>
