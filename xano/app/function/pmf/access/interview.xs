// PMF Engine: load an interview whose customer's product is owned by the caller, or 404
function "pmf/access/interview" {
  description = "Load an owned interview"
  input {
    int interview_id
    int auth_id
  }

  stack {
    db.get interviews {
      field_name = "id"
      field_value = $input.interview_id
    } as $interview

    precondition ($interview != null) {
      error_type = "notfound"
      error = "NOT_FOUND: interview not found"
    }

    function.run "pmf/access/customer" {
      input = {customer_id: $interview.customer_id, auth_id: $input.auth_id}
    } as $customer
  }

  response = {record: $interview, customer: $customer.record, product_id: $customer.product_id}
}
