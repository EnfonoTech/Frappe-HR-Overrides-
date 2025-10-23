<template>
	<ion-page>
		<ion-content :fullscreen="true">
			<FormView
				v-if="formFields.data"
				doctype="Expense Claim"
				v-model="expenseClaim"
				:isSubmittable="true"
				:fields="formFields.data"
				:id="props.id"
				:tabbedView="true"
				:tabs="tabs"
				:showAttachmentView="false"
				@validateForm="validateForm"
			>
				<!-- Child Tables -->
				<template #expenses="{ isFormReadOnly }">
					<div v-show="false">
						<ExpensesTable
							v-model:expenseClaim="expenseClaim"
							:currency="currency"
							:isReadOnly="isReadOnly || isFormReadOnly"
							@addExpenseItem="addExpenseItem"
							@updateExpenseItem="updateExpenseItem"
							@deleteExpenseItem="deleteExpenseItem"
						/>
					</div>
				</template>

				<template #taxes="{ isFormReadOnly }">
					<div v-show="false">
						<ExpenseTaxesTable
							v-model:expenseClaim="expenseClaim"
							:currency="currency"
							:isReadOnly="isReadOnly || isFormReadOnly"
							@addExpenseTax="addExpenseTax"
							@updateExpenseTax="updateExpenseTax"
							@deleteExpenseTax="deleteExpenseTax"
						/>
					</div>
				</template>

				<template #advances="{ isFormReadOnly }">
					<div v-show="false">
						<ExpenseAdvancesTable
							v-model:expenseClaim="expenseClaim"
							:currency="currency"
							:isReadOnly="isReadOnly || isFormReadOnly"
						/>
					</div>
				</template>
			</FormView>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { createResource } from "frappe-ui"
import { computed, ref, watch, inject } from "vue"

import FormView from "@/components/FormView.vue"
import ExpensesTable from "@/components/ExpensesTable.vue"
import ExpenseTaxesTable from "@/components/ExpenseTaxesTable.vue"
import ExpenseAdvancesTable from "@/components/ExpenseAdvancesTable.vue"

import { getCompanyCurrency } from "@/data/currencies"
import { call } from "frappe-ui"

const dayjs = inject("$dayjs")
const employee = inject("$employee")
const today = dayjs().format("YYYY-MM-DD")
const isReadOnly = ref(false)

const props = defineProps({
	id: {
		type: String,
		required: false,
	},
})

const tabs = [
	{ name: "Trip Allowance", lastField: "cost_center" },
]

// object to store form data
const expenseClaim = ref({
  employee: employee.data.name,
  company: employee.data.company,
  custom_trip_location: "",
  custom_from: "",
  custom_to: "",
  custom_distance_in_km: 0,
})
const currency = computed(() => getCompanyCurrency(expenseClaim.value.company))

// get form fields
const formFields = createResource({
	url: "hrms.api.get_doctype_fields",
	params: { doctype: "Expense Claim" },
	transform(data) {
		let fields = getFilteredFields(data)

		return fields.map((field) => {
			
			if (field.fieldname === "posting_date") field.default = today
			if (field.fieldname === "custom_expense_claim_type") {
				field.default = "Trip Allowance"
				field.read_only = true 
			}
			return applyFilters(field)
		})
	},
	onSuccess(_data) {
		expenseApproverDetails.reload()
		companyDetails.reload()
	},
})
formFields.reload()

// resources
const advances = createResource({
	url: "hrms.hr.doctype.expense_claim.expense_claim.get_advances",
	params: { employee: employee.data.name },
	auto: true,
	onSuccess(data) {
		// set advances
		if (props.id) {
			expenseClaim.value.advances?.map((advance) => (advance.selected = true))
		} else {
			expenseClaim.value.advances = []
		}

		return data.forEach((advance) => {
			if (
				props.id &&
				expenseClaim.value.advances?.some(
					(entry) => entry.employee_advance === advance.name
				)
			)
				return

			expenseClaim.value.advances?.push({
				employee_advance: advance.name,
				purpose: advance.purpose,
				posting_date: advance.posting_date,
				advance_account: advance.advance_account,
				advance_paid: advance.paid_amount,
				unclaimed_amount: advance.paid_amount - advance.claimed_amount,
				allocated_amount: 0,
			})
		})
	},
})

