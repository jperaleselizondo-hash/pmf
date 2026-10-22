// PMF Engine: a product whose market fit is being investigated
table products {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp? updated_at?
    int owner_user_id {
      table = "user"
      description = "Owning PMF user; API must also enforce the designated owner ID"
    }

    text name filters=trim
    text? description? filters=trim
    text? core_value? filters=trim
    text? activation_definition? filters=trim
    text? value_event_definition? filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "owner_user_id", op: "asc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]
}
