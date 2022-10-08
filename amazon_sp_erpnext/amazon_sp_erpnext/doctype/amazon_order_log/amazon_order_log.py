# Copyright (c) 2022, Greycube and contributors
# For license information, please see license.txt

import frappe
from amazon_sp_erpnext.amazon_sp_erpnext.doctype.amazon_sp_settings.amazon_repository_extn import (
    AmazonRepositoryExtn,
)
from frappe.model.document import Document
import json


class AmazonOrderLog(Document):
    def on_update(self):
        if not self.status == "Error" and not self.sales_invoice:
            amazon_repository = AmazonRepositoryExtn("CARMEL ORGANICS PRIVATE LIMITED")
            si_doc = amazon_repository.create_sales_invoice(
                json.loads(self.amazon_order_json), submit=False
            )
            self.db_set("status", "Processed")
            self.db_set("sales_invoice", si_doc)

            print("Created sales Invoice %s" % si_doc)
