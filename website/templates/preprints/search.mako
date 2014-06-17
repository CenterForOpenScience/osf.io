<%inherit file="base.mako"/>
<%def name="title()">Search</%def>
<%def name="content()">
<section id="Search" xmlns="http://www.w3.org/1999/html">
    <div class="page-header">
        % if query:
##            split on and, so we will be able to remove tags
            <%
                cleaned_query = 'AND'.join(query.split('AND'))
                components = cleaned_query.split('AND')
            %>
        <h1>Search <small> for
##            for showing tags
            % for i, term in enumerate(components):
##              the first is not removable. we need it to query
                    <span class="label label-success btn-mini" style="margin-right:.5em">${term.replace('(', ' ').replace(')',' ')}\
                        % if len(components) > 1:
                        <a href="/search/?q=${'AND'.join((x for x in components if x != term)) | h }" style="color:white">&times;</a>
                        % endif
<%                %></span>
            % endfor
         <br>
##       number of results returned and the time it took
        ${total} result${'s' if total is not 1 else ''} in ${time} seconds</small></h1>
        % endif
    </div><!-- end page-header -->
</section>
<div class="row">
    <div class="col-md-10">
            % if results:
##            iterate through our nice lists of results
                % for result in results:
                    <div class="result">
##                    users are different results than anything associated with projects
                        % if 'user' in result:
                            <div class="user">
                            <a href=${result['user_url']}>${result['user']}</a>
                            </div>
                    </div><!-- end result -->
                        % else:
                            <div class="title">
                                <h4>
                                    %if result.get('is_registration'):
                                        <small>[ Registration ]</small>
                                    %endif
                                    % if result['url']:
                                        <a href=${result['url']}>${result['title']}</a>
                                    %else:
                                        <span style='font-weight:normal; font-style:italic'>${result['title']}</span>
                                    % endif
                                </h4>
                            </div><!-- end title -->
            
                            <div class="description">
                                % if result['description']:
                                    <h5>
                                        ${result['description']}
                                    </h5>
                                % endif
                            </div>
                            
    ##                            jeff's nice logic for displaying users
                            <div class="contributors">
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
    ##                      if we have nested, we have to iterate by keys
    ##                      because many different nodes can be displayed in the nest
    ##                      section of the dictionary
                    </div><!-- end result-->
                    <br>
                    %endif
                % endfor
##            pagination! we're simply going to build a query by telling solr which 'row' we want to start on
                <div class="navigate">
                    <ul class="pagination">
                    % if total > 10:
                        <li> <a href="?q=${query | h}&pagination=${0}">First</a></li>
##                        <a href="?q=${query | h}&pagination=${0}">First</a>
                        % if current_page >= 10:
                              <li><a href="?q=${query | h}&pagination=${(current_page)-10}">&laquo;</a></li>
                        % else:
                            <li><a href="#">&laquo;</a></li>
                        % endif
                            % for i, page in enumerate(range(0, total, 10)):
                                % if i == current_page/10:
                                  <li class="active"><a href="#">${i+1}</a></li>
                                ## The following conditionals force the page to display at least 5 pages in the navigation bar
                                % elif (current_page/10 == 0) and (i in range(1,5)):
                                     <li><a href="?q=${query | h}&pagination=${page}">${i+1}</a></li>
                                % elif (current_page/10 == 1) and (i in range(2,5)):
                                    <li><a href="?q=${query | h}&pagination=${page}">${i+1}</a></li>
                                % elif (current_page/10 == total/10) and (i in range(total - 4), total):
                                    <li><a href="?q=${query | h}&pagination=${page}">${i+1}</a></li>
                                % elif (current_page/10 == ((total/10) - 1)) and (i in range((total/10 -4), total)):
                                   <li><a href="?q=${query | h}&pagination=${page}">${i+1}</a></li>
                                % elif (i in range((current_page-20)/10, current_page/10)) or (i in range(current_page/10, (current_page+30)/10)):
                                    <li><a href="?q=${query | h}&pagination=${page}">${i+1}</a></li>
                                % endif
                            % endfor
                        % if current_page < (total-10):
                            <li><a href="?q=${query | h}&pagination=${(current_page)+10}">&raquo;</a></li>
                        % else:
                            <li><a href="#">&raquo;</a></li>
                        % endif
                        <li><a href="?q=${query | h}&pagination=${total/10 * 10}">Last</a></li>
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
