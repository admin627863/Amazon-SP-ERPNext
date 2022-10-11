# Copyright (c) 2022, Greycube and contributors
# For license information, please see license.txt

import frappe
from sp_api.api import Reports, Sales
from sp_api.base import Marketplaces, ReportType, ProcessingStatus, Granularity
import time
import io
from datetime import datetime
from amazon_sp_erpnext.amazon_sp_erpnext.doctype.amazon_sp_settings.amazon_repository import (
    AmazonRepository,
)


@frappe.whitelist()
def fetch_report(report_type, amz_settings_name):
    credentials = frappe.get_doc(
        "Amazon SP Settings", amz_settings_name
    ).get_credentials()
    res = Reports(credentials=credentials, marketplace=Marketplaces.IN)

    data = res.create_report(
        reportType=report_type,
        dataStartTime="2022-10-06T20:11:24.000Z",
        dataEndTime="2022-10-10T03:56:02.244Z",
        reportOptions={
            "aggregateByLocation": "FC",
            "aggregatedByTimePeriod": "MONTHLY",
            "eventType": "Shipments",
        },
    )

    report_id = data.payload["reportId"]
    data = res.get_report(report_id)

    while data.payload.get("processingStatus") not in [
        ProcessingStatus.DONE,
        ProcessingStatus.FATAL,
        ProcessingStatus.CANCELLED,
    ]:
        print(data.payload)
        print("Sleeping...")
        time.sleep(5)
        data = res.get_report(report_id)

    if data.payload.get("processingStatus") in [
        ProcessingStatus.FATAL,
        ProcessingStatus.CANCELLED,
    ]:
        print("Report failed!")
        frappe.throw(data.payload)
    else:
        print("Success:")
        print(data.payload)

        report = io.BytesIO()
        res.get_report_document(
            data.payload["reportDocumentId"],
            decrypt=True,
            file=report,
        )

        frappe.get_doc(
            {
                "doctype": "File",
                "file_name": f"{report_type}_response_{datetime.now()}.csv",
                "content": report.getvalue(),
                "is_private": True,
            }
        ).insert()

        frappe.db.commit()
