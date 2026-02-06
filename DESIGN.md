# Market Moves Narrative Creator - Design Document

## Project Overview

An intelligent agent system that analyzes market movements and generates daily narratives attempting to explain what it observes. The focus is on understanding what market moves reveal about the real economy through an iterative, hypothesis-driven approach.

## Core Principles

1. **Iterative Analysis** - The agent explores data, forms hypotheses, investigates, and refines its understanding before generating narratives
2. **Real Economy Focus** - Prioritize understanding broader economic signals over idiosyncratic moves
3. **Observable Reasoning** - Clear visibility into the agent's hypothesis formation and refinement process
4. **Extensible Architecture** - Easy to add new data sources, analytical approaches, and output formats

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Orchestrator/Scheduler                   │
│              (Triggers daily runs, manages flow)             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Iterative Agent Controller                  │
│           (Multi-phase narrative generation loop)            │
│                                                               │
│  Phase 1: Initial Observation                                │
│  Phase 2: Hypothesis Formation                               │
│  Phase 3: Targeted Investigation                             │
│  Phase 4: Narrative Synthesis                                │
└───────────────┬───────────────────────┬─────────────────────┘
                │                       │
                ▼                       ▼
    ┌──────────────────────┐   ┌──────────────────┐
    │   Data Collection    │   │  Historical      │
    │   Layer              │   │  Context         │
    │                      │   │                  │
    │  - Prices/Returns    │   │  - Past          │
    │  - News              │   │    Narratives    │
    │  - Pred Markets      │   │  - Market        │
    │  - Economic Data     │   │    Patterns      │
    └──────────┬───────────┘   └────────┬─────────┘
               │                        │
               └────────────┬───────────┘
                            │
                            ▼
                   ┌────────────────┐
                   │   LLM Layer    │
                   │  (Multi-model) │
                   └────────┬───────┘
                            │
                            ▼
                   ┌────────────────┐
                   │    Storage     │
                   │ (Data, Cache,  │
                   │  Narratives)   │
                   └────────────────┘
