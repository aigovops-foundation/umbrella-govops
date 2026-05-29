package govops.data

# Deny if any feature in the model's feature list is a protected attribute.
# Input shape:
# {
#   "features": ["age", "income", "zip"],
#   "protected_attributes": ["race", "gender", "age"]
# }

default no_direct_protected_features := true

no_direct_protected_features := false if {
    some f
    f := input.features[_]
    f == input.protected_attributes[_]
}

violations[msg] {
    some f
    f := input.features[_]
    f == input.protected_attributes[_]
    msg := sprintf("feature %q is a protected attribute and cannot be used directly", [f])
}
