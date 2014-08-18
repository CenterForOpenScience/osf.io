<%inherit file="base.mako"/>
<%def name="title()">Search</%def>
<%def name="content()">
<section id="Search" xmlns="http://www.w3.org/1999/html">
  <div class="page-header">
    % if query or tags:
      <h1>
        % if query == '*' and not tags:
          Showing all<small>
        % else:
          Search <small> for
##        first show query, if it is there
          % if query:
            <span class="label label-success btn-mini query-label">${query}
              <a href="/search/?type=${type}&tags=${','.join(tags)}" class="remove-button">&times;</a>
            </span>
          % endif
##        then show tags
          % if tags:
            % for tag in tags:
              <span class="label label-info btn-mini query-label">${tag}
                <a href="/search/?q=${query if query != '*' else ''}&type=${type}&tags=${','.join((x for x in tags if x != tag)) | h }" class="remove-button">&times;</a>
              </span>
            % endfor
          % endif
        % endif
        <br>
##      number of results returned and the time it took
        ${total} result${'s' if total is not 1 else ''} in ${time} seconds</small>
      </h1>
    % else:
      <h1>No query</h1>
    % endif
  </div><!-- end page-header -->
</section>
<div class="row">
  <div class="col-md-3">
    % if (query or tags) and isinstance(counts, dict):
      <ul class="nav nav-pills nav-stacked search-types">
        <li class="${'active' if type == '' else ''}"><a href="/search/?q=${query}&tags=${','.join(tags)}">All: ${counts['all']}</a></li>
        <li class="${'active' if type == 'user' else ''}"><a href="/search/?q=${query}&tags=${','.join(tags)}&type=user">Users: ${counts['users']}</a></li>
        <li class="${'active' if type == 'project' else ''}"><a href="/search/?q=${query}&tags=${','.join(tags)}&type=project">Projects: ${counts['projects']}</a></li>
        <li class="${'active' if type == 'component' else ''}"><a href="/search/?q=${query}&tags=${','.join(tags)}&type=component">Components: ${counts['components']}</a></li>
        <li class="${'active' if type == 'registration' else ''}"><a href="/search/?q=${query}&tags=${','.join(tags)}&type=registration">Registrations: ${counts['registrations']}</a></li>
      </ul>
    % endif
##  our tag cloud!
    % if cloud:
      <div class="panel panel-default tag-cloud">
        <div class="panel-heading">
          <h3>${'Improve Your Search' if query != '*' else 'Popular Tags'}:</h3>
        </div>
        <div class="panel-body">
          % for key, value in cloud:
            <span id="tagCloud">
              <a href="/search/?q=${query}&type=${type}&tags=${','.join(tags) + ',' + key}" rel=${value}> ${key} </a>
            </span>
          % endfor
        </div>
      </div>
    % endif
  </div><!-- end col-md -->
  <div class="col-md-9">
    % if results:
##    iterate through our nice lists of results
      <div class="list-group">
        % for result in results:
          <div class="list-group-item result">
##          users are different results than anything associated with projects
            % if 'user' in result:
              <div class="title">
                <h4>
                  % if not type == 'user':
                    <small>[ User ]</small>
                  % endif
                  <a href=${result['user_url']}>${result['user']}</a>
                </h4>
              </div><!-- end user name -->

              % if result['job']:
                <div class="search-field">
                  <p>Employment: ${result['job_title'] if result['job_title'] else 'works'} at ${result['job']}</p>
                </div>
              % endif
              % if result['school']:
                <div class="search-field">
                  <p>Education: ${result['degree'] if result['degree'] else 'studied'} at ${result['school']}</p>
                </div>
              % endif
              % if not (result['school'] or result['job']):
                <div class="search-field">
                  <p class="text-muted">No employment or education information given</p>
                </div>
              % endif

            % else:
              <div class="title">
                <h4>
                  %if result.get('is_registration'):
                    <small>[ Registration${': ' + result['registered_date'] if result.get('registered_date') else ''} ]</small>
                  %endif
                  % if result['url']:
                    <a href=${result['url']}>${result['title']}</a>
                  %else:
                    <span class="private-title">${result['title']}</span>
                  % endif
                </h4>
              </div><!-- end title -->

              <div class="description">
                % if result['description']:
                  <h5>
                    ${result['description'][:500]}${'...' if len(result['description']) > 500 else ''}
                  </h5>
                % elif result['is_component']:
                  <h5>
                    Component of
                    % if result['parent_url']:
                      <a href=${result['parent_url']}>${result['parent_title']}</a>
                    % else:
                      <span class="private-title">${result['parent_title']}</span>
                    % endif
                  </h5>
                % else:
                  <h5 class="text-muted">No description</h5>
                % endif
              </div><!-- end description -->

