# I Ran My Own ChatGPT for a Month. Here's What It Actually Cost.

*[DRAFT — fill in real numbers after running the experiment]*

---

Everyone talks about the privacy angle of self-hosted AI. Nobody talks about the math.

I wanted to know: at what point does running your own model make more financial sense than paying OpenAI? I ran Qwen2.5 on a cloud GPU for a month and logged every request. Here's what I found.

---

## The Setup

- **Model:** Qwen2.5-7B-Instruct, 4-bit quantization
- **Hardware:** RunPod RTX 4090 (24GB VRAM)
- **Cost:** $0.69/hr
- **Interface:** Gradio web UI, password protected
- **Users:** [X people over 30 days]

Monthly cost at full uptime: **$0.69 × 24 × 30 = $496.80**

That's the number that stops most people. But it's the wrong number to look at.

---

## The Real Cost: Idle Time

A GPU running 24/7 costs the same whether it's answering questions or sitting idle. The question isn't "what does it cost per month" — it's "what does it cost per request."

```
[INSERT: chart of requests per hour — shows usage clustered in evenings,
dead from 2am-8am]
```

**[X]% of the time, nobody was using it.**

That changes the math entirely. If you only run the pod when people are actually online:

- Active hours per day: ~[X] hrs
- Monthly cost at actual usage: **$[Y]**

---

## Compared to the API

For the same volume of requests, OpenAI would have cost:

| Model | Input cost | Output cost | Total for [X] requests |
|-------|-----------|-------------|----------------------|
| GPT-4o | $5/1M tokens | $15/1M tokens | $[calculated] |
| GPT-4o-mini | $0.15/1M tokens | $0.60/1M tokens | $[calculated] |
| Self-hosted (7B) | — | — | $[calculated] |

*[Fill in after collecting usage_log.csv data]*

---

## What I Actually Learned

**The break-even point isn't where you think it is.**

At low usage (a few people, occasional questions), the API is cheaper. The math flips when you have consistent high-volume usage — or when you factor in things that don't show up in a spreadsheet: data privacy, no rate limits, the ability to fine-tune on your own data.

**Quality matters more than cost at this scale.**

The 7B model is good enough for most tasks. It's not GPT-4o. For anything requiring deep reasoning or long context, you feel the difference. For summarization, drafting, Q&A — it holds up.

**The operational overhead is real.**

Pods go down. Downloads fail. Disk fills up. None of this is hard to fix once you know what you're doing, but it's time. Factor that in.

---

## The Numbers You Actually Need

To run this experiment yourself, you need to track:

1. **Requests per day** — how much is it actually being used?
2. **Tokens per request** — input + output, determines API comparison cost
3. **Uptime vs. idle time** — where your money is actually going
4. **Response latency** — is it fast enough to be useful?

All of this is in `/workspace/usage_log.csv` if you run the logging version of the inference script.

---

## Should You Do It?

**Yes, if:**
- You have consistent high-volume usage
- Privacy is non-negotiable (medical, legal, personal data)
- You want to fine-tune on your own data
- You're learning how this stuff works

**No, if:**
- Usage is sporadic
- You need GPT-4 quality
- You don't want to deal with infrastructure

---

*[Data collected over 30 days starting [DATE]. Full usage log and inference script at [github link].]*
