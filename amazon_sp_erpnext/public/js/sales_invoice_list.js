frappe.listview_settings["Sales Invoice"] = {
  onload(listview) {
    listview.page.add_inner_button("Delete Invoices", function () {
      frappe.call({
        method: "amazon_sp_erpnext.amazon_sp_erpnext.delete_invoices",
      });
    });
  },
};