const expenseApproverDetails = createResource({
	url: "hrms.api.get_expense_approval_details",
	params: { employee: employee.data.name },
	onSuccess(data) {
		setExpenseApprover(data)
	},
})

const companyDetails = createResource({
	url: "hrms.api.get_company_cost_center_and_expense_account",
	params: { company: expenseClaim.value.company },
	onSuccess(data) {
		expenseClaim.value.cost_center = data?.cost_center
		expenseClaim.value.payable_account =
			data?.default_expense_claim_payable_account
	},
})

// form scripts
watch(
	() => expenseClaim.value.employee,
	(employee_id) => {
		if (props.id && employee_id !== employee.data.name) {
			// if employee is not the current user, set form as read only
			setFormReadOnly()
		}
	}
)

watch(
	() => props.id && expenseClaim.value.expenses,
	(_) => {
		if (expenseClaim.value.docstatus === 0) {
			advances.reload()
		}
	}
)

watch(
	() => expenseClaim.value.advances,
	(_value) => {
		calculateTotalAdvance()
	},
	{ deep: true }
)

watch(
	() => expenseClaim.value.cost_center,
	() => {
		expenseClaim?.value?.expenses?.forEach((expense) => {
			expense.cost_center = expenseClaim.value.cost_center
		})
	}
)

watch(
  () => expenseClaim.value.custom_trip_location,
  async (trip_location) => {
    if (!trip_location) return;

    try {
      console.log("Watcher triggered with Trip Location:", trip_location);

      // Fetch Trip Location record
      const res = await call("frappe.client.get_list", {
        doctype: "Trip Location",
        filters: { name: trip_location },
        fields: ["from", "to", "distancekm"],
        limit_page_length: 1,
      });

      console.log("Trip Location API Response:", res);

      if (!res || !res.length) {
        console.warn("Trip Location not found:", trip_location);
        expenseClaim.value.custom_from = "";
        expenseClaim.value.custom_to = "";
        expenseClaim.value.custom_distance_in_km = "";
        return;
      }

      const data = res[0];

      // Update expenseClaim fields reactively
      expenseClaim.value.custom_from = data.from || "";
      expenseClaim.value.custom_to = data.to || "";
      expenseClaim.value.custom_distance_in_km = data.distancekm || "";

      console.log("Updated expenseClaim after Trip Location fetch:", {
        custom_from: expenseClaim.value.custom_from,
        custom_to: expenseClaim.value.custom_to,
        custom_distance_in_km: expenseClaim.value.custom_distance_in_km
      });
      // Trigger trip amount calculation
      calculateTripAmount();

    } catch (err) {
      console.error("Error fetching Trip Location:", err);
    }
  }
);

watch(
  () => expenseClaim.value.custom_holiday,
  () => {
    console.log("Holiday changed:", expenseClaim.value.custom_holiday);
    calculateTripAmount();
  }
);

