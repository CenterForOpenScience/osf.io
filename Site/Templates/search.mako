<%inherit file="contentContainer.mako" />
<%
    import framework
    import re
%>
<style>
    .nested
        {
            padding-left: 25px;
        }
</style>
<section id="Search" xmlns="http://www.w3.org/1999/html">
    <div class="page-header">
        <h1>Search <small> for ${query} ${total} result${'s' if total is not 1 else ''} in ${time} seconds</small></h1>
        % if spellcheck:
           <h4> Did you mean <a href='/search/?q=${spellcheck}'> ${spellcheck} </a>? </h4>
        % endif
    </div>
</section>
<div class="row">
    <div class="span2">
        <h3>Everything</h3>
        <h3>Projects</h3>
        <h3>Nodes</h3>
        <h3>Files</h3>
    </div>
    <div class="span10">
            % if results:
                % for result in results:
                        <div class="title">
                            <h4> <a href=${result['url']}>${result['title']}</a> </h4>
                        </div>
                        <div class="contributors">
                            % for contributor, url in zip(result['contributors'], result['contributors_url']):
                                <a href=${url}>${contributor}</a>
                            % endfor
                        </div>
                        <div class="highlight">
                            % if result['highlight'] is not None:
                                ${result['highlight']}
                            % endif
                        </div>
                        <div class="nested">
                                % if result['nest']:
                                    % for key in result['nest'].iterkeys():
                                        <div class="sub_title">
                                            <a href=${result['nest'][key]['url']}>${result['nest'][key]['title']}</a>
                                        </div>
                                        % if result['nest'][key]['highlight'] is not None:
                                        <div class="highlight">
                                            % for highlight in result['nest'][key]['highlight']:
                                                ${highlight}
                                            % endfor
                                        </div>
                                         % endif
                                        % if result['nest'][key]['tags'] is not None:
                                            % for tag in result['nest'][key]['tags']:
                                                <a href=/search/?q=${tag}><button class="btn btn-info btn-mini" type="submit"> ${tag} </button> </a>
                                            % endfor
                                        % endif
                                    % endfor
                                % endif

                        </div>
                        <div class="tags">
                            % if 'tags' in result:
                                % for tag in result['tags']:
                                <a href=/search/?q=${tag}><button class="btn btn-info btn-mini" type="submit"> ${tag} </button> </a>
                                % endfor
                            % endif
                        </div>
                % endfor
            % else:
                No results found. <br />
                <br />
                Note: Improvements are currently being made on the search engine, so it might have been reasonable to find something based upon your search terms. Feel free to <a href="mailto:jspies@virginia.edu">send me</a> the terms you used and what you expected to find, and I'll use that information to potentially tune the search algorithm. Thanks!
            %endif
    </div>
</div>