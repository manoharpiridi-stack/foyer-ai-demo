from backend.llm import Usage


def test_cost_estimate_uses_price_per_million_tokens():
    usage = Usage(input_tokens=1_000_000, output_tokens=1_000_000, embedding_tokens=1_000_000)
    assert usage.summary()["cost_usd"] == 0.40 + 1.60 + 0.02


def test_no_tokens_costs_nothing():
    assert Usage().summary()["cost_usd"] == 0
