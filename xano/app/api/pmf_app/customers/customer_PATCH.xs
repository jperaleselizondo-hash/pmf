// PMF Engine: update a customer; product is immutable; segment changes never touch survey snapshots
query "customers/{customer_id}" verb=PATCH {
  api_group = "PMF App"
  auth = "user"
  description = "Update a customer"
  input {
    int customer_id
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

    text[]? clear?
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/customer" {
      input = {customer_id: $input.customer_id, auth_id: $auth.id}
    } as $access

    function.run "pmf/integrity/segment_in_product" {
      input = {segment_id: $input.segment_id, product_id: $access.product_id}
    } as $segment

    function.run "pmf/util/patch_data" {
      input = {
        values   : {segment_id: $input.segment_id, external_id: $input.external_id, name: $input.name, email: $input.email, company_name: $input.company_name, lifecycle_stage: $input.lifecycle_stage}
        clear    : $input.clear
        clearable: ["segment_id"]
      }
    } as $data

    var $external_id {
      value = $data|get:"external_id"
    }

    conditional {
      if ($external_id != null && $external_id != $access.record.external_id) {
        db.query customers {
          where = $db.customers.product_id == $access.product_id && $db.customers.external_id == $external_id && $db.customers.id != $input.customer_id
          return = {type: "exists"}
        } as $duplicate

        precondition (!$duplicate) {
          error_type = "inputerror"
          error = "DUPLICATE_EXTERNAL_ID: another customer of this product has this external_id"
        }
      }
    }

    db.patch customers {
      field_name = "id"
      field_value = $input.customer_id
      data = $data
    } as $updated
  }

  response = $updated
}
