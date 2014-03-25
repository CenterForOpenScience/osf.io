<%inherit file="project/project_base.mako" />
<script src="/addons/static/badges/bake-badges.js"></script>
<script src="/addons/static/badges/png-baker.js"></script>
<script src="/addons/static/badges/awardBadge.js"></script>

%if len(assertions) > 0:
<ul class="two-col" id="badgeList" style="max-height:600px; overflow-y: auto; overflow-x: hidden;">
    %for assertion in assertions:
        <div class="row well well-sm" style="margin-right: 20px;">
            <div class="col-md-2">

                <a class="pull-left" href="/${assertion['uid']}/json/">
                    <img class="open-badge" badge-url="/${assertion['uid']}/json/" src="${assertion['image']}" width="150px" height="150px" id="image">
                </a>
            </div>

            <div class="col-md-8">
                <h4> <a href="${assertion['url']}">${assertion['name']}</a><small> ${assertion['description']}</small></h4>
                    <p>${assertion['criteria']}</p>
            </div>

            <div class="col-md-2" style="text-align:center">
                %if assertion['issuer_id'] == uid:
                  <button class="btn btn-danger btn-xs pull-right revoke-badge" badge-uid="${assertion['uid']}" type="button">
                    <i class="icon-minus"></i>
                  </button>
                %endif
                %if assertion.get('evidence'):
                    <a href="${assertion['evidence']}"><h href>Awarded on ${assertion['issued_on']}</h5></a>
                %else:
                    <h5 href>Awarded on ${assertion['issued_on']}</h5>
                %endif
                ##TODO
                <!-- <button class="btn btn-primary" data-toggle="buttons" >Do not display</button> -->
            </div>
        </div>
    %endfor
</ul>
%endif

<script type="text/javascript">
$(document).ready(function(){

% if can_issue and configured and len(badges) > 0:
    $('#awardBadge').editable({
      name:  'title',
      title: 'Award Badge',
      display: false,
      highlight: false,
      placement: 'bottom',
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
      placement: 'left',
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

<style type="text/css">
.btn-success.editable:hover {
    background-color: #419641;
}

.btn-danger.editable:hover {
    background-color: #d2322d;
}

</style>
