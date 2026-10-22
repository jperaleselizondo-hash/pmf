// PMF Engine: build a write payload from optional inputs
// null = unchanged; blank text = null (rejected for required fields); `clear` nulls allowed non-text fields
function "pmf/util/patch_data" {
  description = "Build create/update payload with blank, clear and required handling"
  input {
    json values
    text[]? clear?
    text[]? clearable?
    text[]? required?
    bool touch?=true
  }

  stack {
    var $data {
      value = {}
    }

    var $required {
      value = $input.required ?? []
    }

    var $clearable {
      value = $input.clearable ?? []
    }

    var $clear {
      value = $input.clear ?? []
    }

    foreach ($input.values|keys) {
      each as $key {
        var $value {
          value = $input.values|get:$key
        }

        conditional {
          if ($value != null) {
            conditional {
              if (((($value|to_text)|trim)|strlen) == 0) {
                precondition (!($required|some:$$ == $key)) {
                  error_type = "inputerror"
                  error = "FIELD_REQUIRED: " ~ $key ~ " must not be blank"
                }

                var.update $data {
                  value = $data|set:$key:null
                }
              }

              else {
                var.update $data {
                  value = $data|set:$key:$value
                }
              }
            }
          }
        }
      }
    }

    foreach ($clear) {
      each as $field {
        precondition ($clearable|some:$$ == $field) {
          error_type = "inputerror"
          error = "INVALID_CLEAR_FIELD: " ~ $field ~ " cannot be cleared"
        }

        precondition (($input.values|get:$field) == null) {
          error_type = "inputerror"
          error = "CONFLICTING_FIELD: " ~ $field ~ " is both set and cleared"
        }

        var.update $data {
          value = $data|set:$field:null
        }
      }
    }

    conditional {
      if ($input.touch) {
        var.update $data {
          value = $data|set:"updated_at":now
        }
      }
    }
  }

  response = $data

  test "drops nulls and keeps values" {
    input = {values: {name: "A", description: null}, touch: false}
    expect.to_equal ($response) {
      value = {name: "A"}
    }
  }

  test "blank optional text becomes null" {
    input = {values: {description: "  "}, touch: false}
    expect.to_be_null ($response.description)
  }

  test "blank required text throws" {
    input = {values: {name: " "}, required: ["name"], touch: false}
    expect.to_throw
  }

  test "clear outside allow-list throws" {
    input = {values: {}, clear: ["product_id"], clearable: ["segment_id"], touch: false}
    expect.to_throw
  }
  guid = "k1FXXopGh-EpDUHrcGkIf6WA-4o"
}
