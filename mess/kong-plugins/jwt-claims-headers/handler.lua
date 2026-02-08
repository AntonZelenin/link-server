local jwt_decoder = require "kong.plugins.jwt.jwt_parser"
local req_set_header = ngx.req.set_header
local ngx_re_gmatch = ngx.re.gmatch

local plugin = {
    PRIORITY = 1000,
    VERSION = "0.1",
}

local function retrieve_token(request, conf)
    local uri_parameters = request.get_uri_args()

    for _, v in ipairs(conf.uri_param_names) do
        if uri_parameters[v] then
            return uri_parameters[v]
        end
    end

    local authorization_header = request.get_headers()["authorization"]
    if authorization_header then
        local iterator, iter_err = ngx_re_gmatch(authorization_header, "\\s*[Bb]earer\\s+(.+)")
        if not iterator then
            return nil, iter_err
        end

        local m, err = iterator()
        if err then
            return nil, err
        end

        if m and #m > 0 then
            return m[1]
        end
    end
end

function plugin:access(plugin_conf)
    local token, err = retrieve_token(ngx.req, plugin_conf)
    if err and not plugin_conf.continue_on_error then
        kong.log.err(err)
        return kong.response.exit(500, { message = "Internal Server Error" })
    end

    if not token and not plugin_conf.continue_on_error then
        return kong.response.exit(401, { message = "Unauthorized" })
    elseif not token and plugin_conf.continue_on_error then
        return
    end

    local jwt, err = jwt_decoder:new(token)
    if err and not plugin_conf.continue_on_error then
        kong.log.err(err)
        return kong.response.exit(500, { message = "Internal Server Error" })
    end

    local claims = jwt.claims
    for claim_key, claim_value in pairs(claims) do
        for _, claim_pattern in pairs(plugin_conf.claims_to_include) do
            --the commented string does not work with hyphens. If you have a key in config like user-id, it won't include it
            --if string.match(claim_key, "^" .. claim_pattern .. "$") then
            if claim_key == claim_pattern then
                req_set_header("X-" .. claim_key, claim_value)
            end
        end
    end
end

return plugin
