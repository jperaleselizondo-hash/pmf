// PMF Engine: an individual prospect or user of one product
table customers {
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
      description = "Primary current segment; API must verify it belongs to the same product"
    }

    text? external_id? filters=trim {
      description = "Optional external reference; API stores blanks as null so uniqueness applies only when present"
    }

    text? name? filters=trim {
      sensitive = true
    }

    email? email? filters=trim|lower {
      sensitive = true
    }

    text? company_name? filters=trim
    enum lifecycle_stage?="prospect" {
      values = ["prospect", "active", "former"]
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "product_id", op: "asc"}, {name: "external_id", op: "asc"}]}
    {type: "btree", field: [{name: "segment_id", op: "asc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]
  guid = "3qTdCCfisuX1dnKCKzk48O8pzKI"
}