function calculateTripAmount() {
  const employee = expenseClaim.value.employee;
  const distance = expenseClaim.value.custom_distance_in_km;
  const is_holiday = expenseClaim.value.custom_holiday === "Yes";
  let trip_amount = 0;

  console.log("Calculating trip amount with:", {
    employee,
    distance,
    is_holiday
  });

  if (!employee || !distance) {
    console.warn("Employee or distance not set, skipping calculation.");
    return;
  }
  call("frappe.client.get_value", {
	doctype: "Employee",
	filters: { name: expenseClaim.value.employee },
	fieldname: "designation"
	}).then(res => {
	console.log("Raw response:", res);

	// Access directly
	const designation = res?.designation;	

	console.log("Extracted designation:", designation);

	if (!designation) {
		console.warn("Employee designation not found for", expenseClaim.value.employee);
		return;
	}

	const is_driver = ["Pick Up Driver", "Heavy Truck Driver"].includes(designation);
	const distance = expenseClaim.value.custom_distance_in_km;
	const is_holiday = expenseClaim.value.custom_holiday === "Yes";

	let trip_amount = 0;

	if (is_driver) {
		if (is_holiday) {
		if (distance === "300-500") trip_amount = 150;
		else if (distance === "501-1000") trip_amount = 175;
		else if (distance === "1000+") trip_amount = 250;
		} else {
		if (distance === "300-500") trip_amount = 100;
		else if (distance === "501-1000") trip_amount = 125;
		else if (distance === "1000+") trip_amount = 185;
		}
	} else {
		if (is_holiday) {
		if (distance === "300-500") trip_amount = 100;
		else if (distance === "501-1000") trip_amount = 150;
		else if (distance === "1000+") trip_amount = 200;
		} else {
		if (distance === "300-500") trip_amount = 75;
		else if (distance === "501-1000") trip_amount = 100;
		else if (distance === "1000+") trip_amount = 140;
		}
	}

	expenseClaim.value.custom_trip_amount = trip_amount;
	console.log("Calculated trip amount:", trip_amount);
	});
}

// helper functions
function getFilteredFields(fields) {
	// reduce noise from the form view by excluding unnecessary fields
	// eg: employee and other details can be fetched from the session user
	const excludeFields = [
		"naming_series",
		"task",
		"taxes_and_charges_sb",
		"advance_payments_sb",
		"accounting_dimensions_section",
		"transactions_section",
		"accounting_details",	
	]
	const extraFields = [
		"employee",
		"employee_name",
		"department",
		"remark",
		"is_paid",
		"mode_of_payment",
		"clearance_date",
		"approval_status",
	]

	if (!props.id) excludeFields.push(...extraFields)

	return fields.filter((field) => !excludeFields.includes(field.fieldname))
}

function applyFilters(field) {
	

	if (["posting_date","grand_total"].includes(field.fieldname)) {
			field.hidden = true
		}
	if (field.fieldname === "cost_center") {
		field.hidden = true  
	}
	if (field.fieldname === "payable_account") {
		field.hidden = true  
	}
	if (field.fieldname === "project") {
		field.hidden = true 
	}
	if (field.fieldname === "payable_account") {
		field.linkFilters = {
			report_type: "Balance Sheet",
			account_type: "Payable",
			company: expenseClaim.value.company,
			is_group: 0,
		}
	} else if (field.fieldname === "cost_center") {
		field.linkFilters = {
			company: expenseClaim.value.company,
			is_group: 0,
		}
	} else if (field.fieldname === "project") {
		field.linkFilters = {
			company: expenseClaim.value.company,
		}
	}

	return field
}

function setExpenseApprover(data) {
	const expense_approver = formFields.data?.find(
		(field) => field.fieldname === "expense_approver"
	)
	expense_approver.reqd = data?.is_mandatory
	expense_approver.documentList = data?.department_approvers.map(
		(approver) => ({
			label: approver.full_name
				? `${approver.name} : ${approver.full_name}`
				: approver.name,
			value: approver.name,
		})
	)

	expenseClaim.value.expense_approver = data?.expense_approver
	expenseClaim.value.expense_approver_name = data?.expense_approver_name
}

function addExpenseItem(item) {
	if (!expenseClaim.value.expenses) expenseClaim.value.expenses = []
	expenseClaim.value.expenses.push(item)
	calculateTotals()
	calculateTaxes()
	allocateAdvanceAmount()
}

function updateExpenseItem(item, idx) {
	expenseClaim.value.expenses[idx] = item
	calculateTotals()
	calculateTaxes()
	allocateAdvanceAmount()
}

