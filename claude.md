# Claude Context Document - Market Narrative Agent

**Last Updated**: 2026-02-06 (Evening)
**Project Status**: Phase 3 Complete - Output formatting and storage layer implemented. Agent generates daily narratives with markdown/JSON outputs and SQLite persistence. Ready for Phase 4 (Optimization & Production Deployment)

---

## Project Overview

**Name**: Market Narrative Agent
**Purpose**: An intelligent agent that analyzes market movements and generates daily narratives attempting to explain what it observes through an iterative, hypothesis-driven approach.

**Core Value**: Understanding what market moves reveal about the real economy (not just technical price action).

---

## Environment Setup

### Python Environment
- **Python Version**: 3.9.6
- **Environment**: `model_project` (user-managed)
- **Activate environment**: `source model_project/bin/activate`
- **Working Directory**: `/Users/mikezhu/Documents/SIPA/Building AI Tools/model_project`

### Dependencies Installed
All dependencies successfully installed via pip:
- **Agent Framework**: langchain (0.3.27), langchain-openai (0.3.35), langchain-anthropic (0.3.22), langgraph (0.6.11)
- **Data Collection**: yfinance (1.1.0), httpx (0.28.1), feedparser (6.0.12), beautifulsoup4 (4.14.3)
- **Data Processing**: pandas (2.3.3), numpy (2.0.2), pydantic (2.12.5)
- **Storage**: aiosqlite (0.22.1), sqlalchemy (2.0.46)
- **Utilities**: loguru (0.7.3), tenacity (9.1.2), pyyaml (6.0.3), python-dotenv (1.2.1)
- **Dev Tools**: pytest (8.4.2), black (25.11.0), ruff (0.15.0), ipython (8.18.1)

### API Keys Configured
- ✅ OpenAI API key (set in .env)
- ✅ Anthropic API key (set in .env)
- ✅ NewsAPI key (set in .env)

---

## Configuration Decisions

### Asset Universe (config.yaml)
**Indices**: S&P 500 (^GSPC), NASDAQ (^IXIC)

**Individual Stocks (MAG7)**:
- AAPL (Apple), MSFT (Microsoft), GOOGL (Alphabet)
- AMZN (Amazon), NVDA (NVIDIA), META (Meta), TSLA (Tesla)

**Sector ETFs (11 sectors)**:
- XLF (Financials), XLE (Energy), XLK (Technology)
- XLV (Healthcare), XLI (Industrials), XLY (Consumer Discretionary)
- XLP (Consumer Staples), XLB (Materials), XLRE (Real Estate)
- XLU (Utilities), XLC (Communications)

**Commodities**: Oil (CL=F), Gold (GC=F)

**Volatility**: VIX (^VIX)

**Treasury Rates**: 2-year, 5-year, 10-year, 30-year (need special handling from FRED/Treasury.gov)

### LLM Configuration
- **Provider**: OpenAI
- **Primary Model**: gpt-5.2
- **Fast Model**: gpt-5-mini
- **Max Tokens**: 4000
- **Temperature**: 0.7

### Processing Thresholds
- **Significance Threshold**: 3% price move
- **Volume Threshold**: 1.5x average volume
- **Max Assets Analyzed**: 10 per day

### Scheduling & Distribution
- **Run Time**: 9:45 AM ET (15 minutes after market open)
- **Output Format**: Markdown + JSON files
- **Output Location**: `./outputs/YYYY-MM-DD/`
- **Human-in-Loop**: No (fully automated)
- **Narrative Style**: Journalistic (clear, fact-based, professional)

---

## Project Structure

