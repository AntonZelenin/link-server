return {
  name = "jwt-claims-headers",
  fields = {
    { config = {
        type = "record",
        fields = {
          { uri_param_names = {
              type = "array",
              default = {"jwt"},
              elements = { type = "string" },
            }
          },
          { claims_to_include = {
              type = "array",
              default = {".*"},
              elements = { type = "string" },
            }
          },
          { continue_on_error = { type = "boolean", default = false } },
        },
      },
    },
  },
}