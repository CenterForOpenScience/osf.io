<div class="addon-widget" name="${short_name}">
%if complete:

    <h3 class="addon-widget-header">
        % if can_issue and configured:
            <button class="pull-right btn btn-success btn-popover">
                <i class="icon-plus"></i>
                Award
            </button>
        % endif
          <span>${full_name}</span>
    </h3>

<div style="max-height:200px; overflow-y: auto; overflow-x: hidden;">
    <ul class="two-col" id="badgeList">
        %for assertion in assertions:
        <li>
          <a class="pull-left" href="/${assertion['uid']}/">
            <img src="${assertion['image']}" width="64px" height="64px">
          </a>
            <h5>${assertion['name']}</h5>
            ${assertion['criteria']}
        </li>
        %endfor
    </ul>
</div>
<script>

$(document).ready(function(){

    $('.btn-popover').editable({
      name:  'title',
      title: 'Award Badge',
      display: false,
      highlight: false,
      placement: 'right',
      type: 'select',
      value: '${badges[0]['id']}',
      source: [
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
        return JSON.stringify({badgeid: params.value});
      },
      success: function(data){
        document.location.reload(true);
      },
      pk: 'newBadge'
    });
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
