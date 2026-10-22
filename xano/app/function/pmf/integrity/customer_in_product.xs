// PMF Engine: a referenced customer must exist and belong to the same product
function "pmf/integrity/customer_in_product" {
  description = "Reject cross-product customer references"
  input {
    int customer_id
    int product_id
  }

  stack {
    db.get customers {
      field_name = "id"
      field_value = $input.customer_id
    } as $customer

    precondition ($customer != null && $customer.product_id == $input.product_id) {
      error_type = "inputerror"
      error = "CROSS_PRODUCT_REFERENCE: customer " ~ $input.customer_id ~ " does not belong to this product"
    }
  }

  response = $customer
}
