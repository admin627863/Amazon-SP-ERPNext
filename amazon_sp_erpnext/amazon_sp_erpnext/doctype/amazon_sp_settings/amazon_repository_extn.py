# -*- coding: utf-8 -*-
# Copyright (c) 2022, Greycube and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from amazon_sp_erpnext.amazon_sp_erpnext.doctype.amazon_sp_settings.amazon_repository import (
    AmazonRepository,
)
import json
import dateutil
from frappe.utils import add_days, today
from datetime import datetime
from frappe.model.naming import get_default_naming_series

logger = frappe.logger("amazon_sp_erpnext", allow_site=frappe.local.site)


class AmazonRepositoryExtn(AmazonRepository):
    def get_orders(self, created_after=None):
        return self._get_orders(created_after)

    def _get_orders(self, created_after):
        """
        Get Orders from Amazom SP SPI and create log entry for each order."""

        if not created_after:
            created_after = frappe.db.get_value(
                "Amazon SP Settings", self.amz_setting.name, "after_date"
            )
            created_after = datetime.combine(
                created_after, datetime.min.time()
            ).isoformat()

        orders = self.get_orders_instance()
        order_statuses = [
            "Shipped",
            # "PendingAvailability",
            # "Pending",
            # "Unshipped",
            # "PartiallyShipped",
            # "InvoiceUnconfirmed",
            # "Canceled",
            # "Unfulfillable",
        ]
        fulfillment_channels = [
            "FBA",  # "SellerFulfilled"
        ]

        orders_payload = self.call_sp_api_method(
            sp_api_method=orders.get_orders,
            created_after=created_after,
            order_statuses=order_statuses,
            fulfillment_channels=fulfillment_channels,
            max_results=50,
        )

        amazon_orders = []

        # frappe.log_error("Amazon SP API getOrders Response", orders_payload)
        logger.debug(orders_payload)

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
                max_results=50,
            )
            logger.debug(orders_payload)

        return amazon_orders

    def get_item_code(self, order_item):
        item_code_key = self.amz_setting.amazon_item_field_in_erpnext or "ASIN"
        item_code = order_item.get(item_code_key)

        if item_code:
            if frappe.db.exists({"doctype": "Item", "item_code": item_code}):
                return item_code
        else:
            raise KeyError(item_code_key)

    def get_order_items(self, order_id):
        orders = self.get_orders_instance()
        order_items_payload = self.call_sp_api_method(
            sp_api_method=orders.get_order_items, order_id=order_id
        )
        logger.debug(order_items_payload)

        final_order_items = []
        warehouse = self.amz_setting.warehouse

        while True:

            order_items_list = order_items_payload.get("OrderItems")
            next_token = order_items_payload.get("NextToken")

            for order_item in order_items_list:
                price = order_item.get("ItemPrice", {}).get("Amount", 0)

                item_details = frappe.db.get_value(
                    "Item",
                    self.get_item_code(order_item),
                    ["item_code", "item_name", "description"],
                    as_dict=True,
                )

                final_order_items.append(
                    {
                        "item_code": item_details.item_code,
                        "item_name": item_details.item_name,
                        "description": item_details.description,
                        "rate": price,
                        "qty": order_item.get("QuantityOrdered"),
                        "stock_uom": "Nos",
                        "warehouse": warehouse,
                        "conversion_factor": "1.0",
                    }
                )

            if not next_token:
                break

            order_items_payload = self.call_sp_api_method(
                sp_api_method=orders.get_order_items,
                order_id=order_id,
                next_token=next_token,
            )
            logger.debug(order_items_payload)

        return final_order_items

    def create_sales_invoice(self, amazon_order, submit=False):

        order_id = amazon_order.get("AmazonOrderId")
        # check for duplicate
        if frappe.db.exists("Sales Invoice", {"amazon_order_id_cf": order_id}):
            pass
            # return

        customer_name = self.create_customer(amazon_order)
        self.create_address(amazon_order, customer_name)
        items = [d for d in self.get_order_items(order_id) if d.get("qty")]

        if not items:
            return

        delivery_date = dateutil.parser.parse(
            amazon_order.get("LatestShipDate")
        ).strftime("%Y-%m-%d")

        transaction_date = dateutil.parser.parse(
            amazon_order.get("PurchaseDate")
        ).strftime("%Y-%m-%d")

        naming_series = frappe.db.get_value(
            "Amazon SP Settings", self.amz_setting.name, "sales_invoice_series"
        ) or get_default_naming_series("Sales Invoice")

        sales_invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "naming_series": naming_series,
                "amazon_order_id": order_id,
                "marketplace_id": amazon_order.get("MarketplaceId"),
                "customer": customer_name,
                "posting_date": transaction_date,
                "due_date": today(),  # order already paid and shipped in amazon
                "items": items,
                "company": self.amz_setting.company,
            }
        )

        taxes_and_charges = self.amz_setting.taxes_charges

        if taxes_and_charges:
            charges_and_fees = self.get_charges_and_fees(order_id)
            for charge in charges_and_fees.get("charges"):
                sales_invoice.append("taxes", charge)
            for fee in charges_and_fees.get("fees"):
                sales_invoice.append("taxes", fee)

        sales_invoice.insert(ignore_permissions=True)
        if submit:
            sales_invoice.submit()

        return sales_invoice.name


def make_order_log(created_after=None):
    """Scheduled Job to run every 5 minutes or so to sync amazon orders"""
    # import ast

    # response = ast.literal_eval(frappe.get_doc("Error Log", "373eaa88b2").get("error"))
    # orders = response.get("Orders") or []

    amz = AmazonRepositoryExtn("CARMEL ORGANICS PRIVATE LIMITED")
    orders = amz._get_orders(created_after)
    for d in orders:
        frappe.get_doc(
            {
                "doctype": "Amazon Order Log",
                "amazon_order_id": d.get("AmazonOrderId"),
                "amazon_order_json": json.dumps(d),
            }
        ).insert()