```
market-narrative-agent/
├── DESIGN.md              # Detailed architecture document
├── README.md              # Project documentation
├── CLAUDE.md              # This context file
├── config.yaml            # Application configuration
├── pyproject.toml         # Python project & dependencies
├── .env                   # API keys (gitignored)
├── .gitignore             # Git ignore rules
│
├── src/
│   ├── __init__.py        # Package init (version: 0.1.0)
│   ├── main.py            # Entry point
│   ├── config.py          # Configuration loader
│   │
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   └── orchestrator.py     # ✅ Orchestrates daily runs with output/DB saving
│   │
│   ├── agent/             # ✅ COMPLETE - Multi-phase agentic workflow
│   │   ├── __init__.py
│   │   ├── controller.py       # ✅ Agent controller with state persistence
│   │   ├── graph.py            # ✅ LangGraph 4-phase workflow
│   │   ├── state.py            # ✅ State management (includes headline field)
│   │   └── tools.py            # ✅ Tool implementations (8 tools)
│   │
│   ├── collectors/        # ✅ COMPLETE - Data collection
│   │   ├── __init__.py
│   │   ├── base.py             # ✅ Base DataCollector class
│   │   ├── price.py            # ✅ Price data (yfinance)
│   │   ├── news.py             # ✅ News (RSS + NewsAPI)
│   │   └── prediction.py       # ✅ Prediction markets (Manifold + Polymarket)
│   │
│   ├── analysis/          # ✅ COMPLETE - Statistical analysis
│   │   ├── __init__.py
│   │   └── processor.py        # ✅ Market snapshots, movers, breadth
│   │
│   ├── storage/           # ✅ COMPLETE - Data models & database
│   │   ├── __init__.py
│   │   ├── models.py           # ✅ Pydantic models (DailyNarrative, MarketSnapshot, etc.)
│   │   └── database.py         # ✅ SQLite async database layer
│   │
│   ├── output/            # ✅ COMPLETE - Output formatting
│   │   ├── __init__.py
│   │   └── formatter.py        # ✅ Markdown + JSON formatters, file writer
│   │
│   └── utils/             # Utilities (if needed)
│
├── tests/                 # ✅ 69 tests passing
├── outputs/               # ✅ Generated narratives
│   └── YYYY-MM-DD/
│       ├── narrative.md        # ✅ Research note style markdown (3.6 KB)
│       ├── narrative.json      # ✅ Full DailyNarrative structure (3.5 KB)
│       └── agent_logs.txt      # ✅ Complete execution logs (21+ KB)
├── data/                  # ✅ Persistent storage
│   └── narratives.db           # ✅ SQLite database (28+ KB)
├── logs/                  # Application logs (legacy)
└── cache/                 # Data cache (in-memory for now)
```

**Note**: Removed `src/llm/` (using LangChain), `src/tools/` (consolidated into agent/tools.py), and `src/narrative/` (integrated into synthesis_node in agent/graph.py)

---

## Output Format & Examples

### Daily Output Structure
Each day generates files in `outputs/YYYY-MM-DD/`:

**1. narrative.md** (Research Note Style)
```markdown
# [Headline generated by LLM]

**Date:** YYYY-MM-DD
**Confidence Score:** XX%

---

## Executive Summary
[First paragraph of primary narrative - concise overview]

## Detailed Analysis
[Full primary narrative - 2-3 paragraphs explaining main story]

## Key Supporting Evidence
- [Supporting point 1]
- [Supporting point 2]
- [Supporting point 3-4]

## Unexplained Movements
- [Moves that don't fit main narrative]

## Looking Ahead
[Forward-looking insights, what to watch]

---

## Methodology
**Data Sources:** [yfinance, RSS feeds, NewsAPI, etc.]
**Analysis Details:**
- Hypotheses generated: X
- Hypotheses investigated: X
- Tools used: X
```

**2. narrative.json** (Structured Data)
```json
{
  "date": "2026-02-06T...",
  "headline": "...",
  "primary_narrative": "...",
  "supporting_narratives": [...],
  "key_moves_explained": [...],
  "prediction_market_insights": [...],
  "unexplained_moves": [...],
  "looking_ahead": "...",
  "confidence_score": 0.82,
  "data_sources": [...],
  "metadata": {
    "tools_used": [...],
    "num_hypotheses": 5,
    "num_investigations": 2
  }
}
```

**3. agent_logs.txt** (Full Execution Log)
- Complete trace of 4-phase workflow
- All tool calls with arguments and results
- Hypothesis generation and ranking
- Investigation details and evidence gathering
- LLM reasoning at each phase
- Timestamps for performance analysis

