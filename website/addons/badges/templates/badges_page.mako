<%inherit file="project/project_base.mako" />
<script src="/addons/static/badges/bake-badges.js"></script>
<script src="/addons/static/badges/png-baker.js"></script>
<script src="/addons/static/badges/awardBadge.js"></script>

%if len(assertions) > 0:
<ul class="two-col" id="badgeList">
    %for assertion in reversed(assertions):
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
                 <h5>Awarded on
                %if assertion.get('evidence'):
                   <a href="${assertion['evidence']}">${assertion['issued_on']}</a>
                %else:
                    ${assertion['issued_on']}
                %endif
                <br />by <a href="${assertion['issuer']}">${assertion['issuer_name']}</a></h5>
                ##TODO
                <!-- <button class="btn btn-primary" data-toggle="buttons" >Do not display</button> -->
            </div>
        </div>
    %endfor
</ul>
%endif

% if can_issue and configured and len(badges) > 0:
  <script type="text/javascript">
  $(document).ready(function(){
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

  });
  </script>

  <style type="text/css">
    .btn-danger.editable:hover {
        background-color: #d2322d;
    }
  </style>
%endif
