// PMF Engine: update product definitions (owner and id are immutable; blank optional text clears)
query "products/{product_id}" verb=PATCH {
  api_group = "PMF App"
  auth = "user"
  description = "Update a product"
  input {
    int product_id
    text? name? filters=trim
    text? description? filters=trim
    text? core_value? filters=trim
    text? activation_definition? filters=trim
    text? value_event_definition? filters=trim
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
        values  : {name: $input.name, description: $input.description, core_value: $input.core_value, activation_definition: $input.activation_definition, value_event_definition: $input.value_event_definition}
        required: ["name"]
      }
    } as $data

    db.patch products {
      field_name = "id"
      field_value = $product.id
      data = $data
    } as $updated
  }

  response = $updated
  guid = "Em2JYgEBdAy3X4OBEeVUBVg3f4M"
}
