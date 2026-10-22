// PMF Engine: reference counts used by restricted deletes (invariant 8, U8)
function "pmf/guard/count_references" {
  description = "Count records that reference an entity"
  input {
    text entity
    int id
  }

  stack {
    var $refs {
      value = {}
    }

    switch ($input.entity) {
      case ("segment") {
        db.query customers {
          where = $db.customers.segment_id == $input.id
          return = {type: "count"}
        } as $segment_customers

        db.query survey_participations {
          where = $db.survey_participations.segment_id_snapshot == $input.id
          return = {type: "count"}
        } as $segment_snapshots

        db.query insights {
          where = $db.insights.segment_id == $input.id
          return = {type: "count"}
        } as $segment_insights

        var.update $refs {
          value = {customers: $segment_customers, survey_participations: $segment_snapshots, insights: $segment_insights}
        }
      } break

      case ("customer") {
        db.query interviews {
          where = $db.interviews.customer_id == $input.id
          return = {type: "count"}
        } as $customer_interviews

        db.query survey_participations {
          where = $db.survey_participations.customer_id == $input.id
          return = {type: "count"}
        } as $customer_participations

        var.update $refs {
          value = {interviews: $customer_interviews, survey_participations: $customer_participations}
        }
      } break

      case ("interview") {
        db.query insight_evidence {
          where = $db.insight_evidence.interview_id == $input.id
          return = {type: "count"}
        } as $interview_evidence

        var.update $refs {
          value = {insight_evidence: $interview_evidence}
        }
      } break

      case ("wave") {
        db.query survey_participations {
          where = $db.survey_participations.survey_wave_id == $input.id
          return = {type: "count"}
        } as $wave_participations

        var.update $refs {
          value = {survey_participations: $wave_participations}
        }
      } break

      case ("participation") {
        db.query insight_evidence {
          where = $db.insight_evidence.survey_participation_id == $input.id
          return = {type: "count"}
        } as $participation_evidence

        var.update $refs {
          value = {insight_evidence: $participation_evidence}
        }
      } break

      case ("insight") {
        db.query insight_evidence {
          where = $db.insight_evidence.insight_id == $input.id
          return = {type: "count"}
        } as $insight_evidence

        db.query hypotheses {
          where = $db.hypotheses.insight_id == $input.id
          return = {type: "count"}
        } as $insight_hypotheses

        var.update $refs {
          value = {insight_evidence: $insight_evidence, hypotheses: $insight_hypotheses}
        }
      } break

      case ("hypothesis") {
        db.query experiments {
          where = $db.experiments.hypothesis_id == $input.id
          return = {type: "count"}
        } as $hypothesis_experiments

        var.update $refs {
          value = {experiments: $hypothesis_experiments}
        }
      } break

      default {
        throw {
          name = "inputerror"
          value = "UNKNOWN_ENTITY: " ~ $input.entity
        }
      }
    }

    var $total {
      value = ($refs|values)|sum
    }
  }

  response = {total: $total, references: $refs}
}
