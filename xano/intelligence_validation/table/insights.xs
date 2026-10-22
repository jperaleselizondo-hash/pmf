// PMF Engine: reviewed or draft interpretation of a customer finding
table insights {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp? updated_at?
    int product_id {
      table = "products"
    }

    int? segment_id? {
      table = "segments"
      description = "API must verify the segment belongs to the insight's product"
    }

    enum type {
      values = ["problem", "benefit", "obstacle", "customer_characteristic"]
    }

    text statement filters=trim {
      sensitive = true
      description = "Interpreted finding; reviewed status requires at least one evidence link"
    }

    enum confidence?="low" {
      values = ["low", "medium", "high"]
    }

    enum review_status?="draft" {
      values = ["draft", "reviewed"]
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "product_id", op: "asc"}, {name: "created_at", op: "desc"}]}
    {type: "btree", field: [{name: "segment_id", op: "asc"}, {name: "created_at", op: "desc"}]}
    {type: "btree", field: [{name: "review_status", op: "asc"}, {name: "created_at", op: "desc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]
}
