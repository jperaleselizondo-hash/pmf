// PMF Engine: load a segment whose product is owned by the caller, or 404
function "pmf/access/segment" {
  description = "Load an owned segment"
  input {
    int segment_id
    int auth_id
  }

  stack {
    db.get segments {
      field_name = "id"
      field_value = $input.segment_id
    } as $segment

    precondition ($segment != null) {
      error_type = "notfound"
      error = "NOT_FOUND: segment not found"
    }

    function.run "pmf/access/product" {
      input = {product_id: $segment.product_id, auth_id: $input.auth_id}
    } as $product
  }

  response = {record: $segment, product_id: $product.id}
}
