"""JSON schema used to enforce LLM extraction output format."""

EXTRACTION_SCHEMA = {
    "type": "object",
    "required": ["income_statement", "balance_sheet"],
    "properties": {
        "income_statement": {
            "type": "object",
            "required": ["periods", "revenue", "cost_of_goods_sold", "gross_profit",
                         "operating_expenses", "ebit", "interest_expense", "ebt",
                         "income_tax", "net_income"],
            "properties": {
                "periods": {
                    "type": "array",
                    "items": {"type": "object", "required": ["year", "label"],
                               "properties": {"year": {"type": "integer"}, "label": {"type": "string"}}}
                },
                "revenue":             {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "cost_of_goods_sold":  {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "gross_profit":        {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "operating_expenses":  {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "ebit":                {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "interest_expense":    {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "ebt":                 {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "income_tax":          {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "net_income":          {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "depreciation_amortization": {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "ebitda":              {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
            }
        },
        "balance_sheet": {
            "type": "object",
            "required": ["periods", "cash", "accounts_receivable", "inventory",
                         "other_current_assets", "current_assets", "fixed_assets",
                         "other_noncurrent_assets", "total_assets", "accounts_payable",
                         "short_term_debt", "other_current_liabilities", "current_liabilities",
                         "long_term_debt", "other_noncurrent_liabilities", "total_liabilities",
                         "share_capital", "retained_earnings", "total_equity"],
            "properties": {
                "periods": {
                    "type": "array",
                    "items": {"type": "object", "required": ["year", "label"],
                               "properties": {"year": {"type": "integer"}, "label": {"type": "string"}}}
                },
                "cash":                       {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "accounts_receivable":        {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "inventory":                  {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "other_current_assets":       {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "current_assets":             {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "fixed_assets":               {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "other_noncurrent_assets":    {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "total_assets":               {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "accounts_payable":           {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "short_term_debt":            {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "other_current_liabilities":  {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "current_liabilities":        {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "long_term_debt":             {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "other_noncurrent_liabilities": {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "total_liabilities":          {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "share_capital":              {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "retained_earnings":          {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "total_equity":               {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
            }
        },
        "cash_flow_statement": {
            "type": ["object", "null"],
            "properties": {
                "periods": {
                    "type": "array",
                    "items": {"type": "object", "required": ["year", "label"],
                               "properties": {"year": {"type": "integer"}, "label": {"type": "string"}}}
                },
                "operating_cash_flow":  {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "investing_cash_flow":  {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "financing_cash_flow":  {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
                "free_cash_flow":       {"type": "object", "additionalProperties": {"type": ["number", "null"]}},
            }
        },
        "company_name":       {"type": "string"},
        "currency":           {"type": "string"},
        "nace_code":          {"type": "string"},
        "reporting_standard": {"type": "string"},
    }
}
