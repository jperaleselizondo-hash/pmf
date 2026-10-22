// PMF Engine: delete a customer only when no interview or survey participation references it
query "customers/{customer_id}" verb=DELETE {
  api_group = "PMF App"
  auth = "user"
  description = "Delete an unreferenced customer"
  input {
    int customer_id
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/customer" {
      input = {customer_id: $input.customer_id, auth_id: $auth.id}
    } as $access

    db.transaction {
      stack {
        function.run "pmf/guard/count_references" {
          input = {entity: "customer", id: $input.customer_id}
        } as $refs

        precondition ($refs.total == 0) {
          error_type = "inputerror"
          error = "IN_USE: the customer has interviews or survey participations"
        }

        db.del customers {
          field_name = "id"
          field_value = $input.customer_id
        }
      }
    }
  }

  response = {deleted: true, id: $input.customer_id}
  guid = "mWbUbPG0S_HUayqN1NdPK1KedGs"
}
