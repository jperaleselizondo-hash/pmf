// PMF Engine: aggregate participation rows into survey counts (pure)
// valid = responded_at AND disappointment_level; incomplete = responded_at without category;
// anomaly = category without responded_at (never scored).
function "pmf/report/count_wave" {
  description = "Count eligible, invited, responded, valid and category totals"
  input {
    json rows
  }

  stack {
    var $rows {
      value = $input.rows ?? []
    }

    var $invited {
      value = $rows|filter:$$.invited_at != null
    }

    var $responded {
      value = $rows|filter:$$.responded_at != null
    }

    var $valid {
      value = $rows|filter:$$.responded_at != null && $$.disappointment_level != null
    }

    var $incomplete {
      value = $rows|filter:$$.responded_at != null && $$.disappointment_level == null
    }

    var $anomaly {
      value = $rows|filter:$$.responded_at == null && $$.disappointment_level != null
    }

    var $very {
      value = $valid|filter:$$.disappointment_level == "very"
    }

    var $somewhat {
      value = $valid|filter:$$.disappointment_level == "somewhat"
    }

    var $not {
      value = $valid|filter:$$.disappointment_level == "not"
    }

    var $invited_valid {
      value = $valid|filter:$$.invited_at != null
    }

    var $unsegmented {
      value = $rows|filter:$$.segment_id_snapshot == null
    }
  }

  response = {
    eligible_count        : ($rows|count)
    invited_count         : ($invited|count)
    responded_count       : ($responded|count)
    valid_response_count  : ($valid|count)
    incomplete_response_count: ($incomplete|count)
    anomaly_count         : ($anomaly|count)
    very_count            : ($very|count)
    somewhat_count        : ($somewhat|count)
    not_count             : ($not|count)
    invited_valid_count   : ($invited_valid|count)
    manual_valid_count    : ($valid|count) - ($invited_valid|count)
    unsegmented_count     : ($unsegmented|count)
  }

  test "fixture wave W1" {
    input = {
      rows: [
        {customer_id: 1, segment_id_snapshot: 11, invited_at: 1, responded_at: 2, disappointment_level: "very"}
        {customer_id: 2, segment_id_snapshot: 11, invited_at: 1, responded_at: 2, disappointment_level: "somewhat"}
        {customer_id: 3, segment_id_snapshot: 12, invited_at: 1, responded_at: null, disappointment_level: null}
        {customer_id: 4, segment_id_snapshot: 12, invited_at: 1, responded_at: null, disappointment_level: null}
        {customer_id: 5, segment_id_snapshot: null, invited_at: null, responded_at: 2, disappointment_level: "not"}
      ]
    }

    expect.to_equal ($response.eligible_count) {
      value = 5
    }

    expect.to_equal ($response.invited_count) {
      value = 4
    }

    expect.to_equal ($response.valid_response_count) {
      value = 3
    }

    expect.to_equal ($response.very_count) {
      value = 1
    }

    expect.to_equal ($response.invited_valid_count) {
      value = 2
    }

    expect.to_equal ($response.manual_valid_count) {
      value = 1
    }

    expect.to_equal ($response.unsegmented_count) {
      value = 1
    }
  }

  test "incomplete and anomaly are never valid" {
    input = {
      rows: [
        {responded_at: 2, disappointment_level: null}
        {responded_at: null, disappointment_level: "very"}
      ]
    }

    expect.to_equal ($response.valid_response_count) {
      value = 0
    }

    expect.to_equal ($response.incomplete_response_count) {
      value = 1
    }

    expect.to_equal ($response.anomaly_count) {
      value = 1
    }
  }
  guid = "MGCFw79MKQA-FknJTp3ijswRdng"
}
