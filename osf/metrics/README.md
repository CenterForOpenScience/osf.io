# osf.metrics

`osf.metrics` allows storing anonymized usage data and defining periodic
reports based on that data.

the data model was built to be [COUNTER](https://cop5.projectcounter.org/en/5.0.2/)-compliant,
but note that the COUNTER_SUSHI api has not yet been implemented atop.

## data model
usage data and periodic reports are both stored in elasticsearch using
`elasticsearch-dsl`-based data models.

each "usage" is represented as `CountedAuthUsage` -- see `osf.metrics.counted_usage`
for field definitions with comments mapping fields to concepts in the COUNTER spec.

each periodic report is represented as a subclass of `DailyReport` or `MonthlyReport`
(see `osf.metrics.reports`) and has a "reporter" (see `osf.metrics.reporters`) that
is invoked periodically to report.

## api
note: the `osf.metrics` api is subject to change, is supported only for use within OSF
(use at your own risk!), and may someday be mostly replaced by a
[COUNTER_SUSHI api](https://cop5.projectcounter.org/en/5.0.2/08-sushi/index.html).

the `osf.metrics` api is currently located under the osf api namespace `/_/metrics/`,
and contains a variety of special-purpose endpoints (see `api.metrics.urls` for a full accounting).

endpoints of interest for new development (all starting with `/_/metrics/`):
- `events/counted_usage/`: POST-only, for recording a usage
- `reports/`: GET list of available report types
  - `reports/<report-id>/recent`: GET list of recent reports
- `query/`: namespace for views that query usage data on demand (only for statically defined, cheap queries)

## how to

### add a new monthly report
- add a `MonthlyReport` subclass (in `osf.metrics.reports`) with the fields you want
- add a `MonthlyReporter` subclass (in a module under `osf.metrics.reporters`)
  that knows how to build your report
- to have your reporter run automatically, add it to `osf.metrics.reporters.MONTHLY_REPORTERS`
- to have your report available in the api, add it to `api.metrics.views.VIEWABLE_REPORTS`