function deleteExpenseItem(idx) {
	expenseClaim.value.expenses.splice(idx, 1)
	calculateTotals()
	calculateTaxes()
	allocateAdvanceAmount()
}

function addExpenseTax(item) {
	if (!expenseClaim.value.taxes) expenseClaim.value.taxes = []
	expenseClaim.value.taxes.push(item)
	calculateTaxes()
	allocateAdvanceAmount()
}

function updateExpenseTax(item, idx) {
	expenseClaim.value.taxes[idx] = item
	calculateTaxes()
	allocateAdvanceAmount()
}

function deleteExpenseTax(idx) {
	expenseClaim.value.taxes.splice(idx, 1)
	calculateTaxes()
	allocateAdvanceAmount()
}

function calculateTotals() {
	let total_claimed_amount = 0
	let total_sanctioned_amount = 0

	expenseClaim.value?.expenses?.forEach((item) => {
		total_claimed_amount += parseFloat(item.amount)
		total_sanctioned_amount += parseFloat(item.sanctioned_amount)
	})

	expenseClaim.value.total_claimed_amount = total_claimed_amount
	expenseClaim.value.total_sanctioned_amount = total_sanctioned_amount
	calculateGrandTotal()
}

function calculateTaxes() {
	let total_taxes_and_charges = 0

	expenseClaim.value?.taxes?.forEach((item) => {
		if (item.rate) {
			item.tax_amount =
				parseFloat(expenseClaim.value.total_sanctioned_amount) *
				parseFloat(item.rate / 100)
		}

		item.total =
			parseFloat(item.tax_amount) +
			parseFloat(expenseClaim.value.total_sanctioned_amount)
		total_taxes_and_charges += parseFloat(item.tax_amount)
	})
	expenseClaim.value.total_taxes_and_charges = total_taxes_and_charges
	calculateGrandTotal()
}

function calculateGrandTotal() {
	expenseClaim.value.grand_total =
		parseFloat(expenseClaim.value.total_sanctioned_amount || 0) +
		parseFloat(expenseClaim.value.total_taxes_and_charges || 0) -
		parseFloat(expenseClaim.value.total_advance_amount || 0)
}

function allocateAdvanceAmount() {
	// allocate reqd advance amount
	let amount_to_be_allocated =
		parseFloat(expenseClaim.value.total_sanctioned_amount) +
		parseFloat(expenseClaim.value.total_taxes_and_charges)
	let total_advance_amount = 0

	expenseClaim?.value?.advances?.forEach((advance) => {
		if (amount_to_be_allocated >= parseFloat(advance.unclaimed_amount)) {
			advance.allocated_amount = parseFloat(advance.unclaimed_amount)
			amount_to_be_allocated -= parseFloat(advance.allocated_amount)
		} else {
			advance.allocated_amount = amount_to_be_allocated
			amount_to_be_allocated = 0
		}

		advance.selected = advance.allocated_amount > 0 ? true : false
		total_advance_amount += parseFloat(advance.allocated_amount)
	})
	expenseClaim.value.total_advance_amount = total_advance_amount
	calculateGrandTotal()
}

function calculateTotalAdvance() {
	// update total advance amount as per user selection & edited values
	let total_advance_amount = 0

	expenseClaim?.value?.advances?.forEach((advance) => {
		if (advance.selected) {
			total_advance_amount += parseFloat(advance.allocated_amount)
		}
	})
	expenseClaim.value.total_advance_amount = total_advance_amount
	calculateGrandTotal()
}

function setFormReadOnly() {
	if (expenseClaim.value.expense_approver === employee.data.user_id) return
	formFields.data.map((field) => (field.read_only = true))
	isReadOnly.value = true
}

function validateForm() {
	// set selected advances
	if (!expenseClaim?.value?.advances) return

	expenseClaim.value.advances = expenseClaim?.value?.advances?.filter(
		(advance) => advance.selected
	)
	expenseClaim?.value?.expenses?.forEach((expense) => {
		expense.cost_center = expenseClaim.value.cost_center
	})
}
</script>