### Example Output (2026-02-06 - Latest Run)
- **Headline**: "Tech-led rally slashes VIX; gold jumps"
- **Confidence**: 75%
- **Key Insights**:
  - Risk-on rebound with VIX -18.4% to 17.8
  - Tech leadership: XLK +4.1%, NVDA +7.9%, driven by Jensen Huang's "$660B capex buildout sustainable" comments
  - Broad market strength (S&P +2.0%, Nasdaq +2.2%, 18 advancers vs 5 decliners)
  - Mega-cap dispersion: NVDA/MSFT/TSLA strong while AMZN -5.6%, GOOGL -2.5%, META -1.3%
  - Unexplained: Gold +2.6% on 4.7x volume despite risk-on equity tone
- **Hypotheses Investigated**: 2 of 5 (Relief rally + AI/semiconductor catalyst)
- **Tools Used**: 11 total (no redundant calls)
- **Data Sources**: 6 RSS feeds (CNBC, FT, Bloomberg) + NewsAPI, 10+ prediction markets
- **Execution Time**: ~90 seconds
- **Output Files**: 4 (narrative.md with tables, narrative.json, market_snapshot.json, agent_logs.txt)

---

## Key Design Principles (from DESIGN.md)

### 1. Iterative Narrative Generation (4-Phase Workflow)

**Phase 1: Initial Observation**
- Fetch major asset returns (indices, sectors, key stocks)
- Identify biggest movers and volume spikes
- Collect major news headlines
- Output: MarketSnapshot with structured summary

**Phase 2: Hypothesis Formation**
- Analyze patterns in market snapshot
- Cross-reference with news headlines
- Generate multiple candidate narratives
- Rank hypotheses by plausibility
- Output: Ranked CandidateNarrative list with questions to investigate

**Phase 3: Targeted Investigation**
- For each hypothesis, agent decides what to investigate:
  - Specific stock analysis (correlated moves, earnings)
  - News deep dive (keyword search, timing analysis)
  - Prediction market check (Fed rates, recession odds)
  - Cross-asset validation (yields, dollar, gold)
- Output: InvestigatedNarrative with supporting/contradicting evidence

**Phase 4: Narrative Synthesis**
- Compare with historical narratives
- Reweight and refine hypotheses
- Combine related narratives
- Generate final coherent output
- Output: DailyNarrative with confidence scores

### 2. Agent Design Pattern: Tool-Calling Reasoner

Agent has access to tools and decides which to call based on phase:

**Phase 1 Tools (always called)**:
- `get_market_overview()` → MarketSnapshot
- `get_sector_returns(date)` → Dict[str, float]
- `get_top_movers(n=10)` → List[Mover]
- `get_news_headlines(limit=50)` → List[Headline]

**Phase 3 Tools (called based on hypotheses)**:
- `get_stock_details(ticker)` → StockDetails
- `search_news(keywords, date_range)` → List[Article]
- `get_prediction_market(query)` → List[Prediction]
- `get_economic_indicator(name)` → TimeSeries
- `get_correlated_moves(ticker, threshold)` → List[Correlation]
- `get_yield_curve()` → YieldCurve

**Phase 4 Tools**:
- `get_historical_narratives(date_range, similarity)` → List[Narrative]
- `compare_market_conditions(date1, date2)` → Comparison

### 3. Data Sources (Prioritizing Free APIs)

**Price Data**:
- yfinance (free, unlimited) - stocks, indices, ETFs
- CoinGecko API (free tier) - crypto (de-emphasized)
- Alpha Vantage (free: 25 calls/day) - backup for stocks

**News**:
- RSS Feeds (free, unlimited) - Reuters, CNBC, FT
- NewsAPI (free: 100 requests/day) - keyword search
- Google News RSS, Hacker News API

**Prediction Markets**:
- Manifold Markets API (free, unlimited)
- Polymarket (via Gamma API, free tier)

**Economic Data**:
- FRED API (free) - GDP, unemployment, CPI
- Treasury.gov (free) - yield curve data

### 4. Why This Design?

**Iterative/Multi-Phase**:
- More thorough than single-pass generation
- Agent can course-correct if initial hypotheses weak
- Mimics how human analysts work
- Natural place to inject human feedback in future

**Hypothesis-Driven Investigation**:
- More efficient than exhaustive data collection
- Focuses agent attention on relevant data
- Creates interpretable reasoning chain
- Easy to debug when narratives are wrong

**Real Economy Focus**:
- De-emphasize crypto (most moves are technical/idiosyncratic)
- Focus on what market moves tell us about broader economy
- Better aligns with prediction markets
- Richer, more actionable narratives

