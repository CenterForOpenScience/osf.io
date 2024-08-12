import csv
import io

from django.http import Http404

from rest_framework import renderers


# put these fields first, then sort the rest alphabetically
PRIORITIZED_FIELDNAMES = {"report_date", "report_yearmonth", "timestamp"}


def csv_fieldname_sortkey(fieldname):
    return (
        (fieldname not in PRIORITIZED_FIELDNAMES),  # False ordered before True
        fieldname,
    )


def get_nested_keys(report_attrs):
    for attr_key in sorted(report_attrs.keys(), key=csv_fieldname_sortkey):
        attr_value = report_attrs[attr_key]
        if isinstance(attr_value, dict):
            for subkey in get_nested_keys(attr_value):
                yield f"{attr_key}.{subkey}"
        else:
            yield attr_key


def get_key_value(nested_key, report_attrs):
    (key, _, next_nested_key) = nested_key.partition(".")
    attr_value = report_attrs.get(key, {})
    return (
        get_key_value(next_nested_key, attr_value)
        if next_nested_key
        else attr_value
    )


def get_csv_row(keys_list, report_attrs):
    return [get_key_value(key, report_attrs) for key in keys_list]


class MetricsReportsCsvRenderer(renderers.BaseRenderer):
    media_type = "text/csv"
    format = "csv"
    CSV_DIALECT = csv.excel

    def render(
        self,
        json_response,
        accepted_media_type=None,
        renderer_context=None,
    ):
        serialized_reports = (
            jsonapi_resource["attributes"]
            for jsonapi_resource in json_response["data"]
        )
        try:
            first_row = next(serialized_reports)
        except StopIteration:
            raise Http404("<h1>none found</h1>")
        csv_fieldnames = list(get_nested_keys(first_row))
        csv_filecontent = io.StringIO(newline="")
        csv_writer = csv.writer(csv_filecontent, dialect=self.CSV_DIALECT)
        csv_writer.writerow(csv_fieldnames)
        for serialized_report in (first_row, *serialized_reports):
            csv_writer.writerow(
                get_csv_row(csv_fieldnames, serialized_report),
            )
        return csv_filecontent.getvalue()


class MetricsReportsTsvRenderer(MetricsReportsCsvRenderer):
    format = "tsv"
    media_type = "text/tab-separated-values"
    CSV_DIALECT = csv.excel_tab
