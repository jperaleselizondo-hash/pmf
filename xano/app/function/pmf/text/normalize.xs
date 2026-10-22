// PMF Engine: blank text becomes null; founder text is trimmed, raw evidence is kept verbatim
function "pmf/text/normalize" {
  description = "Normalize optional text: blank to null, optional trim"
  input {
    text? value?
    bool trim?=true
  }

  stack {
    var $result {
      value = null
    }

    conditional {
      if ($input.value != null) {
        var $trimmed {
          value = $input.value|trim
        }

        conditional {
          if (($trimmed|strlen) > 0) {
            conditional {
              if ($input.trim) {
                var.update $result {
                  value = $trimmed
                }
              }

              else {
                var.update $result {
                  value = $input.value
                }
              }
            }
          }
        }
      }
    }
  }

  response = $result

  test "trims founder text" {
    input = {value: "  Idea  ", trim: true}
    expect.to_equal ($response) {
      value = "Idea"
    }
  }

  test "keeps raw evidence verbatim" {
    input = {value: "  said: no  ", trim: false}
    expect.to_equal ($response) {
      value = "  said: no  "
    }
  }

  test "blank becomes null" {
    input = {value: "   ", trim: false}
    expect.to_be_null ($response)
  }

  test "null stays null" {
    input = {value: null}
    expect.to_be_null ($response)
  }
}
