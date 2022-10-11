// Copyright (c) 2022, Greycube and contributors
// For license information, please see license.txt

frappe.ui.form.on("Amazon SP Settings", {
  fetch_report: function (frm) {
    frappe.call({
      method:
        "amazon_sp_erpnext.amazon_sp_erpnext.controllers.report_controller.fetch_report",
      args: {
        report_type: frm.doc.report_type,
        amz_settings_name: frm.doc.name,
      },
      callback: () => {
        console.log("file created");
      },
    });
  },
});
