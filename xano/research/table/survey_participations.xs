// PMF Engine: one eligible customer in one survey wave, responded or not
table survey_participations {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      description = "When the customer was qualified for the wave"
    }

    timestamp? updated_at?
    int survey_wave_id {
      table = "survey_waves"
    }

    int customer_id {
      table = "customers"
      description = "API must verify the customer belongs to the wave's product"
    }

    int? segment_id_snapshot? {
      table = "segments"
      description = "Customer's segment at qualification; set by the server on create, never updated"
    }

    timestamp? invited_at?
    timestamp? responded_at?
    enum? disappointment_level? {
      values = ["very", "somewhat", "not"]
      description = "Counts toward PMF only together with responded_at"
    }

    text? beneficiary_description? {
      sensitive = true
    }

    text? main_benefit? {
      sensitive = true
    }

    text? improvement_request? {
      sensitive = true
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "survey_wave_id", op: "asc"}, {name: "customer_id", op: "asc"}]}
    {type: "btree", field: [{name: "customer_id", op: "asc"}, {name: "created_at", op: "desc"}]}
    {type: "btree", field: [{name: "survey_wave_id", op: "asc"}, {name: "segment_id_snapshot", op: "asc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]
  guid = "BF-adhEQRC36Y0SmfrZV-6mZJVs"
}