**Historical Context in Final Phase**:
- Prevents contradicting past analyses
- Enables learning from experience
- Allows referencing similar situations
- Builds institutional memory

---

## Implementation Status

### ✅ Phase 1: Foundation (COMPLETE)
- [x] Project directory structure
- [x] Python package configuration (pyproject.toml)
- [x] Configuration system (config.yaml, .env)
- [x] LangChain/LangGraph integration (replaced custom LLM client)
- [x] Base classes:
  - [x] DataCollector (collectors/base.py)
  - [x] Pydantic models (storage/models.py)
- [x] Entry point (main.py)
- [x] Orchestrator skeleton (orchestrator/orchestrator.py)
- [x] Documentation (README.md, DESIGN.md)
- [x] Dependencies installed and verified

### ✅ Data Collectors (COMPLETE - All Tests Passing)
- [x] **Price collector** (collectors/price.py)
  - [x] yfinance integration for stocks, indices, sectors, commodities, VIX
  - [x] Returns calculation and volume ratio analysis
  - [x] In-memory caching (5-minute TTL)
  - [x] 14 tests passing
- [x] **News collector** (collectors/news.py)
  - [x] RSS feed parser (Reuters, Yahoo, CNBC)
  - [x] NewsAPI integration (optional, with key)
  - [x] Keyword filtering and deduplication
  - [x] In-memory caching (1-hour TTL)
  - [x] 15 tests passing (1 skipped without NewsAPI key)
- [x] **Prediction markets collector** (collectors/prediction.py)
  - [x] Manifold Markets integration (binary markets)
  - [x] Polymarket integration (via Gamma API)
  - [x] Keyword filtering and sorting by volume
  - [x] In-memory caching (1-hour TTL)
  - [x] 17 tests passing

### ✅ Data Processor (COMPLETE)
- [x] **Statistical analysis** (analysis/processor.py)
  - [x] Significant move detection (>3% threshold)
  - [x] Volume spike analysis (>1.5x average)
  - [x] Market snapshot generation
  - [x] Sector performance calculations
  - [x] Market breadth metrics
  - [x] 18 tests passing

### ✅ Test Coverage
- **69 tests passing** across all modules
- All core data collection and processing functionality verified

### ✅ Phase 2: Iterative Agent (COMPLETE)
- [x] **LangGraph state machine** (agent/graph.py)
  - [x] 4-phase workflow: Observation → Hypothesis → Investigation → Synthesis
  - [x] Async node execution with proper state management
  - [x] LLM integration for each phase
  - [x] Structured JSON outputs with parsing
  - [x] **Tool calling in investigation phase** - LLM requests and executes tools
  - [x] Enhanced logging showing all hypotheses and tool executions
- [x] **Agent controller** (agent/controller.py)
  - [x] Orchestrates full workflow
  - [x] Initializes all collectors and tools
  - [x] Creates LLM instance (OpenAI/Anthropic support)
  - [x] Converts state to DailyNarrative output
- [x] **Agent state** (agent/state.py)
  - [x] TypedDict for LangGraph workflow
  - [x] CandidateHypothesis and InvestigationResult types
  - [x] Tracks all 4 phases with intermediate outputs
- [x] **Agent tools** (agent/tools.py)
  - [x] Phase 1 tools: get_market_overview, get_sector_returns, get_top_movers, get_news_headlines
  - [x] Phase 3 tools: get_stock_details, search_news, get_prediction_markets, get_correlated_moves
  - [x] Tool dependency injection via initialize_tools()
  - [x] Full integration with collectors
  - [x] Used by LLM during investigation phase
- [x] **Narrative generation** (integrated in synthesis_node)
  - [x] LLM creates primary narrative, supporting points, unexplained moves
  - [x] Forward-looking insights generated
  - [x] Confidence scoring based on investigation results
- [x] **Orchestrator integration** (orchestrator/orchestrator.py)
  - [x] Uses AgentController for daily narrative generation
  - [x] Entry point for production usage
- [x] **4 agent tests passing**
  - [x] State creation and initialization
  - [x] Controller initialization
  - [x] Full workflow execution (end-to-end)