```

---

## Iterative Narrative Generation Workflow

The agent follows a multi-phase approach to generate narratives, refining its understanding at each step:

### Phase 1: Initial Observation
**Goal**: Get a broad view of the market landscape

**Actions**:
- Fetch major asset returns (indices, sectors, key stocks)
- Identify biggest movers (stocks and sectors)
- Get industry/sector returns
- Collect major news headlines
- Note significant volume or volatility spikes

**Output**: Structured summary of market state
```python
MarketSnapshot {
    major_indices: {SPY: +1.2%, QQQ: -0.8%, ...}
    biggest_gainers: [NVDA +5.3%, JPM +3.1%, ...]
    biggest_losers: [TSLA -4.2%, META -3.5%, ...]
    sector_performance: {Tech: -0.5%, Finance: +2.1%, ...}
    market_breadth: {advancers: 1234, decliners: 2345, ...}
    news_count: 47
}
```

### Phase 2: Hypothesis Formation
**Goal**: Generate candidate narratives that could explain observations

**Agent Process**:
1. Analyze patterns in the market snapshot
2. Cross-reference with news headlines
3. Formulate multiple candidate explanations
4. Rank hypotheses by plausibility

**Example Hypotheses**:
- "Tech selloff on rate concerns - Fed speak dominated headlines"
- "Rotation into financials on yield curve steepening"
- "Sector-specific: NVDA earnings beat driving semiconductor rally"
- "Risk-off move: VIX spike, bonds rallying, equities down"

**Output**: Ranked list of candidate narratives with questions
```python
CandidateNarrative {
    hypothesis: str
    supporting_evidence: List[str]
    confidence: float
    questions_to_investigate: List[str]
}
```

### Phase 3: Targeted Investigation
**Goal**: Deep dive into specific data to validate/refine hypotheses

**Agent Actions**:
For each hypothesis, agent decides what to investigate:

1. **Specific Stock Analysis**
   - If hypothesis involves specific companies, fetch detailed moves
   - Look for correlated moves in similar companies
   - Check earnings announcements, guidance changes

2. **News Deep Dive**
   - Search news for keywords from hypothesis
   - Identify key events (Fed speech, earnings, geopolitical)
   - Check timing: did news precede price moves?

3. **Prediction Market Check**
   - Query relevant prediction markets based on hypothesis
   - Example: If "rate concerns" → check Fed rate predictions
   - Example: If "recession fears" → check GDP/recession markets
   - Look for probability changes that align with market moves

4. **Cross-Asset Validation**
   - Check if other assets confirm hypothesis
   - Example: Yields up + dollar up + gold down = rate concerns
   - Example: All sectors down = broad risk-off

**Output**: Enhanced candidates with supporting/refuting evidence
```python
InvestigatedNarrative {
    hypothesis: str
    confidence: float  # updated after investigation
    supporting_evidence: List[Evidence]
    contradicting_evidence: List[Evidence]
    relevant_prediction_markets: List[MarketPrediction]
    key_quotes: List[str]  # from news
}
```

### Phase 4: Narrative Synthesis
**Goal**: Generate final, coherent set of narratives

**Agent Actions**:
1. **Compare with Historical Context**
   - Retrieve past narratives from database
   - Check for recurring themes or contradictions
   - Reference similar market conditions from history
   - Learn from what made past narratives good/bad

2. **Reweight and Refine**
   - Adjust confidence in each narrative
   - Combine related narratives
   - Discard low-confidence hypotheses
   - Identify dominant themes

3. **Generate Final Output**
   - Create coherent narrative structure
   - Primary narrative (main explanation)
   - Secondary themes (contributing factors)
   - Outliers/unexplained moves
   - Forward-looking implications

**Output**: Structured narrative document
```python
DailyNarrative {
    date: datetime
    headline: str
    primary_narrative: str
    supporting_narratives: List[str]
    key_moves_explained: List[AssetStory]
    prediction_market_insights: List[PredictionInsight]
    unexplained_moves: List[str]
    looking_ahead: str
    confidence_score: float
    data_sources: List[str]
}
```

---

## Data Sources

### Core Sources

**Market Data**
- **Equities**: S&P 500, sector ETFs, major stocks
- **Fixed Income**: Treasury yields across curve, corporate spreads
- **Commodities**: Oil, gold (as macro indicators)
- **Volatility**: VIX, options-implied volatility
- **Economic Data**: FRED data (GDP, unemployment, CPI, etc.)

**News & Information**
- Financial news aggregators (RSS feeds, APIs)
- Economic calendars (Fed meetings, data releases)
- Corporate announcements (earnings, guidance)

**Prediction Markets**
- Manifold Markets (wide range of topics)
- Polymarket (if easily accessible)
- Focus areas: Fed policy, recession odds, political events

### Data Collection Strategy

**Pull approach**: Agent decides what data to fetch based on current phase
- Phase 1: Broad market overview (same set of core assets every day)
- Phase 3: Targeted fetches based on hypotheses

**Advantages**:
- Only fetch what's needed
- Agent-driven exploration
- More efficient than "fetch everything"

---

## Agent Design

### Agent Type: Tool-Calling Reasoner

The agent has access to tools and decides which to call based on its current phase and hypotheses.

**Available Tools**:

```python
# Phase 1 Tools (always called)
get_market_overview() -> MarketSnapshot
get_sector_returns(date) -> Dict[str, float]
get_top_movers(n=10, direction="both") -> List[Mover]
get_news_headlines(limit=50) -> List[Headline]

# Phase 3 Tools (called based on hypotheses)
get_stock_details(ticker) -> StockDetails
search_news(keywords, date_range) -> List[Article]
get_prediction_market(query) -> List[Prediction]
get_economic_indicator(indicator_name) -> TimeSeries
get_correlated_moves(ticker, threshold=0.7) -> List[Correlation]
get_yield_curve() -> YieldCurve

