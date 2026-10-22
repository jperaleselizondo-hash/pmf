// PMF Engine: allow only the designated owner (env PMF_OWNER_USER_ID); fails closed
function "pmf/auth/require_owner" {
  description = "Allow only the designated PMF owner"
  input {
    int? auth_id
  }

  stack {
    var $configured {
      value = $env.PMF_OWNER_USER_ID
    }

    precondition ($configured != null && (($configured|to_text)|trim) != "") {
      error_type = "standard"
      error = "OWNER_NOT_CONFIGURED: the designated owner is not configured"
    }

    var $owner_id {
      value = $configured|to_int
    }

    precondition ($input.auth_id != null && $input.auth_id == $owner_id) {
      error_type = "accessdenied"
      error = "NOT_OWNER: this account is not authorized"
    }
  }

  response = $owner_id
  guid = "R1GD_pgZWUgY4mr6bq7743W7AL4"
}
