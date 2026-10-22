// PMF Engine: a referenced segment must exist and belong to the same product (null is allowed)
function "pmf/integrity/segment_in_product" {
  description = "Reject cross-product segment references"
  input {
    int? segment_id?
    int product_id
  }

  stack {
    var $segment {
      value = null
    }

    conditional {
      if ($input.segment_id != null) {
        db.get segments {
          field_name = "id"
          field_value = $input.segment_id
        } as $found

        precondition ($found != null && $found.product_id == $input.product_id) {
          error_type = "inputerror"
          error = "CROSS_PRODUCT_REFERENCE: segment does not belong to this product"
        }

        var.update $segment {
          value = $found
        }
      }
    }
  }

  response = $segment
}
