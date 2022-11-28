import frappe


@frappe.whitelist()
def delete_invoices():
    for d in frappe.get_all("Sales Invoice", {"creation": [">", "2022-11-23"]}):
        frappe.delete_doc("Sales Invoice", d.name)
