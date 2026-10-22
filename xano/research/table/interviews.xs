// PMF Engine: a customer interview with raw, first-hand notes
table interviews {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp? updated_at?
    int customer_id {
      table = "customers"
    }

    timestamp conducted_at
    text? notes? {
      sensitive = true
    }

    text? transcript? {
      sensitive = true
    }

    text? existing_alternatives? {
      sensitive = true
    }

    text? problem_context? {
      sensitive = true
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "customer_id", op: "asc"}, {name: "conducted_at", op: "desc"}]}
    {type: "btree", field: [{name: "conducted_at", op: "desc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]
}
