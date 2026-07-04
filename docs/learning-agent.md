# Learning Agent

`LearningAgent` turns historical Shorts analytics into future content strategy.
It analyzes high-performing videos, extracts winning hooks, topics, posting
times, and formats, then stores the learning run in the `learning_feedback`
table.

## What It Learns

- Winning hooks: reusable hook patterns such as curiosity questions, numbered
  payoffs, mistake warnings, hidden truths, contrast loops, and direct benefits.
- Winning topics: topics and keywords attached to the strongest videos.
- Winning posting times: UTC day/hour windows from published or uploaded videos.
- Best performing formats: duration/aspect/format buckets such as
  `fast_cut_vertical` or explicit `metadata.format` values.

## Recommendation Output

The result includes:

- `next_topics`
- `hook_templates`
- `posting_schedule`
- `format_defaults`
- `generation_hints`
- `confidence`

`generation_hints` is designed to be passed into trend, script, visual, SEO, or
upload scheduling steps so future content automatically uses proven patterns.

## Usage

```python
from app.agents.learning import LearningAgent

agent = LearningAgent.from_session(db_session)
result = await agent.run_learning_cycle()

generation_context = agent.recommend_generation_context(
    result,
    base_context={"audience": "solo creators"},
)
```

The agent stores:

- one aggregate `learning_run` record with the full recommendation bundle
- focused `winning_hook` records
- focused `winning_topic` records
- focused `winning_posting_time` records
- focused `best_format` records

## Configuration

- `LEARNING_LOOKBACK_DAYS`
- `LEARNING_TOP_N`
- `LEARNING_MAX_SAMPLES`
- `LEARNING_MIN_VIEWS`
- `LEARNING_MODEL_VERSION`
