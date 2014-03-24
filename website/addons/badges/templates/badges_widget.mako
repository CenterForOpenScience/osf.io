<div class="addon-widget" name="${short_name}">
<script src="/addons/static/badges/awardBadge.js"></script>
<script src="/addons/static/badges/bake-badges.js"></script>
<script src="/addons/static/badges/png-baker.js"></script>

%if complete:

    <h3 class="addon-widget-header">
        % if can_issue and configured:
            <button class="pull-right btn btn-success" id="awardBadge">
                <i class="icon-plus"></i>
                Award
            </button>
        % endif
          <span>${full_name}</span>
    </h3>
%if len(assertions) > 0:
  <div style="max-height:200px; overflow-y: auto; overflow-x: hidden;">
      <ul class="two-col" id="badgeList">
          %for assertion in assertions:
          <li>
            <a class="pull-left" href="/${assertion['uid']}/" style="margin-right: 5px;">
              <img src="${assertion['image']}" width="64px" height="64px" class="open-badge" badge-url="/${assertion['uid']}/json/" >
            </a>
            %if assertion['issuer_id'] == uid:
              <button class="btn btn-danger btn-xs pull-right revoke-badge" badge-uid="${assertion['uid']}" type="button">
                <i class="icon-minus"></i>
              </button>
            %endif
              <h5>${assertion['name']}</h5>
              ${assertion['criteria']}
          </li>
          %endfor
      </ul>
  </div>
%endif
<script>

$(document).ready(function(){
% if can_issue and configured:
    $('#awardBadge').editable({
      name:  'title',
      title: 'Award Badge',
      display: false,
      highlight: false,
      placement: 'right',
      showbuttons: 'bottom',
      type: 'AwardBadge',
      value: '${badges[0]['id']}',
      badges: [
        %for badge in badges:
          {value: '${badge['id']}', text: '${badge['name']}'},
        %endfor
      ],
      ajaxOptions: {
        'type': 'POST',
        "dataType": "json",
        "contentType": "application/json"
      },
      url: nodeApiUrl + 'badges/award/',
      params: function(params){
        // Send JSON data
        return JSON.stringify(params.value);
      },
      success: function(data){
        document.location.reload(true);
      },
      pk: 'newBadge'
    });

    $('.revoke-badge').editable({
      type: 'text',
      pk: 'revoke',
      title: 'Revoke this badge?',
      placeholder: 'Reason',
      display: false,
      validate: function(value) {
        if($.trim(value) == '') return 'A reason is required';
      },
      ajaxOptions: {
        'type': 'POST',
        "dataType": "json",
        "contentType": "application/json"
      },
      url: nodeApiUrl + 'badges/revoke/',
      params: function(params){
        // Send JSON data
        var uid = $(this).attr('badge-uid')
        return JSON.stringify({reason: params.value, id: uid});
      },
      success: function(data){
        document.location.reload(true);
      },
    });
%endif
});

</script>

<style>
.two-col {
    margin: 2px;
    padding: 2px;

}

.two-col li {
    display: inline-block;
    width: 47%;
    margin: 5px;
    padding: 10px;
    background-color: #EEE;
    border:2px #CCC solid;
    border-radius:5px;
    vertical-align:top;
}

.btn-success.editable:hover {
    background-color: #419641;
}

.btn-danger.editable:hover {
    background-color: #d2322d;
}
</style>
%else:
        <div mod-meta='{
                "tpl": "project/addon/config_error.mako",
                "kwargs": {
                    "short_name": "${short_name}",
                    "full_name": "${full_name}"
                }
            }'></div>
%endif
</div>
