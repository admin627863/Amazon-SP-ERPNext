# -*- coding: utf-8 -*-
# Copyright (c) 2022, Greycube and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_migrate(**args):
    custom_fields = {
        "Sales Invoice": [
            dict(
                fieldtype="Data",
                fieldname="amazon_order_id_cf",
                label="Amazon Order Id",
                insert_after="party_name",
                allow_on_submit=1,
            ),
            dict(
                fieldtype="Data",
                fieldname="marketplace_id_cf",
                label="Marketplace Id",
                insert_after="amazon_order_id_cf",
                allow_on_submit=1,
            ),
        ],
        "Warehouse": [
            dict(
                fieldtype="Data",
                fieldname="amazon_fba_fulfilment_center",
                label="Fulfilment Center",
                insert_after="company",
                description="""4 digit FC Code e.g. DEL1 
                https://forestshipping.com/amazon-fulfillment-center-address-in-india""",
            ),
        ],
    }

    for d in custom_fields:
        print("creating fields for %s" % d)
        print([x["label"] for x in custom_fields[d]])

    create_custom_fields(custom_fields)
    frappe.db.commit()  # to avoid implicit-commit errors
