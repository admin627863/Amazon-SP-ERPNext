# Copyright (c) 2022, Greycube and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from amazon_sp_erpnext.amazon_sp_erpnext.controllers.mtr import MTR_COLUMNS as mcols


class AmazonSPCommonSettings(Document):
    def get_tax_category(self, order):
        return (
            self.in_state_tax_category
            if order.get(mcols.SGST_RATE)
            else self.out_state_tax_category
            if order.get(mcols.IGST_RATE)
            else ""
        )

    def get_gst_category(self, order):
        return (
            order.get(mcols.CUSTOMER_BILL_TO_GSTID)
            and "Registered Regular"
            or "Unregistered"
        )

    def get_item_tax_template(self, order):
        item_tax_template = None

        if order.get(mcols.SGST_RATE):
            item_tax_template = frappe.db.get_value(
                "Item Tax Template",
                filters={
                    "amazon_mtr_tax_column_cf": "In State",
                    "amazon_mtr_tax_rate_cf": order.get(mcols.SGST_RATE),
                },
            )
        elif order.get(mcols.IGST_RATE):
            item_tax_template = frappe.db.get_value(
                "Item Tax Template",
                filters={
                    "amazon_mtr_tax_column_cf": "Out State",
                    "amazon_mtr_tax_rate_cf": order.get(mcols.IGST_RATE),
                },
            )

        return item_tax_template
