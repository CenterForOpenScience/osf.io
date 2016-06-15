<%inherit file="project/project_base.mako" />

%if len(assertions) > 0:
<ul class="two-col" id="badgeList">
    %for assertion in reversed(assertions):
        <div class="row well well-sm assertion">
            <div class="col-md-2">
              <img class="open-badge pull-left" badge-url="/badge/assertion/json/${assertion._id}/" src="${assertion.badge.image}" width="150px" height="150px">
            </div>

            <div class="col-md-8">
                <h4> <a href="/${assertion.badge._id}/">${assertion.badge.name}</a><small> ${assertion.badge.description}</small></h4>
                <p>${assertion.badge.criteria_list}</p>
            </div>

            <div class="col-md-2 assertion-dates">
                 <h5>Awarded on:</h5>
                  %for key in assertion.dates.keys():
                    %for date in assertion.dates[key]:
                      %if date[1]:
                        <a href="${date[1]}">${date[0]}</a>
                      %else:
                        ${date[0]}
                      %endif
                    %endfor
                    <br />by <a href="${assertion.dates[key][0][2].owner.profile_url}">${assertion.dates[key][0][2].owner.fullname}</a>
                  %endfor
                ##TODO
                <!-- <button class="btn btn-primary" data-toggle="buttons" >Do not display</button> -->
            </div>
        </div>
    %endfor
</ul>

<script>
  $script('/static/addons/badges/bake-badges.js')
</script>

<style type="text/css">
  .assertion {
    margin-right: 20px;
  }

  .assertion-dates {
    text-align: center;
    max-height: 200px;
    overflow: auto;
  }
</style>

%endif
