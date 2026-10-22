// PMF Engine: create a product; the owner is always the authenticated designated owner
query "products" verb=POST {
  api_group = "PMF App"
  auth = "user"
  description = "Create a product"
  input {
    text name filters=trim
    text? description? filters=trim
    text? core_value? filters=trim
    text? activation_definition? filters=trim
    text? value_event_definition? filters=trim
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/util/patch_data" {
      input = {
        values  : {name: $input.name, description: $input.description, core_value: $input.core_value, activation_definition: $input.activation_definition, value_event_definition: $input.value_event_definition}
        required: ["name"]
        touch   : false
      }
    } as $data

    db.add products {
      data = {
        owner_user_id         : $auth.id
        name                  : $data.name
        description           : $data.description
        core_value            : $data.core_value
        activation_definition : $data.activation_definition
        value_event_definition: $data.value_event_definition
      }
    } as $product
  }

  response = $product
}
