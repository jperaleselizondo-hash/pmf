// PMF Engine: load an insight whose product is owned by the caller, or 404
function "pmf/access/insight" {
  description = "Load an owned insight"
  input {
    int insight_id
    int auth_id
  }

  stack {
    db.get insights {
      field_name = "id"
      field_value = $input.insight_id
    } as $insight

    precondition ($insight != null) {
      error_type = "notfound"
      error = "NOT_FOUND: insight not found"
    }

    function.run "pmf/access/product" {
      input = {product_id: $insight.product_id, auth_id: $input.auth_id}
    } as $product
  }

  response = {record: $insight, product_id: $product.id}
  guid = "o3GWF9YZ5-LoqxP4jutUu4-_U7M"
}
