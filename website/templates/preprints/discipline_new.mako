<%inherit file="preprints/base.mako"/>
<%def name="title()">Explore Preprints</%def>
<%def name="content()">
<%
    from framework.auth import get_user
%>



  <div class="row">

    <div class="col-md-9" role="main">
        <section id='newPreprints'>
            <h3>${discipline} Preprints</h3>
            <div id="grid">
            </div>
        </section>

    </div>
  </div><!-- /.row -->


</%def>


<%def name="javascript_bottom()">
    <script type="text/javascript">
        var data = [
            %for node in recent_preprints:
                {
                    id: '${node._id}',
                    nodeUrl: "${node.url}preprint/",
                    title: "${node.title}",
                    author: [
                        %for author in node.contributors:
                            '${author.family_name}',
                        %endfor
                    ],
                    authorUrls: [
                        %for author in node.contributors:
                            '${author.url}',
                        %endfor
                    ],
                    downloadUrl: '${node.url}osffiles/preprint.pdf/download/',
                    date: '${node.date_created.date()}'
                },
            %endfor
        ];
        $script('/static/js/preprintDisciplineExplore.js');
        $script.ready('conference', function() {
            new Meeting(data);
        })
    </script>
</%def>