### ✅ Phase 3: Output & Storage (COMPLETE)
- [x] **Output formatting** (output/formatter.py)
  - [x] Markdown formatter with market data tables (indices, sectors, top movers, breadth, volatility)
  - [x] JSON output with structured DailyNarrative
  - [x] Agent logs capture and export
  - [x] Market snapshot JSON export
  - [x] Handles both MarketSnapshot objects and dicts
- [x] **Storage layer** (storage/database.py)
  - [x] SQLite database with async support (aiosqlite)
  - [x] Three tables: market_snapshots, news_headlines, daily_narratives
  - [x] Upsert functionality for all tables
  - [x] Retrieval methods for historical narratives
  - [x] Handles both Pydantic models and dicts
- [x] **Production testing**
  - [x] End-to-end test with real market data
  - [x] All output files generated successfully
  - [x] Database persistence verified
  - [x] Market data table displays correctly in markdown
  - [x] No redundant tool calls
  - [x] Prediction markets used in investigation
- [x] **Bug fixes**
  - [x] Fixed market data storage using state["additional_data"]
  - [x] Updated RSS feeds (removed broken Reuters/Yahoo, added FT/Bloomberg/WSJ)
  - [x] Enhanced investigation prompt to prevent redundant API calls
  - [x] Improved prediction market prompting with specific examples

### 📋 Phase 4: Optimization & Production Deployment (Planned)
- [ ] Historical context integration (compare with past narratives)
- [ ] Scheduling system (run daily at 9:45 AM ET)
- [ ] Email/Slack distribution
- [ ] Performance optimization (reduce API calls, cache management)
- [ ] Monitoring and alerting
- [ ] Cost tracking and optimization
- [ ] Backtesting narrative accuracy
- [ ] Multi-narrative styles (brief, detailed, technical)

---

## Key Technical Decisions Made

### Python Version Compatibility
- **Decision**: Support Python 3.9+ (originally specified 3.11+)
- **Reason**: User's environment uses Python 3.9.6
- **Impact**: Updated all type hints from `X | None` to `Optional[X]` for compatibility
- **Files Updated**: config.py, collectors/base.py, llm/base.py, storage/models.py, orchestrator/orchestrator.py

### Build System
- **Decision**: Use hatchling as build backend
- **Configuration**: Added `[tool.hatch.build.targets.wheel]` with `packages = ["src"]`
- **Reason**: Modern, standard-compliant build system

### Agent Framework: LangChain/LangGraph
- **Decision**: Use LangChain/LangGraph instead of custom LLM client
- **Reason**:
  - Perfect fit for multi-phase agentic workflows
  - Built-in tool calling, state management, and conditional edges
  - Saves time not reinventing agent orchestration
  - LangGraph designed specifically for this use case
- **Impact**:
  - Removed custom `src/llm/` module
  - Added langchain, langchain-openai, langchain-anthropic, langgraph dependencies
  - Will use LangGraph state machines for 4-phase workflow
- **When**: Phase 1 complete, Phase 2 agent implementation uses LangGraph

### Prediction Markets: Manifold + Polymarket
- **Decision**: Use Manifold Markets and Polymarket (removed Metaculus)
- **Reason**:
  - Metaculus API changed, requires individual question fetches for predictions
  - Manifold Markets has clean API, good for binary markets
  - Polymarket Gamma API provides open markets with volume data
- **Implementation**:
  - Manifold: Uses `/markets` endpoint with `sort=last-bet-time`
  - Polymarket: Uses `/markets` endpoint with `closed=false` filter
  - Both return binary Yes/No markets with probabilities

### Agent Implementation: 4-Phase LangGraph Workflow
- **Decision**: Implement full 4-phase workflow with LangGraph state machine
- **Architecture**:
  - **observe_node**: Calls tools (market overview, top movers, news), LLM analyzes and summarizes
  - **hypothesize_node**: LLM generates 3-5 candidate hypotheses with JSON output
  - **investigate_node**: LLM analyzes hypotheses with evidence (simplified for now)
  - **synthesize_node**: LLM creates final narrative with JSON output
- **Technical Details**:
  - AgentState TypedDict tracks all phase data through workflow
  - Async node execution with proper await handling
  - Tool dependency injection via initialize_tools()
  - LLM passed to nodes via wrapper functions
  - JSON parsing with markdown code block removal
