<%inherit file="project/addon/node_settings.mako" />

%if user_has_auth and is_owner:
    <div class="form-group">
        <div class="well well-sm">Authorized by <a href="${owner_url}">${owner}</a></div>


        <input type="hidden" id="s3_bucket" value="${bucket}" name="s3_bucket" />

        <div class="btn-group btn-input">
          <button type="button" class="btn btn-default dropdown-toggle form-control" data-toggle="dropdown">
            <span id="bucketlabel" data-bind="label">${bucket if bucket else 'Select a bucket'}</span> <span class="caret"></span>
          </button>

          <ul class="dropdown-menu" role="menu">
            <li role="presentation" class="dropdown-header">Your buckets</li>
            ${bucket_list}
            <li role="presentation" class="divider"></li>
            <li role="presentation"><a href="#">Create a new bucket</a></li>
          </ul>

        </div>
    </div>
%elif user_has_auth:
 Authorized by <a href="${owner_url}">${owner}</a><br></br>
<div class="btn-group btn-input">
          <button type="button" class="btn btn-default dropdown-toggle form-control" data-toggle="dropdown" disabled>
            <span id="bucketlabel" data-bind="label">${bucket if bucket else 'Select a bucket'}</span> <span class="caret"></span>
          </button>
</div>
%else:
    Amazon Simple Storage Service add-on is not configured properly.
    <br>
    Configure this add-on on the <a href="/settings/">settings</a> page, or click <a class="widget-disable" href="${node['api_url']}s3/settings/disable/">here</a> to disable it.
    <br>
%endif


<script src="/addons/static/s3/s3-node-settings.js"></script>
<script type="text/javascript">
    var addonShortname = '${addon_short_name}';
    setDropDownListener();
</script>

<%def name="submit_btn()">
</%def>
