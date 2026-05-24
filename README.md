# ChurnShield

Autonomous churn intervention engine. Intercepts cancellation requests in real-time, scores churn risk from behavioral signals, classifies users into segments, selects the best retention offer via Thompson Sampling, and generates personalized messages via Claude API or smart templates.

Built across 4 verticals: B2B SaaS, Streaming, Fitness, and Marketplace -- same engine, different segments and signals per domain.

## How It Works

```
User triggers cancel
        |
        v
Behavioral features computed from Redis event stream
(engagement decay, login recency, feature adoption,
support intensity, payment reliability)
        |
        v
GradientBoostingClassifier scores churn risk (0-1)
+ feature importances explain why
        |
        v
Rule-based segmentation classifies the user
(e.g. underutilizer, price_sensitive, binge_cliff)
        |
        v
Thompson Sampling bandit selects best offer per segment
(learns from accepted/rejected outcomes over time)
        |
        v
Message generated via Claude API (or template fallback)
        |
        v
Outcome recorded, bandit distributions updated
```

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI + Python 3.11 |
| Database | PostgreSQL |
| Cache / Event Store | Redis sorted sets |
| ML | scikit-learn GradientBoostingClassifier |
| Offer Selection | Thompson Sampling (Beta-Bernoulli bandit) |
| LLM | Anthropic Claude API (optional) |
| Frontend | React + Vite + Tailwind CSS + Recharts |
| Infrastructure | Docker Compose |

## Quick Start

```bash
git clone <repo>
cd churner

# Optional: add Claude API key for LLM-generated messages
export ANTHROPIC_API_KEY=sk-ant-...

docker compose up --build
```

- **App:** http://localhost:3000
- **API docs:** http://localhost:8000/docs

On first boot the backend automatically seeds 500 synthetic users (125 per vertical) and trains 4 ML models. Takes about 60-90 seconds.

## Verticals

| Vertical | Segments |
|----------|----------|
| B2B SaaS | price_sensitive, underutilizer, frustrated, disengaged, at_risk |
| Streaming | binge_cliff, passive_subscriber, content_mismatch, price_shopper, at_risk |
| Fitness | guilt_churn, plateau, hobbyist_cliff, seasonal_dropper, at_risk |
| Marketplace | bad_experience, frequency_decay, competitor_switch, promo_dependent, at_risk |

## Feature Vector (per user)

| Feature | Description |
|---------|-------------|
| engagement_decay | (sessions_30d - sessions_prev_30d) / sessions_prev_30d |
| login_recency_days | days since last login |
| feature_adoption | features_used / total_features |
| support_intensity | support tickets in last 30 days |
| payment_reliability | 1 - (payment_failures / 5) |
| plan_value | monthly_spend / baseline |
| engagement_velocity | rate of change in engagement (vertical-specific) |

Extra signals computed per vertical from Redis (e.g. content velocity for streaming, order frequency for marketplace).

## Bandit

Each segment-offer pair has a Beta(alpha, beta) distribution initialized at Beta(1,1). On each cancellation the system samples from all distributions and picks the highest. On outcome:

- Accepted: alpha += 1
- Rejected: beta += 1

Over time the bandit converges on the offers that convert best per segment without requiring a fixed exploration schedule.

## LLM Mode

Works fully without an API key using hand-crafted templates. To enable Claude:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Each intervention records `message_source: "llm" | "template"` visible in the UI.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/users?vertical=b2b_saas` | List users for a vertical |
| POST | `/api/users/{id}/cancel` | Trigger churn intervention |
| POST | `/api/interventions/{id}/respond` | Record accepted / rejected outcome |
| GET | `/api/analytics?vertical=b2b_saas` | Dashboard stats |
| GET | `/api/verticals` | List all verticals and their segments |
| POST | `/api/seed?vertical=b2b_saas` | Re-seed one or all verticals |
| GET | `/health` | Health check |

## Reset Demo

Click **Reset Demo** in the header or run:

```bash
curl -X POST http://localhost:8000/api/seed
```

Clears all users, events, interventions, and bandit stats, then re-seeds 500 fresh users.

## Deploy

For production deployment, use the production Docker files in this repo:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

Full guide: [DEPLOYMENT.md](/Users/vanshika/churner/DEPLOYMENT.md)