- **Node Communication**:
  - Linear workflow: observe → hypothesize → investigate → synthesize → END
  - Each node returns updated AgentState dict
  - State persists across all phases
- **Tools Implemented**:
  - Phase 1: get_market_overview, get_sector_returns, get_top_movers, get_news_headlines
  - Phase 3: get_stock_details, search_news, get_prediction_markets, get_correlated_moves

### DateTime Handling in News Collector
- **Issue**: Mixed timezone-aware and timezone-naive datetimes from different sources
- **Fix**: Normalize all datetimes to UTC naive before sorting
- **Implementation**: Convert timezone-aware to UTC and strip timezone, keep naive as-is
- **Impact**: Prevents "can't compare offset-naive and offset-aware datetimes" error

### Market Data Storage in Agent State
- **Issue**: Market data was being stored as `state["market_data_dict"]` which isn't a field in AgentState TypedDict
- **Fix**: Store in `state["additional_data"]["market_data_dict"]` using the flexible additional_data dict
- **Reason**: AgentState has `additional_data: Dict[str, Any]` specifically for tool outputs that don't fit predefined fields
- **Impact**: Market data now properly persists through workflow and can be retrieved by orchestrator for formatting
- **Files Updated**: agent/graph.py (observe_node, investigate_node), orchestrator/orchestrator.py

### Output Formatter Dual-Mode Support
- **Decision**: Support both MarketSnapshot Pydantic objects and raw dicts in formatter
- **Reason**: Agent stores market data as dict, but database may return MarketSnapshot objects
- **Implementation**:
  - Helper function `get_field()` normalizes access (dict.get() vs object.attribute)
  - Mover iteration handles both dict and object representations
  - JSON serialization uses `json.dumps()` for dicts, `model_dump_json()` for Pydantic models
- **Files Updated**: output/formatter.py (_format_market_table, save_narrative)

### RSS Feed Sources Update
- **Issue**: Reuters and Yahoo RSS feeds broken/not parsing correctly
- **Fix**: Removed broken feeds, added reliable alternatives
- **New Sources**:
  - CNBC (3 feeds): Top News, Business, Markets
  - Financial Times: Home feed
  - Bloomberg: Markets feed
  - NewsAPI: Keyword search (requires API key)
- **Impact**: Now successfully collecting from 6 sources with ~60-100 articles per run
- **File Updated**: collectors/news.py (DEFAULT_RSS_FEEDS)

### Investigation Phase Optimization
- **Issue**: Agent redundantly calling get_market_overview and get_sector_returns during investigation
- **Fix**: Enhanced investigation prompt with Phase 1 data summary
- **Implementation**:
  - Include major indices, top movers, sectors, breadth, volatility in prompt
  - Explicit instruction: "DO NOT re-call get_market_overview or get_sector_returns"
  - Tool recommendations guide LLM to use appropriate Phase 3 tools
- **Impact**: Reduced unnecessary API calls, faster execution, lower costs
- **File Updated**: agent/graph.py (investigate_node)

### Prediction Markets Enhanced Prompting
- **Issue**: Agent wasn't using prediction markets tool despite availability
- **Fix**: Added specific examples and guidance in investigation prompt
- **Examples Added**:
  - "If NVDA beat expectations, search 'NVIDIA earnings' or 'NVDA stock price'"
  - "If Fed policy mentioned, search 'Fed rate' or 'interest rate'"
  - "Look for same-day probability changes that corroborate hypothesis"
- **Impact**: Prediction markets now consistently used to validate hypotheses
- **File Updated**: agent/graph.py (investigate_node)

### Code Style
- **Black**: Line length 100, target Python 3.9
- **Ruff**: Line length 100, target Python 3.9
- **Linting**: E, F, I, N, W rules enabled (except E501)

### Dependency Version Constraints
- **ipython**: Limited to `>=8.12.0,<8.19.0` for Python 3.9 compatibility
- **pytest**: Downgraded to `>=7.4.0` from `>=8.3.0`
- **black**: Downgraded to `>=24.0.0` from `>=24.8.0`

---

## Common Commands

### Run the application
```bash
python3 -m src.main
```

### Run tests
```bash
pytest
```

### Format code
```bash
black src/ tests/
```

### Lint code
```bash
ruff check src/ tests/
```

