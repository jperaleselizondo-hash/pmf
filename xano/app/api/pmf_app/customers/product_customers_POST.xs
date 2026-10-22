// PMF Engine: create a customer; segment must be in the same product; external_id unique when present
query "products/{product_id}/customers" verb=POST {
  api_group = "PMF App"
  auth = "user"
  description = "Create a customer"
  input {
    int product_id
    int? segment_id?
    text? external_id? filters=trim
    text? name? filters=trim {
      sensitive = true
    }

    email? email? filters=trim|lower {
      sensitive = true
    }

    text? company_name? filters=trim
    enum? lifecycle_stage? {
      values = ["prospect", "active", "former"]
    }
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/product" {
      input = {product_id: $input.product_id, auth_id: $auth.id}
    } as $product

    function.run "pmf/integrity/segment_in_product" {
      input = {segment_id: $input.segment_id, product_id: $product.id}
    } as $segment

    function.run "pmf/util/patch_data" {
      input = {
        values: {segment_id: $input.segment_id, external_id: $input.external_id, name: $input.name, email: $input.email, company_name: $input.company_name, lifecycle_stage: $input.lifecycle_stage}
        touch : false
      }
    } as $data

    var $external_id {
      value = $data|get:"external_id"
    }

    conditional {
      if ($external_id != null) {
        db.query customers {
          where = $db.customers.product_id == $product.id && $db.customers.external_id == $external_id
          return = {type: "exists"}
        } as $duplicate

        precondition (!$duplicate) {
          error_type = "inputerror"
          error = "DUPLICATE_EXTERNAL_ID: another customer of this product has this external_id"
        }
      }
    }

    db.add customers {
      data = {
        product_id     : $product.id
        segment_id     : $data|get:"segment_id"
        external_id    : $external_id
        name           : $data|get:"name"
        email          : $data|get:"email"
        company_name   : $data|get:"company_name"
        lifecycle_stage: $input.lifecycle_stage ?? "prospect"
      }
    } as $customer
  }

  response = $customer
}
