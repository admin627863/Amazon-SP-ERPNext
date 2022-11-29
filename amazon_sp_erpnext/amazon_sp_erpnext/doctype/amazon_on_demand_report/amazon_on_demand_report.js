// Copyright (c) 2022, Greycube and contributors
// For license information, please see license.txt

frappe.ui.form.on("Amazon On Demand Report", {
  refresh: function (frm) {
    if (!frm.doc.__islocal) {
      frm.add_custom_button(
        __("Process MTR File"),
        function () {
          frappe.call({
            method:
              "amazon_sp_erpnext.amazon_sp_erpnext.doctype.amazon_on_demand_report.amazon_on_demand_report.process_mtr_report_scheduled",
            args: {
              name: frm.doc.name,
              amazon_settings: frm.doc.amazon_settings,
            },
          });
        },
        __("Action")
      );
    }
  },
});