### Install in editable mode
```bash
pip install -e ".[dev]"
```

---

## Data Models Reference

### Core Models (storage/models.py)

**AssetMove**: Single asset's price movement
- symbol, name, price, change_percent, change_absolute
- volume, volume_ratio

**MarketSnapshot**: Broad market state
- date, major_indices, biggest_gainers, biggest_losers
- sector_performance, market_breadth, volatility

**NewsArticle**: News item
- title, url, source, published_at
- summary, keywords

**Prediction**: Prediction market data
- question, probability, platform, url
- last_updated, volume

**CandidateNarrative**: Hypothesis during investigation
- hypothesis, supporting_evidence, contradicting_evidence
- confidence, questions_to_investigate

**DailyNarrative**: Final output
- date, headline, primary_narrative
- supporting_narratives, key_moves_explained
- prediction_market_insights, unexplained_moves
- looking_ahead, confidence_score, data_sources, metadata

---

## Next Steps (Priority Order)

### ✅ Phase 1 Complete
All data collectors implemented and tested:
- ✅ Price collector with yfinance (14 tests)
- ✅ News collector with RSS + NewsAPI (16 tests)
- ✅ Prediction markets collector - Manifold + Polymarket (17 tests)
- ✅ Data processor for market snapshots (18 tests)

### ✅ Phase 2 Complete
Agent implementation with LangGraph:
- ✅ Agent state schema (AgentState TypedDict)
- ✅ 8 tools for Phase 1 and Phase 3
- ✅ LangGraph state machine with 4 phases
- ✅ Agent controller with LLM integration
- ✅ Full workflow testing (4 tests)
- ✅ **69 tests passing total**

### ✅ Phase 3: Output & Storage (COMPLETE)

1. **Output Formatting** ✅
   - [x] Created markdown formatter (research note style) - `src/output/formatter.py`
   - [x] Markdown includes: Executive Summary, Detailed Analysis, Supporting Evidence, Unexplained Movements, Looking Ahead
   - [x] JSON output with full DailyNarrative structure
   - [x] Full agent logs captured for evaluation (21+ KB per run)
   - [x] Files saved to `./outputs/YYYY-MM-DD/` directory structure

2. **Storage Layer** ✅
   - [x] SQLite database implementation - `src/storage/database.py`
   - [x] Three tables: `market_snapshots`, `news_headlines`, `daily_narratives`
   - [x] Async operations with SQLAlchemy + aiosqlite
   - [x] Upsert functionality (update if exists, insert if new)
   - [x] Historical narrative retrieval methods ready for future use
   - [x] Database location: `./data/narratives.db`

3. **Orchestrator Integration** ✅
   - [x] Updated orchestrator to save all outputs
   - [x] Log capture during execution
   - [x] File writing (markdown, JSON, logs)
   - [x] Database persistence (narratives, snapshots, headlines)
   - [x] Proper error handling with try-finally

4. **Bug Fixes** ✅
   - [x] Fixed headline truncation bug (was splitting "U.S." incorrectly)
   - [x] LLM now generates headlines directly in synthesis phase
   - [x] Added headline field to AgentState
   - [x] Fixed SQLAlchemy raw SQL queries to use select() and text()
   - [x] Installed greenlet dependency for async SQLAlchemy

5. **End-to-End Testing** ✅
   - [x] Successfully generated narrative for 2026-02-06
   - [x] Headline: "Tech-led rally slashes VIX; gold jumps"
   - [x] Confidence score: 75%
   - [x] All output files created successfully (markdown, JSON, market snapshot, logs)
   - [x] Market data tables displaying correctly in markdown
   - [x] Database populated with narratives and snapshots
   - [x] No redundant tool calls
   - [x] Prediction markets successfully used in investigation
   - [x] RSS feeds working from 6 reliable sources

### 📋 Phase 4: Optimization & Production (NEXT)

**All Known Issues Resolved** ✅:

1. ~~**Redundant Tool Calls in Investigation**~~ ✅ **FIXED**
   - Added Phase 1 data summary to investigation prompt
   - Explicit instruction not to re-call get_market_overview/get_sector_returns
   - Reduced from ~11 tools to ~6 tools per investigation
   - Saves ~6-10 seconds per run

