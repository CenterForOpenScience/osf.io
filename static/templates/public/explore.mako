<%inherit file="base.mako"/>
<%def name="title()">Content</%def>

<%def name="javascript()">
    %if use_cdn:
    <script src="//cdnjs.cloudflare.com/ajax/libs/d3/3.2.2/d3.v3.min.js"></script>
    %else:
    <script src="/static/d3.v3.min.js"></script>
    %endif
</%def>
<%def name="content()">
<div class="row">
  <div class="span12">
    <h1>Collaborator Network for Public Projects</h1>
    <p>Projects with more than 10 connections are used to represent the connections between each of the collaborators on that project for clarity. Node radius represents total collaboration overall, while number of lines connecting to a node represent the individuals they collaborate with.</p>
    <div style="font: 10px sans-serif;margin: 0px auto 22px;clear: both;width">
      <div id='chart'></div>
    </div>
  </div>
</div>

<style>

.node {
  stroke: #fff;
  stroke-width: 1.5px;
}

.link {
  stroke: #999;
  stroke-opacity: .6;
}

</style>

%if use_cdn:
<script src="//cdnjs.cloudflare.com/ajax/libs/d3/3.2.2/d3.v3.min.js"></script>
%else:
<script src="/static/d3.v3.min.js"></script>
%endif

<script>

var margin = {top: 15, right: 20, bottom: 100, left: 40},
    margin2 = {top: 430, right: 10, bottom: 20, left: 40},
    width = 960 - margin.left - margin.right,
    height = 800 - margin.top - margin.bottom,
    height2 = 800 - margin2.top - margin2.bottom;

var color = d3.scale.category20();

var force = d3.layout.force()
    .charge(-120)
    .linkDistance(200)
    .size([width, height]);

var svg = d3.select("div#chart").append("svg")
    .attr("width", width)
    .attr("height", height);

d3.json("/static/nodes.json", function(error, graph) {
  force
      .nodes(graph.nodes)
      .links(graph.links)
      .start();

  var link = svg.selectAll("line.link")
      .data(graph.links)
    .enter().append("line")
      .attr("class", "link")
      .style("stroke-width", function(d) { return Math.sqrt(d.value); });

  var node = svg.selectAll("circle.node")
      .data(graph.nodes)
    .enter().append("circle")
      .attr("class", "node")
      .attr("r", function(d) { return d.radius; })
      .style("fill", function(d) { return color(d.group); })
      .call(force.drag);

  node.append("title")
      .text(function(d) { return d.name; });

  force.on("tick", function() {
    link.attr("x1", function(d) { return d.source.x; })
        .attr("y1", function(d) { return d.source.y; })
        .attr("x2", function(d) { return d.target.x; })
        .attr("y2", function(d) { return d.target.y; });

    node.attr("cx", function(d) { return d.x; })
        .attr("cy", function(d) { return d.y; });
  });
});

</script>
</%def>
