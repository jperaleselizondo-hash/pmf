// PMF Engine: create a segment; names are unique per product (case-sensitive, D-017)
query "products/{product_id}/segments" verb=POST {
  api_group = "PMF App"
  auth = "user"
  description = "Create a segment"
  input {
    int product_id
    text name filters=trim
    text? description? filters=trim
    text? criteria? filters=trim
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/product" {
      input = {product_id: $input.product_id, auth_id: $auth.id}
    } as $product

    function.run "pmf/util/patch_data" {
      input = {
        values  : {name: $input.name, description: $input.description, criteria: $input.criteria}
        required: ["name"]
        touch   : false
      }
    } as $data

    db.query segments {
      where = $db.segments.product_id == $product.id && $db.segments.name == $data.name
      return = {type: "exists"}
    } as $duplicate

    precondition (!$duplicate) {
      error_type = "inputerror"
      error = "DUPLICATE_SEGMENT_NAME: a segment with this name already exists for the product"
    }

    db.add segments {
      data = {
        product_id : $product.id
        name       : $data.name
        description: $data.description
        criteria   : $data.criteria
      }
    } as $segment
  }

  response = $segment
  guid = "Gs0LOTeU9Sa1c04ARzuYNlfzdvI"
}