2. ~~**RSS Feed Failures**~~ ✅ **FIXED**
   - Removed broken Reuters and Yahoo feeds
   - Added reliable sources: Financial Times, Bloomberg, WSJ
   - Now collecting from 6 sources: CNBC (3), FT, Bloomberg, NewsAPI
   - Typically 60-100 articles per run

3. ~~**Market Data Table Missing from Markdown**~~ ✅ **FIXED**
   - Fixed market data storage in state["additional_data"]["market_data_dict"]
   - Updated formatter to handle both MarketSnapshot objects and dicts
   - Tables now display: Major Indices, Sector Performance, Top Movers, Market Breadth, Volatility

4. ~~**Prediction Markets Not Used**~~ ✅ **IMPROVED**
   - Enhanced investigation prompt with specific examples of when to use prediction markets
   - Added guidance: "Market participants vote with money, so probability changes provide evidence"
   - Now consistently called during investigation (10+ markets per hypothesis)

**Current Performance** (2026-02-06 test):
- **Execution Time**: ~90 seconds end-to-end
- **Confidence Score**: 75%
- **Tools Used**: 11 total (reduced from 16+ with redundant calls)
- **News Articles**: 20 unique articles from 6 sources
- **Prediction Markets**: 10+ markets queried per hypothesis
- **Output Files**: 4 files (narrative.md, narrative.json, market_snapshot.json, agent_logs.txt)
- **Database**: Successfully persisted narratives, snapshots, and headlines

**Planned Enhancements**:

1. **Optimize Investigation Phase**
   - Include Phase 1 data in investigation context to reduce redundant calls
   - Add data source citations to narrative (which specific articles, predictions used)
   - Implement caching for repeated tool calls within same run

2. **Improve News Collection**
   - Remove/fix broken RSS feeds (Reuters, Yahoo)
   - Add alternative sources: Financial Times, Wall Street Journal, Bloomberg
   - Implement RSS feed health checks
   - Add source diversity metrics

3. **Historical Context Integration**
   - Retrieve past narratives from database
   - Compare current market conditions to historical patterns
   - Reference similar past situations in narrative
   - Track narrative accuracy over time

4. **Production Readiness**
   - Implement scheduling (9:45 AM ET daily run)
   - Add error handling and retry logic
   - Email/Slack notifications for daily reports
   - Monitoring and alerting for failures
   - Cost tracking and optimization

---

## Important Notes

### Real Economy Focus
- De-emphasize crypto - most moves are technical/idiosyncratic
- Focus on stocks, sectors, rates, commodities as economic signals
- Look for connections between asset classes

### Token Efficiency Considerations
- Pre-process data before sending to LLM
- Use structured outputs (Pydantic models)
- Cache LLM responses for identical prompts
- Use smaller models for routine tasks
- Estimated cost: ~$0.10-0.50 per day

### Free Data Source Strategy
- **yfinance**: Primary for price data (no key needed, unlimited)
- **RSS feeds**: Primary for news (no key needed, unlimited)
- **NewsAPI**: Secondary for news (100 calls/day free, key required)
- **Manifold Markets**: Prediction markets (no key needed, unlimited)
- **Polymarket**: Prediction markets via Gamma API (no key needed, free tier)
- **FRED**: Economic data (free with API key, not yet implemented)

### Future Extensions
- Multi-agent system with specialists
- Memory/RAG for past narratives
- Backtesting narrative accuracy
- Interactive chat mode
- Web dashboard
- Real-time alerts
- Multiple narrative styles

---

## Debugging Tips

### Import Issues
- Ensure you're in the project root directory
- Use `python3 -m src.main` not `python src/main.py`
- Check PYTHONPATH includes project root

### API Issues
- Verify .env file has correct keys
- Check API rate limits (especially NewsAPI)
- yfinance can be flaky - implement retries with tenacity

### Type Checking
- Remember: Python 3.9 requires `Optional[X]` not `X | None`
- Use `from typing import Optional, Union, Dict, List`
- Lowercase `dict`, `list` work in type hints for 3.9+

---

## Contact & Resources

**Developer**: Mike Zhu (mike.zhu888@gmail.com)
**Repository**: [To be added]
**Documentation**: See DESIGN.md for detailed architecture
**License**: MIT

---

*This document should be updated as the project evolves. Always check git history for latest changes.*
