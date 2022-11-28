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
        "Item tax Template": [
            dict(
                label="Amazon MTR Tax Column",
                fieldname="amazon_mtr_tax_column_cf",
                fieldtype="Select",
                options="\nIn State\nOut State",
                insert_after="disabled",
                in_list_view=1,
                in_standard_filter=1,
            ),
            dict(
                label="Amazon MTR Tax Rate",
                fieldname="amazon_mtr_tax_rate_cf",
                fieldtype="Float",
                insert_after="amazon_mtr_tax_column_cf",
                in_list_view=1,
                in_standard_filter=1,
                description="if GST is 5% , put Igst =0.05 , Sgst =0.025",
            ),
        ],
    }

    for d in custom_fields:
        print("creating fields for %s" % d)
        print([x["label"] for x in custom_fields[d]])

    create_custom_fields(custom_fields)
    frappe.db.commit()  # to avoid implicit-commit errors
