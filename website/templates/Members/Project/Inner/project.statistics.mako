<%inherit file="project.view.mako" />
<%
    import website.settings
    import framework.analytics as analytics
    if node:
        counters = analytics.get_day_total_list('node:{0}'.format(node._primary_key))
    else:
        counters = analytics.get_day_total_list('node:{0}'.format(project._primary_key))

    csv = "date,price\\n"
    for i in counters:
      csv+= "{0},{1}\\n".format(i[0], i[1])
%>

<div class="row">
	<div class="span12">
    <h1>Visits Per Day</h1>
		<div style="font: 10px sans-serif;margin: 0px auto 22px;clear: both;width">
			<div id='chart'></div>
		</div>
	</div>
</div>

##<script type="text/javascript" src="/static/protovis.min.js"></script>
##<script type="text/javascript" src="/static/timeline.js"></script>
##<script type="text/javascript+protovis">
##
##var data = [
##%for i in range(len(dates)):
##  {
##    time: new Date('${dates[i]}'),
##    count: ${total[i]}
##  },
##%endfor
##]


%if website.settings.use_cdn_for_client_libs:
<script src="//cdnjs.cloudflare.com/ajax/libs/d3/2.10.0/d3.v2.min.js"></script>
%else:
<script src="/static/d3.v2.js"></script>
%endif
<style>

svg {
  font: 10px sans-serif;
}

path {
  fill: steelblue;
}

.axis path, .axis line {
  fill: none;
  stroke: #000;
  shape-rendering: crispEdges;
}

.brush .extent {
  stroke: #fff;
  fill-opacity: .125;
  shape-rendering: crispEdges;
}
</style>

<script>

var margin = {top: 15, right: 20, bottom: 100, left: 40},
    margin2 = {top: 430, right: 10, bottom: 20, left: 40},
    width = 960 - margin.left - margin.right,
    height = 500 - margin.top - margin.bottom,
    height2 = 500 - margin2.top - margin2.bottom;

var formatDate = d3.time.format("%Y/%m/%d");

var x = d3.time.scale().range([0, width]),
    x2 = d3.time.scale().range([0, width]),
    y = d3.scale.linear().range([height, 0]),
    y2 = d3.scale.linear().range([height2, 0]);

var xAxis = d3.svg.axis().scale(x).orient("bottom"),
    xAxis2 = d3.svg.axis().scale(x2).orient("bottom"),
    yAxis = d3.svg.axis().scale(y).orient("left");

var brush = d3.svg.brush()
    .x(x2)
    .on("brush", brush);

var area = d3.svg.area()
    .interpolate("monotone")
    .x(function(d) { return x(d.date); })
    .y0(height)
    .y1(function(d) { return y(d.price); });

var area2 = d3.svg.area()
    .interpolate("monotone")
    .x(function(d) { return x2(d.date); })
    .y0(height2)
    .y1(function(d) { return y2(d.price); });

var svg = d3.select("div#chart").append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom);

svg.append("defs").append("clipPath")
    .attr("id", "clip")
  .append("rect")
    .attr("width", width)
    .attr("height", height);

var focus = svg.append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

var context = svg.append("g")
    .attr("transform", "translate(" + margin2.left + "," + margin2.top + ")");

data = d3.csv.parse("${csv}");

data.forEach(function(d) {
    d.date = formatDate.parse(d.date);
    d.price = +d.price;
  });

  x.domain(d3.extent(data.map(function(d) { return d.date; })));
  y.domain([0, d3.max(data.map(function(d) { return d.price; }))]);
  x2.domain(x.domain());
  y2.domain(y.domain());

  focus.append("path")
      .data([data])
      .attr("clip-path", "url(#clip)")
      .attr("d", area);

  focus.append("g")
      .attr("class", "x axis")
      .attr("transform", "translate(0," + height + ")")
      .call(xAxis);

  focus.append("g")
      .attr("class", "y axis")
      .call(yAxis);

  context.append("path")
      .data([data])
      .attr("d", area2);

  context.append("g")
      .attr("class", "x axis")
      .attr("transform", "translate(0," + height2 + ")")
      .call(xAxis2);

  context.append("g")
      .attr("class", "x brush")
      .call(brush)
    .selectAll("rect")
      .attr("y", -6)
      .attr("height", height2 + 7);

function brush() {
  x.domain(brush.empty() ? x2.domain() : brush.extent());
  focus.select("path").attr("d", area);
  focus.select(".x.axis").call(xAxis);
}

</script>

##Timeline('timeline-chart').data(data).draw();
##</script>
##<link href='/static/d3/css/d3.tsline.css' media='screen' rel='stylesheet' type='text/css'>
##<script src="/static/d3/js/d3.js"></script>
##<script src="/static/d3/js/d3.time.js"></script>
##<script src="/static/d3/js/d3.tsline.js"></script>
##<script>
##      //<![CDATA[
##        // make chart object
##        var chart = new d3_tsline("#chart");
##        
##        // override parse_date function to handle our data's date format
##        chart.parse_date = d3.time.format("%Y/%m/%d").parse;
##        chart.parse_val = function(v) {
##            return parseInt(v)
##        }
##        // add some metadata about the series
##        chart.series = {
##            "aapl" : {
##                "name"   : "AAPL",
##                "active" : true
##            }
##        };
##        chart.ref_series="aapl";
##        chart.view_span = 120;
##        // fetch data and draw the chart
##        var data = [
##        %for i,total in enumerate(total):
##        	["${dates[i]}", ${total}],
##        %endfor
##        ];
##        chart.setSeriesData("aapl",data);
##        chart.render();
##      //]]>
##    </script>##