// PMF Engine: create an insight; always starts as draft (review requires evidence)
query "products/{product_id}/insights" verb=POST {
  api_group = "PMF App"
  auth = "user"
  description = "Create an insight"
  input {
    int product_id
    enum type {
      values = ["problem", "benefit", "obstacle", "customer_characteristic"]
    }

    text statement filters=trim {
      sensitive = true
    }

    enum? confidence? {
      values = ["low", "medium", "high"]
    }

    int? segment_id?
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
        values  : {statement: $input.statement}
        required: ["statement"]
        touch   : false
      }
    } as $data

    db.add insights {
      data = {
        product_id   : $product.id
        segment_id   : $input.segment_id
        type         : $input.type
        statement    : $data.statement
        confidence   : $input.confidence ?? "low"
        review_status: "draft"
      }
    } as $insight
  }

  response = $insight
  guid = "EUAlAcvwQt_P27sIBuNsBoqJDQM"
}
