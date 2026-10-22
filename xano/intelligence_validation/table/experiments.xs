// PMF Engine: an experiment used to evaluate a hypothesis
table experiments {
  auth = false

  schema {
    int id
    timestamp created_at?=now
    timestamp? updated_at?
    int hypothesis_id {
      table = "hypotheses"
    }

    text name filters=trim
    text method filters=trim
    timestamp? started_at?
    timestamp? ended_at?

    text? baseline? {
      sensitive = true
    }

    text? target? {
      sensitive = true
    }

    text? observed_result? {
      sensitive = true
    }

    enum? conclusion? {
      values = ["supported", "refuted", "inconclusive"]
    }

    enum? decision? {
      values = ["adopt", "iterate", "reject", "investigate"]
    }

    text? notes? {
      sensitive = true
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "hypothesis_id", op: "asc"}, {name: "created_at", op: "desc"}]}
    {type: "btree", field: [{name: "started_at", op: "desc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]
}
