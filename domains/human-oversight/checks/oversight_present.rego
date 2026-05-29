package govops.oversight

# Require non-empty oversight fields on every high-risk system.
default complete := false

complete := true if {
    input.human_oversight.mode != ""
    input.human_oversight.override_path != ""
    input.human_oversight.escalation_sla != ""
}

violations[msg] {
    not input.human_oversight.mode
    msg := "human_oversight.mode is required"
}
