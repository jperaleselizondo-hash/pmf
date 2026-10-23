// PMF Engine: serialization point for writes on one survey wave (U13, PROPOSED FIX)
// Called first inside db.transaction. The former unchanged-column rewrite did not serialize insights
// (C02/C04); this version performs a REAL row change (`updated_at = now`) to take the row lock until commit.
// Verified only if C01/C03 pass with full overlap; C01 is also protected by the unique (wave, customer) index.
function "pmf/lock/wave" {
  description = "Lock a survey wave row and return its current state"
  input {
    int wave_id
  }

  stack {
    db.get survey_waves {
      field_name = "id"
      field_value = $input.wave_id
    } as $wave

    precondition ($wave != null) {
      error_type = "notfound"
      error = "NOT_FOUND: survey wave not found"
    }

    db.edit survey_waves {
      field_name = "id"
      field_value = $input.wave_id
      data = {updated_at: now}
    } as $locked
  }

  response = $locked
  guid = "arQgFLYwEHU20r_ASVEly4auF-w"
}
