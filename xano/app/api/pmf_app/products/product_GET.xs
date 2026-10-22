// PMF Engine: product detail with related record counts
query "products/{product_id}" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "Get a product with related counts"
  input {
    int product_id
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/product" {
      input = {product_id: $input.product_id, auth_id: $auth.id}
    } as $product

    db.query segments {
      where = $db.segments.product_id == $product.id
      return = {type: "count"}
    } as $segment_count

    db.query customers {
      where = $db.customers.product_id == $product.id
      return = {type: "count"}
    } as $customer_count

    db.query interviews {
      join = {
        customers: {table: "customers", type: "inner", where: $db.interviews.customer_id == $db.customers.id}
      }

      where = $db.customers.product_id == $product.id
      return = {type: "count"}
    } as $interview_count

    db.query survey_waves {
      where = $db.survey_waves.product_id == $product.id
      return = {type: "count"}
    } as $wave_count

    db.query insights {
      where = $db.insights.product_id == $product.id
      return = {type: "count"}
    } as $insight_count

    db.query hypotheses {
      join = {
        insights: {table: "insights", type: "inner", where: $db.hypotheses.insight_id == $db.insights.id}
      }

      where = $db.insights.product_id == $product.id
      return = {type: "count"}
    } as $hypothesis_count
  }

  response = $product|set:"counts":{segments: $segment_count, customers: $customer_count, interviews: $interview_count, survey_waves: $wave_count, insights: $insight_count, hypotheses: $hypothesis_count}
  guid = "OV7RJ_sYIQvha8_Bt4Bv3UbulzY"
}
