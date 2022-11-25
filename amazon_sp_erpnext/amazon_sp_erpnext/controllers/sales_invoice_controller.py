# Copyright (c) 2022, Greycube and contributors
# For license information, please see license.txt

import frappe
import pandas as pd
import io
import dateutil
from frappe.model.naming import get_default_naming_series
from frappe.utils import today
from amazon_sp_erpnext.amazon_sp_erpnext.controllers.mtr import MTR_COLUMNS as mcols


def amz_datetime_to_date(amz_date):
    return dateutil.parser.parse(amz_date).strftime("%Y-%m-%d")


def get_naming_series(amz_setting):
    return amz_setting.sales_invoice_series or get_default_naming_series(
        "Sales Invoice"
    )


def get_b2c_customer():
    return frappe.get_cached_value(
        "Amazon SP Common Settings", None, "amazon_customer_for_b2c"
    )


def get_warehouse(fc_name, company):
    warehouse = frappe.db.get_all(
        "Warehouse",
        pluck="name",
        filters={"amazon_fba_fulfilment_center": fc_name, "company": company},
        limit=1,
    )
    return warehouse and warehouse[0][0] or None


def make_contacts(data):
    # create contacts for B2C customers
    amazon_customer_for_b2c = get_b2c_customer()

    contacts = frappe.db.get_all(
        "Dynamic Link",
        filters={
            "link_doctype": "Customer",
            "link_name": amazon_customer_for_b2c,
            "parenttype": "Contact",
        },
        pluck="parent",
    )

    for d in data:
        if f"Buyer-{d}-{amazon_customer_for_b2c}" in contacts:
            return
        print("creating: ", d)
        frappe.get_doc(
            {
                "doctype": "Contact",
                "first_name": f"Buyer-{d}",
                "links": [
                    {
                        "doctype": "Dynamic Link",
                        "link_doctype": "Customer",
                        "link_name": amazon_customer_for_b2c,
                    },
                ],
            }
        ).insert()


def make_address(df):
    nowtime = frappe.utils.now()
    df_copy = (
        df[
            [
                "Order Id",
                "Ship To City",
                "Ship To State",
                "Ship To Country",
                "Ship To Postal Code",
            ]
        ]
        .copy()
        .rename(
            columns={
                "Order Id": "order-id",
                "Ship To City": "city",
                "Ship To State": "state",
                "Ship To Country": "country",
                "Ship To Postal Code": "pincode",
            }
        )
    )

    df_copy.drop_duplicates(inplace=True, ignore_index=True)
    df_copy = df_copy.assign(
        name=df_copy["order-id"] + " - Shipping",
        creation=nowtime,
        modified=nowtime,
        modified_by="Administrator",
        address_type="Shipping",
        address_line1="Not Provided",
        country=lambda x: "India" if x["country"].str == "IN" else x["country"],
    )

    fields = [
        "name",
        "creation",
        "modified",
        "modified_by",
        "address_type",
        "address_line1",
        "city",
        "state",
        "pincode",
        "country",
    ]

    data = df_copy[fields].values.tolist()
    frappe.db.bulk_insert(
        "Address",
        fields=fields,
        values=data,
        ignore_duplicates=True,
    )

    frappe.db.commit()


def make_b2b_customer_contact(amz_setting):
    # create B2B Customer
    args = {}

    amz_setting = frappe.get_cached_doc("Amazon SP Setting", amz_setting)

    new_customer = frappe.new_doc(
        {
            "doctype": "Customer",
            "customer_name": args.get("Buyer Name"),
            "customer_group": amz_setting.customer_group,
            "territory": amz_setting.territory,
            "customer_type": amz_setting.customer_type,
        }
    )
    new_customer.save()

    frappe.get_doc(
        {
            "doctype": "Contact",
            "first_name": args.get("Buyer Name"),
            "links": [
                {
                    "doctype": "Dynamic Link",
                    "link_doctype": "Customer",
                    "link_name": new_customer.name,
                },
            ],
        }
    ).insert()
    return new_customer.name


