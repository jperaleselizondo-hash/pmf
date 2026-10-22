// PMF Engine: load a customer whose product is owned by the caller, or 404
function "pmf/access/customer" {
  description = "Load an owned customer"
  input {
    int customer_id
    int auth_id
  }

  stack {
    db.get customers {
      field_name = "id"
      field_value = $input.customer_id
    } as $customer

    precondition ($customer != null) {
      error_type = "notfound"
      error = "NOT_FOUND: customer not found"
    }

    function.run "pmf/access/product" {
      input = {product_id: $customer.product_id, auth_id: $input.auth_id}
    } as $product
  }

  response = {record: $customer, product_id: $product.id}
}
