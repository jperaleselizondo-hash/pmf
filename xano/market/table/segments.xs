// PMF Engine: a target customer segment within one product
table segments {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp? updated_at?
    int product_id {
      table = "products"
    }

    text name filters=trim
    text? description? filters=trim
    text? criteria? filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "product_id", op: "asc"}, {name: "name", op: "asc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]
  guid = "W-EFpGzVVRJ7rIR2Ht4QqRcxxlE"
}
