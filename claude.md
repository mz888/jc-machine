# Claude Context Document - Market Narrative Agent

**Last Updated**: 2026-02-06
**Project Status**: Phase 2 Complete - Agent fully implemented with LangGraph. Ready for Phase 3 (Production Testing & Output)

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
│   │   └── orchestrator.py     # ✅ Orchestrates daily runs
│   │
│   ├── agent/             # ✅ COMPLETE - Multi-phase agentic workflow
│   │   ├── __init__.py
│   │   ├── controller.py       # ✅ Agent controller
│   │   ├── graph.py            # ✅ LangGraph 4-phase workflow
│   │   ├── state.py            # ✅ State management
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
│   ├── storage/           # ✅ Data models (database layer TODO)
│   │   ├── __init__.py
│   │   └── models.py           # ✅ Pydantic models
│   │
│   └── utils/             # Utilities (if needed)
│
├── tests/                 # ✅ 69 tests passing
├── outputs/               # Generated narratives (to be created)
├── logs/                  # Application logs
└── cache/                 # Data cache (in-memory for now)
```

**Note**: Removed `src/llm/` (using LangChain), `src/tools/` (consolidated into agent/tools.py), and `src/narrative/` (integrated into synthesis_node in agent/graph.py)

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

### 📋 Phase 3: Production Readiness (Planned)
- [ ] Output formatting (markdown + JSON files)
- [ ] Storage layer for narratives (SQLite database)
- [ ] Historical context integration
- [ ] Quality improvements and testing

### 📋 Phase 4: Production Readiness (Planned)
- [ ] Orchestration and scheduling
- [ ] Error handling and monitoring
- [ ] Comprehensive tests
- [ ] Production documentation

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

### 🚧 Phase 3: Production Readiness (CURRENT)

1. **Test End-to-End Narrative Generation**
   - Run agent on real market data
   - Verify narrative quality and coherence
   - Test with different market conditions (up/down/mixed days)
   - Validate hypothesis generation and investigation

2. **Enhance Investigation Phase**
   - Implement actual tool calling in investigate_node (currently simplified)
   - Parse LLM tool call requests
   - Execute tools based on hypotheses
   - Aggregate investigation results

3. **Add Storage Layer**
   - Create SQLite database schema for narratives
   - Implement `src/storage/database.py`
   - Store DailyNarrative objects
   - Add historical narrative retrieval for context

4. **Output Formatting**
   - Create markdown formatter (human-readable narrative)
   - Create JSON formatter (structured output)
   - Add visualization of key moves and sectors
   - Generate daily report files in `./outputs/YYYY-MM-DD/`

5. **Production Integration**
   - Update orchestrator.py to use agent controller
   - Add error handling and retry logic
   - Implement scheduling (9:45 AM ET daily run)
   - Add monitoring and alerting

6. **Documentation and Polish**
   - Update README with usage examples
   - Add example narratives to documentation
   - Create user guide for customization
   - Document API cost estimates

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
