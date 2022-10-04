# -*- coding: utf-8 -*-
# Copyright (c) 2022, Greycube and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from amazon_sp_erpnext.amazon_sp_erpnext.doctype.amazon_sp_settings.amazon_repository import (
    AmazonRepository,
)


class AmazonRepositoryExtn(AmazonRepository):
    def get_orders(self, created_after):
        """
        Get Orders from Amazom SP SPI and create log entry for each order."""
        orders = self.get_orders_instance()
        order_statuses = [
            "PendingAvailability",
            "Pending",
            "Unshipped",
            "PartiallyShipped",
            "Shipped",
            "InvoiceUnconfirmed",
            "Canceled",
            "Unfulfillable",
        ]
        fulfillment_channels = ["FBA", "SellerFulfilled"]

        orders_payload = self.call_sp_api_method(
            sp_api_method=orders.get_orders,
            created_after=created_after,
            order_statuses=order_statuses,
            fulfillment_channels=fulfillment_channels,
            max_results=50,
        )

        amazon_orders = []

        while True:

            orders_list = orders_payload.get("Orders")
            next_token = orders_payload.get("NextToken")

            if not orders_list or len(orders_list) == 0:
                break

            amazon_orders.extend(orders_list)

            if not next_token:
                break

            orders_payload = self.call_sp_api_method(
                sp_api_method=orders.get_orders,
                created_after=created_after,
                next_token=next_token,
            )
        for d in amazon_orders:
            frappe.get_doc({"doctype": "Amazon Log"}).insert()

    def create_invoices(self):
        pass
