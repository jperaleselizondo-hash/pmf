// PMF Engine: correct an evidence link's excerpt, relationship or cited field; its source is immutable
query "evidence/{evidence_id}" verb=PATCH {
  api_group = "PMF App"
  auth = "user"
  description = "Update an evidence link"
  input {
    int evidence_id
    text? excerpt? {
      sensitive = true
    }

    enum? relationship? {
      values = ["supports", "contradicts"]
    }

    text? source_field? filters=trim
    text[]? clear?
  }

  stack {
    function.run "pmf/auth/require_owner" {
      input = {auth_id: $auth.id}
    } as $owner_id

    function.run "pmf/access/evidence" {
      input = {evidence_id: $input.evidence_id, auth_id: $auth.id}
    } as $access

    function.run "pmf/util/patch_data" {
      input = {
        values   : {excerpt: $input.excerpt, relationship: $input.relationship, source_field: $input.source_field}
        clear    : $input.clear
        clearable: ["source_field"]
        required : ["excerpt"]
      }
    } as $data

    db.transaction {
      stack {
        function.run "pmf/lock/insight" {
          input = {insight_id: $access.record.insight_id}
        } as $insight

        db.get insight_evidence {
          field_name = "id"
          field_value = $input.evidence_id
        } as $current

        var $merged {
          value = $current
        }

        foreach ($data|keys) {
          each as $key {
            var.update $merged {
              value = $merged|set:$key:($data|get:$key)
            }
          }
        }

        function.run "pmf/evidence/validate_source" {
          input = {insight: $insight, interview_id: $current.interview_id, survey_participation_id: $current.survey_participation_id, source_field: $merged.source_field, excerpt: $merged.excerpt}
        } as $source

        db.patch insight_evidence {
          field_name = "id"
          field_value = $input.evidence_id
          data = $data
        } as $updated
      }
    }
  }

  response = $updated
}