def get_mtr_df(file_name=None, amz_setting=None):
    amz_setting = frappe.get_cached_doc("Amazon SP Settings", amz_setting)
    is_b2b, df, items = False, None, []

    if not file_name:
        for d in frappe.get_all(
            "File",
            {"file_name": ["like", "GST_MTR_B2%"]},
            order_by="creation desc",
            limit=1,
        ):
            file_name = d.name

    if not file_name:
        frappe.throw("No MTR `file to process.")

    content = frappe.get_doc("File", file_name).get_content()
    df = pd.read_csv(
        io.StringIO(content),
        # sep="\t",
    )
    return df[(df[mcols.TRANSACTION_TYPE] == "Shipment") & (df[mcols.QUANTITY] > 0)]


def process_mtr_file(file_name=None, amz_setting=None, submit=True):
    df = get_mtr_df(file_name, amz_setting)
    amz_setting = frappe.get_cached_doc("Amazon SP Settings", amz_setting)

    is_b2b = mcols.CUSTOMER_BILL_TO_GSTID in df.columns

    if not is_b2b:
        contacts = df[mcols.ORDER_ID].drop_duplicates().to_list()
        make_contacts(contacts)

    make_address(df)

    customer_name = get_b2c_customer()

    for order_id in set(df[mcols.ORDER_ID].values.tolist()):
        print("creating sales invoice: %s" % (order_id))

        df_copy = df[df[mcols.ORDER_ID] == order_id]
        if not len(df_copy):
            return

        lines = df_copy.to_dict("records")
        order = lines[0]

        order_id = order.get(mcols.ORDER_ID)
        # check for duplicate
        if frappe.db.exists("Sales Invoice", {"amazon_order_id_cf": order_id}):
            return

        if is_b2b:
            customer_name = make_b2b_customer_contact(order)

        posting_date = amz_datetime_to_date(order.get(mcols.INVOICE_DATE))

        args = {
            "doctype": "Sales Invoice",
            "naming_series": get_naming_series(amz_setting),
            "company": amz_setting.company,
            "amazon_order_id_cf": order_id,
            "customer": customer_name,
            "posting_date": posting_date,
            "due_date": posting_date,  # order already paid and shipped in amazon
            "debit_to": "default_receivable_account",
            "items": [],
        }
        sales_invoice = frappe.get_doc(args)

        for d in lines:
            if not d.get(mcols.QUANTITY):
                continue

            item_details = frappe.db.get_value(
                "Item",
                d.get(mcols.SKU),
                ["item_code", "item_name", "description"],
                as_dict=True,
            )
            sales_invoice.append(
                "items",
                {
                    "item_code": item_details.item_code,
                    "item_name": item_details.item_name,
                    "description": item_details.description,
                    "base_net_total": d.get(mcols.TAX_EXCLUSIVE_GROSS),
                    "base_grand_total": d.get(mcols.INVOICE_AMOUNT),
                    "grand_total": d.get(mcols.INVOICE_AMOUNT),
                    "rate": 0,
                    "qty": d.get(mcols.QUANTITY) or 0,
                    "stock_uom": "Nos",
                    "conversion_factor": "1.0",
                    "warehouse": get_warehouse(
                        d.get(mcols.WAREHOUSE_ID), amz_setting.company
                    ),
                },
            )

        # Handle Taxes and Shipping Item
        # taxes_and_charges = self.amz_setting.taxes_charges

        # if taxes_and_charges:
        #     charges_and_fees = self.get_charges_and_fees(order_id)
        #     for charge in charges_and_fees.get("charges"):
        #         sales_invoice.append("taxes", charge)
        #     for fee in charges_and_fees.get("fees"):
        #         sales_invoice.append("taxes", fee)

        sales_invoice.insert(ignore_permissions=True)

        if submit:
            sales_invoice.submit()

        print("\n" * 5, "Created invoice: ", sales_invoice.name)
        # break
