// PMF Engine: a testable product or customer-value hypothesis
table hypotheses {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp? updated_at?
    int insight_id {
      table = "insights"
      description = "API permits linking only to a reviewed insight"
    }

    text statement filters=trim
    text expected_outcome filters=trim
    text success_metric filters=trim

    enum priority?="medium" {
      values = ["low", "medium", "high"]
    }

    enum status?="proposed" {
      values = ["proposed", "testing", "validated", "rejected"]
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "insight_id", op: "asc"}, {name: "created_at", op: "desc"}]}
    {type: "btree", field: [{name: "status", op: "asc"}, {name: "created_at", op: "desc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]
  guid = "rceJ9f8BqX5HjHmCCTxot8iam0k"
}
