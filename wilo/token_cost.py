"""What a model call costs, from the usage the API reports. Used by the chat's spend cap (wilo/chat.py) and the
token report (scripts/token-cost/usage_report.py). Update PRICES if Anthropic's change."""

# $ per million tokens: input, output, cache read, cache write 5 min (1.25x input), cache write 1 hour (2x input)
PRICES = {'claude-sonnet-5-5': (2.00, 10.00, 0.20, 2.50, 4.00),
          'claude-opus-5-5': (4.00, 20.00, 0.20, 5.00, 8.00),
          # RunPod's public Kimi endpoint (#228); no cache pricing used, every input token counts at full price
          'kimi-k2.6': (0.95, 4.00, 0.95, 0.95, 0.95),
          'kimi-k3.1-pro': (2.00, 10.00, 2.00, 2.00, 2.00)}


def tokens(u):
    """(in, read, write 5 min, write 1 hour, out) from one call's usage."""
    write = u.get('cache_creation_input_tokens') or 0
    split = u.get('cache_creation') or {}
    w5, w1 = split.get('ephemeral_5m_input_tokens'), split.get('ephemeral_1h_input_tokens')
    if w5 is None and w1 is None:
        w5, w1 = 0, write  # no split reported: the chat caches for 1 hour
    return u.get('input_tokens') or 0, u.get('cache_read_input_tokens') or 0, w5 or 0, w1 or 0, u.get('output_tokens') or 0


def dollars(model, t):
    """Cost of one call, or None for a model with no price."""
    p = next((v for k, v in PRICES.items() if model.startswith(k)), None)
    if p is None:
        return None
    i, r, w5, w1, o = t
    return (i * p[0] + o * p[1] + r * p[2] + w5 * p[3] + w1 * p[4]) / 1e6


def call_cost(call):
    """Cost of one saved call ({model, usage}). A model with no price counts at the dearest price, so a cap can't
    leak through a model nobody priced."""
    t = tokens(call.get('usage', {}))
    cost = dollars(call.get('model', ''), t)
    return cost if cost is not None else max(dollars(m, t) for m in PRICES)