# Phase 4 Tools
get_historical_narratives(date_range, similarity_threshold) -> List[Narrative]
compare_market_conditions(date1, date2) -> Comparison
```

### Agent Control Flow

```
while not done:
    current_phase = determine_phase()

    if phase == "observation":
        snapshot = call_observation_tools()
        state.update(snapshot)

    elif phase == "hypothesis":
        candidates = llm.generate_hypotheses(state.snapshot, state.news)
        state.candidates = rank_hypotheses(candidates)

    elif phase == "investigation":
        for hypothesis in state.candidates[:top_n]:
            # Agent decides which tools to call
            investigation_plan = llm.plan_investigation(hypothesis)
            evidence = execute_investigation(investigation_plan)
            hypothesis.update_confidence(evidence)

    elif phase == "synthesis":
        history = get_historical_narratives()
        final = llm.synthesize_narrative(
            state.candidates,
            state.all_evidence,
            history
        )
        return final

    done = llm.should_continue(state)
```

### Multi-Model Strategy

Different models for different phases:
- **Fast model**: Tool selection, data extraction
- **Strong model**: Hypothesis formation, synthesis
- **Configurable**: Easy to swap models per phase

---

## Component Breakdown

### 1. Orchestrator
- Schedules daily runs
- Manages agent lifecycle
- Handles errors and retries
- Logs execution traces

### 2. Agent Controller
- Implements multi-phase loop
- Maintains agent state across phases
- Decides when to move between phases
- Calls LLM with appropriate context

### 3. Data Collection Layer
- Modular collectors for each source
- Caching to avoid redundant API calls
- Standard interface for all collectors
- Async fetching for parallel requests

### 4. LLM Layer
- Provider-agnostic interface
- Support for multiple providers (Anthropic, OpenAI, etc.)
- Structured outputs (Pydantic models)
- Retry logic and error handling

### 5. Storage Layer
- Market data cache (time-series)
- News archive
- Historical narratives
- Agent execution logs

### 6. Analysis Tools
- Statistical anomaly detection
- Correlation analysis
- Pattern matching
- Text similarity for historical comparison

---

## Key Design Decisions

### Why Iterative/Multi-Phase?
- More thorough than single-pass generation
- Agent can course-correct if initial hypotheses weak
- Mimics how human analysts actually work
- Natural place to inject human feedback in future

### Why Hypothesis-Driven Investigation?
- More efficient than exhaustive data collection
- Focuses agent attention on relevant data
- Creates interpretable reasoning chain
- Easy to debug when narratives are wrong

### Why Historical Context in Final Phase?
- Prevents contradicting past analyses
- Enables learning from experience
- Allows referencing similar situations
- Builds institutional memory

### Why Real Economy Focus?
- More valuable insights for decision-making
- Better aligns with prediction markets
- Richer narratives (connects multiple domains)
- More stable patterns over time

---

## Implementation Considerations

### Token Efficiency
- Pre-process data before sending to LLM (reduce tokens)
- Cache LLM responses for identical queries
- Use structured outputs to avoid parsing issues
- Smaller models for routine tasks, larger for reasoning
- Batch related queries when possible

### Free Data Sources
- Prefer free APIs (yfinance, FRED, RSS feeds)
- Use paid APIs only for critical data
- Implement fallbacks if free sources fail
- Monitor usage to stay within free tiers

### Reliability
- Graceful degradation if data sources unavailable
- Retry logic with exponential backoff
- Validation of external data
- Clear error messages and logging

### Observability
- Log each phase transition
- Save intermediate hypotheses
- Track which tools were called and why
- Store agent reasoning traces

---

## Future Extensions

### Enhanced Data Sources
- Social sentiment (Twitter, Reddit)
- Insider trading data (SEC filings)
- Options flow (institutional positioning)
- International markets (global context)
- Satellite data (alternative data)

### Agent Capabilities
- Multi-agent system (specialist agents per domain)
- Memory system (semantic search over past narratives)
- Backtesting (evaluate past narrative accuracy)
- Predictive mode (forecast tomorrow's moves)
- Interactive mode (user asks questions, agent investigates)

### Analysis Sophistication
- Causal graph generation
- Anomaly detection with ML
- Sentiment analysis on news
- Network analysis (company relationships)
- Time-series forecasting

### User Interaction
- Web dashboard with visualizations
- Chat interface for follow-up questions
- Customizable watchlists
- Real-time alerts for significant moves
- API for third-party integration

### Output Formats
- Multiple narrative styles (technical, casual, academic)
- Different lengths (brief, standard, detailed)
- Multi-language support
- Audio/podcast generation
- Automated email/Slack delivery

### Evaluation & Improvement
- Track narrative accuracy over time
- A/B test different agent strategies
- User feedback collection
- Automated fact-checking
- Ensemble of multiple agent approaches

---

## Success Metrics

### Narrative Quality
- Factual accuracy (verifiable claims)
- Completeness (covers major moves)
- Coherence (logical explanation)
- Actionability (useful insights)

### Agent Performance
- Hypothesis refinement (low → high confidence)
- Investigation efficiency (right tools, right time)
- Historical consistency (doesn't contradict self)

### System Reliability
- Uptime / successful daily runs
- Data source availability
- Error recovery
- Runtime (reasonable completion time)

### Extensibility
- Time to add new data source
- Time to add new agent capability
- Configuration-driven behavior

---

## Project Structure

```
market-narrative-agent/
├── README.md
├── DESIGN.md              # This file
├── config.yaml            # System configuration
├── .env.example           # Environment variables template
│
├── src/
│   ├── main.py           # Entry point
│   ├── config.py         # Config loader
│   │
│   ├── orchestrator/     # Daily run orchestration
│   ├── agent/            # Multi-phase agent controller
│   ├── collectors/       # Data collection modules
│   ├── llm/              # LLM abstraction layer
│   ├── tools/            # Agent tools implementation
│   ├── narrative/        # Narrative generation
│   ├── storage/          # Data persistence
│   ├── analysis/         # Statistical analysis utilities
│   └── utils/            # Common utilities
│
├── tests/                # Unit tests
├── outputs/              # Generated narratives
├── logs/                 # Application logs
└── cache/                # Data cache
```

---

## Implementation Roadmap

### Phase 1: Foundation
- Project setup and structure
- Basic data collectors (prices, news)
- Simple storage layer
- Single-phase agent (observation only)

**Deliverable**: Can fetch and store daily market data

### Phase 2: Iterative Agent
- Multi-phase agent controller
- Tool-calling system
- Hypothesis formation
- Targeted investigation

**Deliverable**: Agent can form and investigate hypotheses

### Phase 3: Narrative Generation
- Historical context integration
- Narrative synthesis
- Output formatting
- Quality improvements

**Deliverable**: Complete daily narratives

### Phase 4: Production Readiness
- Orchestration and scheduling
- Error handling and monitoring
- Configuration system
- Documentation

**Deliverable**: Fully automated system

---

## Project Configuration

### Asset Universe
**Indices**: S&P 500, NASDAQ

**Individual Stocks**: MAG7 (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA)

**Sector ETFs**: XLF (Finance), XLE (Energy), XLK (Tech), XLV (Healthcare), XLI (Industrials), XLY (Consumer Discretionary), XLP (Consumer Staples), XLB (Materials), XLRE (Real Estate), XLU (Utilities), XLC (Communications)

**Commodities**: Oil (CL=F), Gold (GC=F)

**Volatility**: VIX

**Treasury Rates**: 2-year, 5-year, 10-year, 30-year

### Narrative Style
**Default**: Journalistic style
- Clear, concise explanations
- Fact-based with supporting evidence
- Professional tone suitable for informed readers
- Future: Can add academic or casual variants

### Scheduling
**Timing**: 9:45 AM ET (15 minutes after market open)
- Captures opening moves and overnight news
- Early enough to be actionable for the trading day
- Allows for intraday follow-ups if needed

### Distribution
**Format**: File output (markdown and JSON)
- Saved to `outputs/YYYY-MM-DD/narrative.md`
- Structured data in `outputs/YYYY-MM-DD/narrative.json`
- Future: Email, Slack, web dashboard

### Automation
**Human-in-Loop**: No
- Fully automated generation and publishing
- Agent runs autonomously each trading day
- Manual review optional but not required

---

## Next Steps

1. Review and refine this design
2. Set up initial project structure
3. Begin Phase 1 implementation
4. Iterate based on early results
