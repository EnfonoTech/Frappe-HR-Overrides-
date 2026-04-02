# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)
    summary = get_report_summary(data, filters)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {
            "label": _("Expense Claim"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Expense Claim",
            "width": 160,
        },
        {
            "label": _("Employee"),
            "fieldname": "employee",
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120,
        },
        {
            "label": _("Employee Name"),
            "fieldname": "employee_name",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 130,
        },
        {
            "label": _("Posting Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": _("Expense Claim Type"),
            "fieldname": "expense_type",
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "label": _("Description"),
            "fieldname": "description",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Expense Date"),
            "fieldname": "expense_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": _("Sanctioned Amount"),
            "fieldname": "sanctioned_amount",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 140,
        },
        {
            "label": _("Total Claimed Amount"),
            "fieldname": "total_claimed_amount",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150,
        },
        {
            "label": _("Total Sanctioned Amount"),
            "fieldname": "total_sanctioned_amount",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 170,
        },
        {
            "label": _("Amount Paid"),
            "fieldname": "total_amount_reimbursed",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130,
        },
        {
            "label": _("Pending Amount"),
            "fieldname": "pending_amount",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 130,
        },
        {
            "label": _("Approval Status"),
            "fieldname": "approval_status",
            "fieldtype": "Select",
            "width": 130,
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 130,
        },
        # Hidden helper column — currency resolved from tabCompany.default_currency
        # because tabExpense Claim in ERPNext v15 does NOT have a currency field.
        {
            "label": _("Currency"),
            "fieldname": "currency",
            "fieldtype": "Data",
            "hidden": 1,
            "width": 80,
        },
    ]


def get_data(filters):
    conditions, detail_conditions = get_conditions(filters)

    # NOTE: tabExpense Claim in ERPNext v15 does NOT have a `currency` column.
    # We LEFT JOIN tabCompany to get default_currency for the currency columns.
    data = frappe.db.sql(
        """
        SELECT
            ec.name,
            ec.employee,
            ec.employee_name,
            ec.department,
            ec.posting_date,
            ecd.expense_type,
            ecd.description,
            ecd.expense_date,
            ecd.sanctioned_amount,
            ec.total_claimed_amount,
            ec.total_sanctioned_amount,
            ec.total_amount_reimbursed,
            (ec.total_sanctioned_amount - IFNULL(ec.total_amount_reimbursed, 0)) AS pending_amount,
            ec.approval_status,
            ec.status,
            ec.company,
            IFNULL(c.default_currency, 'INR') AS currency
        FROM
            `tabExpense Claim` ec
        INNER JOIN
            `tabExpense Claim Detail` ecd ON ecd.parent = ec.name
        LEFT JOIN
            `tabCompany` c ON c.name = ec.company
        WHERE
            ec.docstatus = 1
            AND ec.is_paid = 0
            {conditions}
            {detail_conditions}
        ORDER BY
            ec.posting_date DESC, ec.employee_name ASC, ecd.expense_date DESC
        """.format(
            conditions=conditions,
            detail_conditions=detail_conditions,
        ),
        filters,
        as_dict=True,
    )

    return data


def get_conditions(filters):
    conditions = []
    detail_conditions = []

    if filters.get("company"):
        conditions.append("AND ec.company = %(company)s")

    if filters.get("employee"):
        conditions.append("AND ec.employee = %(employee)s")

    if filters.get("department"):
        conditions.append("AND ec.department = %(department)s")

    if filters.get("from_date"):
        conditions.append("AND ec.posting_date >= %(from_date)s")

    if filters.get("to_date"):
        conditions.append("AND ec.posting_date <= %(to_date)s")

    if filters.get("approval_status"):
        conditions.append("AND ec.approval_status = %(approval_status)s")

    # Filters on Expense Claim Detail (line-item level)
    if filters.get("expense_type"):
        detail_conditions.append("AND ecd.expense_type = %(expense_type)s")

    if filters.get("expense_from_date"):
        detail_conditions.append("AND ecd.expense_date >= %(expense_from_date)s")

    if filters.get("expense_to_date"):
        detail_conditions.append("AND ecd.expense_date <= %(expense_to_date)s")

    return " ".join(conditions), " ".join(detail_conditions)


def get_chart_data(data):
    if not data:
        return None

    # Group sanctioned amount by expense_type for bar chart
    expense_type_map = {}
    for row in data:
        expense_type = row.get("expense_type") or "Others"
        expense_type_map[expense_type] = expense_type_map.get(expense_type, 0) + flt(
            row.get("sanctioned_amount")
        )

    labels = list(expense_type_map.keys())
    values = list(expense_type_map.values())

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Sanctioned Amount by Expense Type"),
                    "values": values,
                }
            ],
        },
        "type": "bar",
        "colors": ["#5e64ff"],
        "barOptions": {"stacked": False},
    }


def get_report_summary(data, filters):
    if not data:
        return None

    # Deduplicate on Expense Claim name to avoid inflating header-level totals
    # (each claim appears once per expense line due to the INNER JOIN)
    seen = set()
    total_claimed = 0.0
    total_sanctioned = 0.0
    total_paid = 0.0

    for row in data:
        if row.get("name") not in seen:
            seen.add(row.get("name"))
            total_claimed += flt(row.get("total_claimed_amount"))
            total_sanctioned += flt(row.get("total_sanctioned_amount"))
            total_paid += flt(row.get("total_amount_reimbursed"))

    total_pending = total_sanctioned - total_paid

    # Resolve display currency: prefer company filter, fall back to first row
    currency = ""
    company = filters.get("company") if filters else None
    if company:
        currency = frappe.db.get_value("Company", company, "default_currency") or ""
    if not currency and data:
        currency = data[0].get("currency") or ""

    return [
        {
            "value": total_claimed,
            "label": _("Total Claimed"),
            "datatype": "Currency",
            "currency": currency,
            "indicator": "Blue",
        },
        {
            "value": total_sanctioned,
            "label": _("Total Sanctioned"),
            "datatype": "Currency",
            "currency": currency,
            "indicator": "Green",
        },
        {
            "value": total_paid,
            "label": _("Total Paid"),
            "datatype": "Currency",
            "currency": currency,
            "indicator": "Purple",
        },
        {
            "value": total_pending,
            "label": _("Total Pending"),
            "datatype": "Currency",
            "currency": currency,
            "indicator": "Orange",
        },
    ]