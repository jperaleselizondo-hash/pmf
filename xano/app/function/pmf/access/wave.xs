// PMF Engine: load a survey wave whose product is owned by the caller, or 404
function "pmf/access/wave" {
  description = "Load an owned survey wave"
  input {
    int wave_id
    int auth_id
  }

  stack {
    db.get survey_waves {
      field_name = "id"
      field_value = $input.wave_id
    } as $wave

    precondition ($wave != null) {
      error_type = "notfound"
      error = "NOT_FOUND: survey wave not found"
    }

    function.run "pmf/access/product" {
      input = {product_id: $wave.product_id, auth_id: $input.auth_id}
    } as $product
  }

  response = {record: $wave, product_id: $product.id}
  guid = "0B4mSx7IeyWL2MUJy6pjOseozvU"
}
