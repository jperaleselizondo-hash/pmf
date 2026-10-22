// PMF Engine: load a product owned by the caller, or 404
function "pmf/access/product" {
  description = "Load an owned product"
  input {
    int product_id
    int auth_id
  }

  stack {
    db.get products {
      field_name = "id"
      field_value = $input.product_id
    } as $product

    precondition ($product != null && $product.owner_user_id == $input.auth_id) {
      error_type = "notfound"
      error = "NOT_FOUND: product not found"
    }
  }

  response = $product
  guid = "cpsRamwILA8oafFCSWxqlx8ZSDc"
}
