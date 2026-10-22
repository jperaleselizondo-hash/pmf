// PMF Engine: product overview with per-wave PMF summaries; no fabricated trends
query "products/{product_id}/overview" verb=GET {
  api_group = "PMF App"
  auth = "user"
  description = "Product overview and wave PMF summaries"
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

    db.query customers {
      where = $db.customers.product_id == $product.id
      return = {type: "list"}
      output = ["id", "lifecycle_stage"]
    } as $customers

    db.query segments {
      where = $db.segments.product_id == $product.id
      return = {type: "count"}
    } as $segment_count

    db.query interviews {
      join = {
        customers: {table: "customers", type: "inner", where: $db.interviews.customer_id == $db.customers.id}
      }

      where = $db.customers.product_id == $product.id
      return = {type: "count"}
    } as $interview_count

    db.query survey_waves {
      where = $db.survey_waves.product_id == $product.id
      sort = {created_at: "desc"}
      return = {type: "list"}
    } as $waves

    var $wave_summaries {
      value = []
    }

    foreach ($waves) {
      each as $wave {
        function.run "pmf/report/build_wave_report" {
          input = {wave: $wave, summary: true}
        } as $summary

        var.update $wave_summaries {
          value = $wave_summaries|push:$summary
        }
      }
    }

    db.query insights {
      where = $db.insights.product_id == $product.id
      return = {type: "list"}
      output = ["id", "review_status"]
    } as $insights

    db.query hypotheses {
      join = {
        insights: {table: "insights", type: "inner", where: $db.hypotheses.insight_id == $db.insights.id}
      }

      where = $db.insights.product_id == $product.id
      return = {type: "list"}
      output = ["id", "status"]
    } as $hypotheses

    db.query experiments {
      join = {
        hypotheses: {table: "hypotheses", type: "inner", where: $db.experiments.hypothesis_id == $db.hypotheses.id}
        insights  : {table: "insights", type: "inner", where: $db.hypotheses.insight_id == $db.insights.id}
      }

      where = $db.insights.product_id == $product.id
      sort = {created_at: "desc"}
      return = {type: "list", paging: {page: 1, per_page: 5}}
      output = ["id", "hypothesis_id", "name", "started_at", "ended_at", "conclusion", "decision", "created_at"]
    } as $recent_experiments

    var $by_lifecycle {
      value = {prospect: (($customers|filter:$$.lifecycle_stage == "prospect")|count), active: (($customers|filter:$$.lifecycle_stage == "active")|count), former: (($customers|filter:$$.lifecycle_stage == "former")|count)}
    }

    var $insight_counts {
      value = {draft: (($insights|filter:$$.review_status == "draft")|count), reviewed: (($insights|filter:$$.review_status == "reviewed")|count)}
    }

    var $hypothesis_counts {
      value = {proposed: (($hypotheses|filter:$$.status == "proposed")|count), testing: (($hypotheses|filter:$$.status == "testing")|count), validated: (($hypotheses|filter:$$.status == "validated")|count), rejected: (($hypotheses|filter:$$.status == "rejected")|count)}
    }
  }

  response = {
    product           : $product
    customers         : {total: $customers|count, by_lifecycle: $by_lifecycle}
    segments_count    : $segment_count
    interviews_count  : $interview_count
    latest_wave       : $wave_summaries|first
    waves             : $wave_summaries
    insights          : $insight_counts
    hypotheses        : $hypothesis_counts
    recent_experiments: $recent_experiments.items
  }
  guid = "4B3cOTCX1CaXH4vsJlchi8m7LSs"
}
