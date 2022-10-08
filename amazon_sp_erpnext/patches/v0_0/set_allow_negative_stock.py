# -*- coding: utf-8 -*-
# Copyright (c) 2022, Greycube and contributors
# For license information, please see license.txt

import frappe


def execute():
    print("Setting allow_negative_stock to 1 in Stock Settings")
    frappe.db.set_value("Stock Settings", None, "allow_negative_stock", 1)
