// PMF Engine: true when a value is null or contains only whitespace
function "pmf/text/is_blank" {
  description = "Null or whitespace-only check"
  input {
    text? value?
  }

  stack {
    var $blank {
      value = true
    }

    conditional {
      if ($input.value != null) {
        var.update $blank {
          value = ((($input.value|trim)|strlen) == 0)
        }
      }
    }
  }

  response = $blank

  test "null is blank" {
    input = {value: null}
    expect.to_be_true ($response)
  }

  test "whitespace is blank" {
    input = {value: "   "}
    expect.to_be_true ($response)
  }

  test "text is not blank" {
    input = {value: " a "}
    expect.to_be_false ($response)
  }
  guid = "MGo1gCCEYoDG7vGZ-4t-tyj-8Q0"
}
