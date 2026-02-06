# Market Narrative Agent

An intelligent agent system that analyzes market movements and generates daily narratives attempting to explain what it observes. The system uses an iterative, hypothesis-driven approach to understand what market moves reveal about the real economy.

## Overview

The Market Narrative Agent follows a multi-phase approach to generate narratives:

1. **Initial Observation** - Gathers broad market data (indices, sectors, key stocks, news)
2. **Hypothesis Formation** - Generates candidate narratives that could explain observations
3. **Targeted Investigation** - Deep dives into specific data to validate/refine hypotheses
4. **Narrative Synthesis** - Incorporates historical context and generates final narratives

## Features

- **Iterative Analysis** - Agent explores data, forms hypotheses, investigates, and refines understanding
- **Real Economy Focus** - Prioritizes understanding broader economic signals
- **Multi-Source Data** - Integrates price data, news, prediction markets, and economic indicators
- **Observable Reasoning** - Clear visibility into hypothesis formation and refinement
- **Extensible Architecture** - Easy to add new data sources and analytical approaches

## Asset Coverage

- **Indices**: S&P 500, NASDAQ
- **Individual Stocks**: MAG7 (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA)
- **Sector ETFs**: 11 sector ETFs covering the full market
- **Commodities**: Oil, Gold
- **Volatility**: VIX
- **Treasury Rates**: 2Y, 5Y, 10Y, 30Y

## Installation

### Prerequisites

- Python 3.09 or higher
- API keys for LLM providers (Anthropic or OpenAI)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd market-narrative-agent
```

2. Install dependencies:
```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

4. (Optional) Customize configuration:
```bash
# Edit config.yaml to adjust asset universe, LLM settings, etc.
```

## Usage

### Run Daily Narrative Generation

```bash
python -m src.main
```

This will:
1. Collect market data for the day
2. Run the multi-phase agent workflow
3. Generate narratives explaining market moves
4. Save outputs to `outputs/YYYY-MM-DD/`

### Configuration

Edit `config.yaml` to customize:
- Asset universe (stocks, sectors, commodities)
- LLM provider and models
- Processing thresholds (what counts as "significant")
- Output formats and locations
- Cache settings

### Outputs

Generated narratives are saved in two formats:

**Markdown** (`outputs/YYYY-MM-DD/narrative.md`):
- Human-readable narrative document
- Includes headline, primary narrative, supporting themes
- Key moves explained, prediction market insights
- Forward-looking implications

**JSON** (`outputs/YYYY-MM-DD/narrative.json`):
- Structured data format
- Includes all narrative components plus metadata
- Confidence scores, data sources, timestamps

## Project Structure

```
market-narrative-agent/
├── src/
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration management
│   ├── orchestrator/        # Daily run orchestration
│   ├── agent/               # Multi-phase agent controller
│   ├── collectors/          # Data collection (prices, news, predictions)
│   ├── llm/                 # LLM abstraction layer
│   ├── tools/               # Agent tools
│   ├── narrative/           # Narrative generation
│   ├── storage/             # Data models and persistence
│   ├── analysis/            # Statistical analysis
│   └── utils/               # Utilities
├── tests/                   # Tests
├── outputs/                 # Generated narratives
├── logs/                    # Application logs
├── cache/                   # Data cache
├── config.yaml              # Configuration file
├── .env                     # Environment variables (API keys)
└── DESIGN.md               # Detailed design document

```

## Architecture

See [DESIGN.md](DESIGN.md) for comprehensive architecture documentation including:
- Iterative narrative generation workflow
- Data sources and collection strategy
- Agent design patterns
- Component specifications
- Implementation roadmap

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src/ tests/
ruff check src/ tests/
```

### Adding a New Data Collector

1. Create a new file in `src/collectors/`
2. Inherit from `DataCollector` base class
3. Implement `collect()` method and properties
4. Register in orchestrator or agent tools

Example:
```python
from src.collectors.base import DataCollector, CollectionResult

class MyCollector(DataCollector):
    @property
    def source_name(self) -> str:
        return "my_source"

    @property
    def cache_ttl(self) -> int:
        return 3600  # 1 hour

    async def collect(self, params) -> CollectionResult:
        # Fetch data
        data = await fetch_from_api()
        return CollectionResult(
            data=data,
            timestamp=datetime.now(),
            source=self.source_name
        )
```

## Roadmap

### Phase 1: Foundation (Current)
- [x] Project structure and configuration
- [x] Base classes and models
- [ ] Basic data collectors (prices, news)
- [ ] Simple storage layer
- [ ] Single-phase agent

### Phase 2: Iterative Agent
- [ ] Multi-phase agent controller
- [ ] Tool-calling system
- [ ] Hypothesis formation
- [ ] Targeted investigation

### Phase 3: Narrative Generation
- [ ] Historical context integration
- [ ] Narrative synthesis
- [ ] Output formatting
- [ ] Quality improvements

### Phase 4: Production Readiness
- [ ] Orchestration and scheduling
- [ ] Error handling and monitoring
- [ ] Documentation
- [ ] Tests

## Future Extensions

- Multi-agent system with specialist agents
- Memory system for semantic search over past narratives
- Backtesting narrative accuracy
- Interactive mode (chat interface)
- Web dashboard with visualizations
- Real-time alerts for significant moves
- Multiple narrative styles (technical, casual, academic)
- Multi-language support

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Contact

For questions or feedback, please open an issue on GitHub.

## Acknowledgments

- Built with Claude Code
- Uses data from yfinance, NewsAPI, Manifold Markets, Polymarket
- LLM providers: Anthropic (Claude), OpenAI (GPT)
