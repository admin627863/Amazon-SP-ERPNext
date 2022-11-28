# Copyright (c) 2022, Greycube and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import (
    now_datetime,
    add_to_date,
    get_datetime,
    time_diff_in_seconds,
)
from frappe.model.document import Document
import time
import io, json
from sp_api.api import Reports, Sales
from sp_api.base import Marketplaces, ReportType, ProcessingStatus, Granularity

from amazon_sp_erpnext.amazon_sp_erpnext.controllers.sales_invoice_controller import (
    process_mtr_file,
)


def to_amz_utc(date_str):
    return get_datetime(date_str).utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class AmazonOnDemandReport(Document):
    def validate(self):
        current_time = now_datetime()
        if not self.start_time:
            self.start_time = add_to_date(current_time, hours=-1)
        if not self.end_time:
            self.end_time = current_time

    def after_insert(self):
        frappe.enqueue_doc(
            self.doctype,
            self.name,
            "create_report",
            queue="long",
            timeout=3000,
            now=True,
        )
        frappe.db.commit()

    def create_report(self):
        """Create report in Amz. The report will be queued.
        Poll with the Report ID returned, to get report when status is DONE"""

        settings = frappe.get_doc("Amazon SP Settings", self.amazon_settings)
        credentials = settings.get_credentials()

        res = Reports(credentials=credentials, marketplace=Marketplaces.IN)

        # datetime format: "2022-10-06T20:11:24.000Z"
        # reportOptions={
        #     "aggregateByLocation": "FC",
        #     "aggregatedByTimePeriod": "MONTHLY",
        #     "eventType": "Shipments",
        # },

        data = res.create_report(
            reportType=self.report_type,
            dataStartTime=to_amz_utc(self.start_time),
            dataEndTime=to_amz_utc(self.end_time),
        )

        report_id = data.payload["reportId"]
        self.db_set("status", "IN_QUEUE")
        self.db_set("report_id", report_id)


def get_report_scheduled():
    """runs in cron to fetch reports in queue or in progress from seller central"""

    for d in frappe.get_all(
        "Amazon On Demand Report",
        filters={
            "status": [
                "not in",
                (
                    ProcessingStatus.DONE,
                    ProcessingStatus.FATAL,
                    ProcessingStatus.CANCELLED,
                ),
            ]
        },
    ):
        doc = frappe.get_doc("Amazon On Demand Report", d.name)

        settings = frappe.get_doc("Amazon SP Settings", doc.amazon_settings)
        credentials = settings.get_credentials()
        reports_api = Reports(credentials=credentials, marketplace=Marketplaces.IN)

        data = reports_api.get_report(doc.report_id)

        doc.update(
            {
                "status": data.payload.get("processingStatus"),
                "time_taken": time_diff_in_seconds(now_datetime(), doc.creation),
            }
        )
        doc.add_comment(text=json.dumps(data.payload))

        if doc.status in [ProcessingStatus.DONE]:
            buffer = io.BytesIO()
            out = reports_api.get_report_document(
                data.payload["reportDocumentId"],
                decrypt=True,
                file=buffer,
            )

            file_doc = frappe.get_doc(
                {
                    "doctype": "File",
                    "file_name": "{}_{}.csv".format(doc.report_type, doc.start_time),
                    "content": buffer.getvalue(),
                    "is_private": True,
                    "attached_to_doctype": doc.doctype,
                    "attached_to_name": doc.name,
                }
            ).insert()

            # doc.add_comment(text=file_doc.as_json())
            process_mtr_report_scheduled()

        doc.save()
        # frappe.db.commit()


def process_mtr_report_scheduled():
    """runs in a cron to process reports that are DONE"""
    for d in frappe.get_all(
        "Amazon On Demand Report",
        filters={
            "status": ProcessingStatus.DONE,
            "is_processed": 0,
        },
        fields=["name", "amazon_settings"],
    ):
        for f in frappe.db.get_all(
            "File",
            filters={
                "attached_to_doctype": "Amazon On Demand Report",
                "attached_to_name": ("in", d.name),
            },
            fields=["file_url", "name"],
            limit_page_length=1,
        ):

            process_mtr_file(f.name, d.amazon_settings, submit=False)
            frappe.db.set_value("Amazon On Demand Report", d.name, "is_processed", 1)
        frappe.db.commit()


def create_amazon_reports_scheduled():
    """Creates a report for each report_type on the hour (or as scheduled in hooks.py)"""
    for d in [
        "GET_GST_MTR_B2B_CUSTOM",
        # "GET_GST_MTR_B2C_CUSTOM",
        # "GST_MTR_STOCK_TRANSFER_REPORT",
    ]:
        for setting in frappe.get_all("Amazon SP Settings"):
            doc = frappe.get_doc(
                {"doctype": "Amazon On Demand Report", "amazon_settings": setting.name}
            )
            doc.save()