##            jeff's nice logic for displaying users
              <div class="search-field contributors">
                % for index, (contributor, url) in enumerate(zip(result['contributors'][:3], result['contributors_url'][:3])):
                  <%
                    if index == 2 and len(result['contributors']) > 3:
                      # third item, > 3 total items
                      sep = ' & <a href="{url}">{num} other{plural}</a>'.format(
                        num=len(result['contributors']) - 3,
                        plural='s' if len(result['contributors']) - 3 else '',
                        url=result['url']
                      )
                    elif index == len(result['contributors']) - 1:
                      # last item
                      sep = ''
                    elif index == len(result['contributors']) - 2:
                      # second to last item
                      sep = ' & '
                    else:
                      sep = ','
                  %>
                  <a href=${url}>${contributor}</a>${sep}
                % endfor
              </div><!-- end contributors -->
##            if there is a wiki link, display that
              % if result['wiki_link']:
                <div class="search-field">
                  <a href=${result['wiki_link']}> jump to wiki </a>
                </div><!-- end wiki link -->
              % endif
##            show all the tags for the project
              % if result['tags']:
                <div class="search-tags">
                  % for tag in result['tags']:
                    <a href='/search/?tags=${tag}' class="label label-info btn-mini">${tag}</a>
                  % endfor
                </div>
              % endif
            %endif
          </div><!-- end result-->
        % endfor
      </div>
##    pagination! we're simply going to build a query by telling solr which 'row' we want to start on
      <div class="navigate">
        <ul class="pagination">
        % if counts['total'] > 10:
          <li><a href="?q=${query | h}&type=${type}&tags=${tags}&pagination=${0}">First</a></li>
          % if current_page >= 10:
            <li><a href="?q=${query | h}&type=${type}&tags=${tags}&pagination=${(current_page)-10}">&laquo;</a></li>
          % else:
            <li><a href="#">&laquo;</a></li>
          % endif
            % for i, page in enumerate(range(0, counts['total'], 10)):
              % if i == current_page/10:
                <li class="active"><a href="#">${i+1}</a></li>
              ## The following conditionals force the page to display at least 5 pages in the navigation bar
              % elif (current_page/10 == 0) and (i in range(1,5)):
                <li><a href="?q=${query | h}&type=${type}&tags=${tags}&pagination=${page}">${i+1}</a></li>
              % elif (current_page/10 == 1) and (i in range(2,5)):
                <li><a href="?q=${query | h}&type=${type}&tags=${tags}&pagination=${page}">${i+1}</a></li>
              % elif (current_page/10 == total/10) and (i in range((counts['total']/10 - 4), counts['total'])):
                <li><a href="?q=${query | h}&type=${type}&tags=${tags}&pagination=${page}">${i+1}</a></li>
              % elif (current_page/10 == ((total/10) - 1)) and (i in range((counts['total']/10 -4), counts['total'])):
                <li><a href="?q=${query | h}&type=${type}&tags=${tags}&pagination=${page}">${i+1}</a></li>
              % elif (i in range((current_page-20)/10, current_page/10)) or (i in range(current_page/10, (current_page+30)/10)):
                <li><a href="?q=${query | h}&type=${type}&tags=${tags}&pagination=${page}">${i+1}</a></li>
              % endif
            % endfor
          % if current_page < (counts['total']-10):
            <li><a href="?q=${query | h}&type=${type}&tags=${tags}&pagination=${(current_page)+10}">&raquo;</a></li>
          % else:
            <li><a href="#">&raquo;</a></li>
          % endif
          <li><a href="?q=${query | h}&type=${type}&tags=${tags}&pagination=${(counts['total']-1)/10 * 10}">Last</a></li>
        % endif
        </ul>
      </div><!-- end navigate -->
    % else:
      No results found. <br />
    %endif
  </div><!--end col-md -->
</div><!-- end row -->
</%def>

<%def name="javascript_bottom()">
<script>
  //  Initiate tag cloud (on search page)
  $.fn.tagcloud.defaults = {
    size: {start: 14, end: 18, unit: 'pt'},
    color: {start: '#cde', end: '#f52'}
  };

  $(function () {
    $('#tagCloud a').tagcloud();
  });
</script>

</%def>
