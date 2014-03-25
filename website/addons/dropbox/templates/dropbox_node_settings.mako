<%inherit file="../../project/addon/node_settings.mako" />

<script src="/static/vendor/bower_components/typeahead.js/dist/typeahead.jquery.js"></script>
<script src="/static/vendor/bower_components/typeahead.js/dist/bloodhound.min.js"></script>
<link rel="stylesheet" href="/addons/static/dropbox/node_settings.css">
<script src="/addons/static/dropbox/node-settings.js"></script>

<div class="row">
    <div class="col-md-12">
        <div class="input-group">
            <input class="form-control" id="dropboxFolderSelect" type="text" placeholder="Choose a folder">
            <span class="input-group-btn">
                <button id="dropboxSubmit" type="button" class="btn btn-primary" disabled="disabled">Create</button>
            </span>
        </div>
    </div>
</div>

<%def name="submit_btn()">
</%def>


<%def name="title()">
    <h4>
        ${addon_full_name}
        % if node_has_auth:
        <small> Authorized by <a href="${owner_url}">${owner}</a></small>
            %if user_has_auth:
                <small  class="pull-right" >
                    <a id="dropboxDelKey" class="text-danger" style="cursor: pointer">Deauthorize</a>
                </small>
            %endif
        %endif
    </h4>
</%def>
