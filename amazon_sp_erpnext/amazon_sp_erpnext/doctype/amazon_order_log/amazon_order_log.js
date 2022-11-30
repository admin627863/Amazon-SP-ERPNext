// Copyright (c) 2022, Greycube and contributors
// For license information, please see license.txt

frappe.ui.form.on("Amazon Order Log", {
  refresh: function (frm) {
    frm.set_value(
      "amazon_order_json",
      JSON.stringify(JSON.parse(frm.doc.amazon_order_json || "{}"), null, 4)
    );

    // frm.add_custom_button(__("Process MTR File"), function () {

    // });
  },
});
