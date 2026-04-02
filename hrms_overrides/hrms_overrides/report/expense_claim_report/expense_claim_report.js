// Copyright (c) 2025, Your Company and contributors
// For license information, please see license.txt

frappe.query_reports["Expense Claim Report"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			get_query: function () {
				return {
					filters: {
						company: frappe.query_report.get_filter_value("company"),
					},
				};
			},
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
			get_query: function () {
				return {
					filters: {
						company: frappe.query_report.get_filter_value("company"),
					},
				};
			},
		},
		{
			fieldname: "expense_type",
			label: __("Expense Claim Type"),
			fieldtype: "Link",
			options: "Expense Claim Type",
		},
		{
			fieldname: "from_date",
			label: __("Posting Date From"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("Posting Date To"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "expense_from_date",
			label: __("Expense Date From"),
			fieldtype: "Date",
		},
		{
			fieldname: "expense_to_date",
			label: __("Expense Date To"),
			fieldtype: "Date",
		},
		{
			fieldname: "approval_status",
			label: __("Approval Status"),
			fieldtype: "Select",
			options: "\nDraft\nApproved\nRejected",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "pending_amount" && data && data.pending_amount > 0) {
			value = `<span style="color: #e03e2d; font-weight: bold;">${value}</span>`;
		}

		if (column.fieldname === "approval_status") {
			if (data && data.approval_status === "Approved") {
				value = `<span class="indicator-pill green">${data.approval_status}</span>`;
			} else if (data && data.approval_status === "Rejected") {
				value = `<span class="indicator-pill red">${data.approval_status}</span>`;
			} else if (data && data.approval_status === "Draft") {
				value = `<span class="indicator-pill yellow">${data.approval_status}</span>`;
			}
		}

		if (column.fieldname === "status") {
			if (data && data.status === "Paid") {
				value = `<span class="indicator-pill green">${data.status}</span>`;
			} else if (data && data.status === "Unpaid") {
				value = `<span class="indicator-pill orange">${data.status}</span>`;
			}
		}

		return value;
	},

	onload: function (report) {
		// Add custom Export button
		report.page.add_inner_button(__("Export to Excel"), function () {
			frappe.query_report.export_report("Excel");
		});
	},
};