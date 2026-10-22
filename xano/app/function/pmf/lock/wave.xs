// PMF Engine: INTENDED serialization point for writes on one survey wave (UNVERIFIED, U13)
// Called first inside db.transaction. The rewrite of an unchanged column is an attempt to take a row lock
// held until commit; there is NO runtime evidence yet that Xano issues the UPDATE (it may skip unchanged
// values) or that the transaction holds the lock. Deployment is blocked until the isolated repeated-trial
// tests C01/C03 pass with concurrent overlap AND a negative control (this lock disabled) shows they fail.
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
      data = {name: $wave.name}
    } as $locked
  }

  response = $locked
  guid = "arQgFLYwEHU20r_ASVEly4auF-w"
}
