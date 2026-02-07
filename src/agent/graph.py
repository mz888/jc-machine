"""LangGraph state machine for market narrative agent.

Defines the 4-phase workflow:
1. Observation: Collect initial market data
2. Hypothesis: Generate candidate explanations
3. Investigation: Test hypotheses with targeted queries
4. Synthesis: Create final narrative
"""

import json
from datetime import datetime
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from loguru import logger

from src.agent.state import AgentState
from src.agent.tools import (
    get_all_tools,
    get_correlated_moves,
    get_market_overview,
    get_news_headlines,
    get_prediction_markets,
    get_sector_returns,
    get_stock_details,
    get_top_movers,
    search_news,
)


def create_agent_graph(llm):
    """Create the LangGraph state machine for the agent.

    Args:
        llm: LangChain LLM instance (e.g., ChatOpenAI or ChatAnthropic)

    Returns:
        Compiled LangGraph workflow
    """
    # Bind tools to the LLM
    tools = get_all_tools()
    llm_with_tools = llm.bind_tools(tools)

    # Create state graph with LLM attached to config
    workflow = StateGraph(AgentState)

    # Store LLM in a way nodes can access it
    # We'll pass it through the config
    workflow.llm = llm
    workflow.llm_with_tools = llm_with_tools

    # Add nodes for each phase
    # Note: LangGraph handles async functions automatically, no need for lambda wrappers
    async def observe_wrapper(state, config):
        return await observe_node(state, config, workflow.llm)

    async def hypothesize_wrapper(state, config):
        return await hypothesize_node(state, config, workflow.llm)

    async def investigate_wrapper(state, config):
        return await investigate_node(state, config, workflow.llm_with_tools)

    async def synthesize_wrapper(state, config):
        return await synthesize_node(state, config, workflow.llm)

    workflow.add_node("observe", observe_wrapper)
    workflow.add_node("hypothesize", hypothesize_wrapper)
    workflow.add_node("investigate", investigate_wrapper)
    workflow.add_node("synthesize", synthesize_wrapper)

    # Add edges
    workflow.set_entry_point("observe")
    workflow.add_edge("observe", "hypothesize")
    workflow.add_edge("hypothesize", "investigate")
    workflow.add_edge("investigate", "synthesize")
    workflow.add_edge("synthesize", END)

    # Compile the graph
    return workflow.compile()


# =============================================================================
# Node Implementations
# =============================================================================


async def observe_node(state: AgentState, config: RunnableConfig, llm) -> AgentState:
    """Phase 1: Observation - Collect and analyze initial market data.

    This node:
    1. Calls tools to get market overview, top movers, news
    2. Uses LLM to summarize the initial market state
    3. Identifies significant moves and patterns
    """
    logger.info("=== PHASE 1: OBSERVATION ===")

    state["current_phase"] = "observation"

    try:
        # 1. Get market overview
        logger.info("Calling get_market_overview...")
        market_data = await get_market_overview.ainvoke({})
        state["tools_used"].append("get_market_overview")

        # Store market data in additional_data (flexible storage for tool outputs)
        # The dict structure works fine for investigation prompts and can be converted
        # to MarketSnapshot when saving to database
        state["additional_data"]["market_data_dict"] = market_data

        logger.info(f"  → Collected data on {len(market_data.get('major_indices', []))} indices, "
                   f"{len(market_data.get('biggest_gainers', []))} gainers, "
                   f"{len(market_data.get('biggest_losers', []))} losers")

        # 2. Get top movers
        logger.info("Calling get_top_movers...")
        movers_data = await get_top_movers.ainvoke({"n": 10})
        state["tools_used"].append("get_top_movers")
        logger.info(f"  → Top gainer: {movers_data['gainers'][0]['symbol']} "
                   f"({movers_data['gainers'][0]['change_percent']:+.2f}%)")
        logger.info(f"  → Top loser: {movers_data['losers'][0]['symbol']} "
                   f"({movers_data['losers'][0]['change_percent']:+.2f}%)")

        # 3. Get news headlines
        logger.info("Calling get_news_headlines...")
        news_data = await get_news_headlines.ainvoke({"limit": 20})
        state["tools_used"].append("get_news_headlines")
        logger.info(f"  → Collected {len(news_data)} news articles")
        if news_data:
            logger.info(f"  → Latest: \"{news_data[0]['title'][:60]}...\"")
        logger.info("")

        # 4. Use LLM to analyze and summarize
        logger.info("Analyzing observation data with LLM...")

        observation_prompt = f"""You are a financial market analyst. Analyze the following market data and provide a concise summary of the key observations.

MARKET DATA:
{json.dumps(market_data, indent=2, default=str)}

TOP MOVERS:
{json.dumps(movers_data, indent=2, default=str)}

NEWS HEADLINES (sample):
{json.dumps(news_data[:5], indent=2, default=str)}

Please provide:
1. A brief summary of the overall market direction
2. The most significant market moves (2-3 items)
3. Any notable patterns or anomalies
4. Key themes from the news

Keep your response concise (3-4 paragraphs max)."""

        response = await llm.ainvoke([HumanMessage(content=observation_prompt)])
        summary = response.content

        state["initial_summary"] = summary
        state["intermediate_outputs"].append(
            {"phase": "observation", "market_data": market_data, "news_count": len(news_data)}
        )

        logger.info("Observation complete")
        logger.info(f"Summary: {summary[:200]}...")

    except Exception as e:
        logger.error(f"Error in observation phase: {e}")
        state["errors"].append(f"Observation phase error: {str(e)}")
        state["initial_summary"] = "Error collecting market data. Proceeding with limited information."

    return state


async def hypothesize_node(state: AgentState, config: RunnableConfig, llm) -> AgentState:
    """Phase 2: Hypothesis - Generate candidate explanations.

    This node:
    1. Analyzes patterns from observation phase
    2. Uses LLM to generate multiple candidate narratives
    3. Ranks hypotheses by plausibility
    4. Selects top hypotheses for investigation
    """
    logger.info("=== PHASE 2: HYPOTHESIS GENERATION ===")

    state["current_phase"] = "hypothesis"

    try:
        hypothesis_prompt = f"""Based on the market observations below, generate 3-5 candidate hypotheses that could explain the market movements.

MARKET SUMMARY:
{state['initial_summary']}

For each hypothesis, provide:
1. A clear, specific explanation of what's driving the market
2. An initial confidence level (0.0 to 1.0)
3. Key supporting factors you've observed
4. Specific questions to investigate to validate this hypothesis
5. A priority ranking (1=highest priority)

Format your response as a JSON array of objects with these fields:
- hypothesis: string (the explanation)
- confidence: float (0.0 to 1.0)
- supporting_factors: array of strings
- questions_to_investigate: array of strings
- priority: integer (1-5)

Respond with ONLY the JSON array, no other text."""

        response = await llm.ainvoke([HumanMessage(content=hypothesis_prompt)])
        content = response.content.strip()

        # Parse JSON response
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        hypotheses = json.loads(content)

        state["hypotheses"] = hypotheses

        # Log all generated hypotheses
        logger.info(f"Generated {len(hypotheses)} hypotheses:")
        for i, h in enumerate(hypotheses, 1):
            logger.info(f"  Hypothesis {i} (priority={h.get('priority', '?')}, confidence={h.get('confidence', 0):.2f}):")
            logger.info(f"    → {h.get('hypothesis', 'N/A')}")
            logger.info(f"    Supporting: {', '.join(h.get('supporting_factors', [])[:2])}...")
            logger.info(f"    Questions: {', '.join(h.get('questions_to_investigate', [])[:2])}...")

        # Select top 3 hypotheses for investigation
        sorted_hypotheses = sorted(
            hypotheses, key=lambda x: (x.get("priority", 99), -x.get("confidence", 0))
        )
        state["selected_hypotheses"] = [h["hypothesis"] for h in sorted_hypotheses[:3]]

        logger.info(f"\nSelected {len(state['selected_hypotheses'])} hypotheses for investigation:")
        for i, h_text in enumerate(state["selected_hypotheses"], 1):
            logger.info(f"  {i}. {h_text[:100]}...")

        state["intermediate_outputs"].append(
            {"phase": "hypothesis", "num_generated": len(hypotheses), "selected": len(state["selected_hypotheses"])}
        )

    except Exception as e:
        logger.error(f"Error in hypothesis phase: {e}")
        state["errors"].append(f"Hypothesis phase error: {str(e)}")

        # Fallback: create a generic hypothesis
        state["hypotheses"] = [
            {
                "hypothesis": "Market movements driven by general economic factors",
                "confidence": 0.5,
                "supporting_factors": ["Mixed sector performance"],
                "questions_to_investigate": ["What are the key economic indicators?"],
                "priority": 1,
            }
        ]
        state["selected_hypotheses"] = [state["hypotheses"][0]["hypothesis"]]

    return state


async def investigate_node(state: AgentState, config: RunnableConfig, llm_with_tools) -> AgentState:
    """Phase 3: Investigation - Test hypotheses with targeted queries.

    This node:
    1. For each selected hypothesis, determines what to investigate
    2. Calls appropriate tools (stock details, news search, predictions, etc.)
    3. Uses LLM to analyze evidence for/against each hypothesis
    4. Updates confidence scores
    """
    logger.info("=== PHASE 3: INVESTIGATION ===")

    state["current_phase"] = "investigation"

    investigation_results = []

    try:
        # Investigate each selected hypothesis
        for i, hypothesis_text in enumerate(state["selected_hypotheses"][:2]):  # Limit to 2 for cost
            logger.info(f"\n{'='*60}")
            logger.info(f"INVESTIGATING HYPOTHESIS {i+1}")
            logger.info(f"{'='*60}")
            logger.info(f"Hypothesis: {hypothesis_text}")

            # Find the full hypothesis object
            hypothesis = next(
                (h for h in state["hypotheses"] if h["hypothesis"] == hypothesis_text), None
            )

            if not hypothesis:
                logger.warning(f"Could not find full hypothesis object for: {hypothesis_text[:50]}...")
                continue

            logger.info(f"Initial confidence: {hypothesis.get('confidence', 0):.2f}")
            logger.info(f"Questions to investigate:")
            for q in hypothesis.get('questions_to_investigate', []):
                logger.info(f"  • {q}")

            # Prepare summary of already-collected data
            market_data = state["additional_data"].get("market_data_dict", {})
            available_data_summary = f"""
ALREADY AVAILABLE FROM PHASE 1 OBSERVATION:
- Major Indices: {', '.join(f'{k}: {v:+.2f}%' for k, v in market_data.get('major_indices', {}).items())}
- Top Gainers: {', '.join(f"{m['symbol']} ({m['change_percent']:+.2f}%)" for m in market_data.get('biggest_gainers', [])[:5])}
- Top Losers: {', '.join(f"{m['symbol']} ({m['change_percent']:+.2f}%)" for m in market_data.get('biggest_losers', [])[:5])}
- Sector Performance: {', '.join(f'{k}: {v:+.2f}%' for k, v in list(market_data.get('sector_performance', {}).items())[:5])}
- Market Breadth: {market_data.get('market_breadth')}
- Volatility: {market_data.get('volatility')}
- News Headlines: {len(state['news_headlines'])} articles already collected
"""

            investigate_prompt = f"""You are investigating this market hypothesis:

HYPOTHESIS: {hypothesis['hypothesis']}

{available_data_summary}

QUESTIONS TO INVESTIGATE:
{json.dumps(hypothesis['questions_to_investigate'], indent=2)}

Use the available tools ONLY if you need data beyond what was already collected in Phase 1.

RECOMMENDED TOOLS FOR INVESTIGATION:
1. **get_stock_details(symbol)** - For specific stock analysis (volume, price history, volatility)
2. **search_news(keywords, date_range)** - Search for specific events, catalysts, or company-specific news
3. **get_prediction_markets(query)** - CHECK PROBABILITY CHANGES to validate market expectations
   - Use this to validate hypotheses involving expectations, sentiment, or forward-looking catalysts
   - Example: If NVDA beat expectations, search "NVIDIA earnings" or "NVDA stock price"
   - Example: If Fed policy is mentioned, search "Fed rate" or "interest rate"
   - Look for same-day probability changes that corroborate your hypothesis
4. **get_correlated_moves(symbol, threshold)** - Identify related assets moving together

IMPORTANT: Consider using prediction markets to validate your hypothesis. Market participants vote with money,
so significant probability changes on the same day can provide strong evidence for or against your explanation.

DO NOT re-call get_market_overview or get_sector_returns - that data is already available above.

Call 2-3 relevant tools to investigate this hypothesis."""

            # Call LLM with tools - it will request tool executions
            logger.info(f"Calling LLM to request tools...")
            messages = [HumanMessage(content=investigate_prompt)]
            response = await llm_with_tools.ainvoke(messages)

            # Check if LLM made any tool calls
            if hasattr(response, 'tool_calls') and response.tool_calls and len(response.tool_calls) > 0:
                logger.info(f"LLM requested {len(response.tool_calls)} tool calls:")
                for tc in response.tool_calls:
                    logger.info(f"  • {tc.get('name', 'unknown')} with args: {tc.get('args', {})}")

                # Execute the tool calls
                messages.append(response)  # Add the AIMessage with tool calls

                # Import and map tools
                from langchain_core.messages import ToolMessage

                # Import investigation tools
                tool_map = {
                    "search_news": search_news,
                    "get_stock_details": get_stock_details,
                    "get_prediction_markets": get_prediction_markets,
                    "get_correlated_moves": get_correlated_moves,
                    "get_market_overview": get_market_overview,
                    "get_top_movers": get_top_movers,
                    "get_news_headlines": get_news_headlines,
                    "get_sector_returns": get_sector_returns,
                }

                # Execute each tool call (limit to first 3 for cost)
                for tc in response.tool_calls[:3]:
                    tool_name = tc.get("name")
                    tool_args = tc.get("args", {})
                    tool_id = tc.get("id", "unknown")

                    if tool_name in tool_map:
                        try:
                            logger.info(f"Executing {tool_name}...")
                            tool_result = await tool_map[tool_name].ainvoke(tool_args)

                            # Log summary of tool result
                            if isinstance(tool_result, list):
                                logger.info(f"  → Returned {len(tool_result)} items")
                            elif isinstance(tool_result, dict):
                                logger.info(f"  → Returned data with {len(tool_result)} keys")

                            # Add tool result to messages
                            messages.append(
                                ToolMessage(
                                    content=json.dumps(tool_result, default=str),
                                    tool_call_id=tool_id,
                                    name=tool_name,
                                )
                            )
                            state["tools_used"].append(tool_name)
                        except Exception as e:
                            logger.warning(f"  → Tool {tool_name} failed: {e}")
                            messages.append(
                                ToolMessage(
                                    content=f"Error: {str(e)}",
                                    tool_call_id=tool_id,
                                    name=tool_name,
                                )
                            )
                    else:
                        logger.warning(f"  → Unknown tool: {tool_name}")

                # Now call LLM again with tool results to get analysis
                analysis_prompt = f"""Based on the tool results above, analyze this hypothesis:

HYPOTHESIS: {hypothesis['hypothesis']}

Provide:
1. Summary of evidence SUPPORTING the hypothesis
2. Summary of evidence CONTRADICTING the hypothesis
3. Confidence adjustment (-0.5 to +0.5)
4. Brief explanation of your reasoning

Keep your response concise (2-3 paragraphs max)."""

                messages.append(HumanMessage(content=analysis_prompt))
                logger.info(f"Calling LLM to analyze tool results...")
                final_response = await llm_with_tools.ainvoke(messages)
                analysis = final_response.content

                logger.info(f"LLM Final Analysis (first 300 chars):")
                logger.info(f"  {analysis[:300]}...")

            else:
                logger.info("No tool calls requested by LLM - using direct analysis")
                analysis = response.content if response.content else "Unable to analyze hypothesis"
                logger.info(f"LLM Analysis (first 300 chars):")
                logger.info(f"  {analysis[:300]}...")

            # Parse the analysis to extract confidence adjustment (simple heuristic)
            # Look for phrases like "+0.2" or "increase by 0.15"
            adjustment = 0.1  # Default
            import re
            confidence_match = re.search(r'[+-]?\s*0?\.\d+', analysis)
            if confidence_match:
                try:
                    parsed_adj = float(confidence_match.group().replace(' ', ''))
                    if -0.5 <= parsed_adj <= 0.5:
                        adjustment = parsed_adj
                except:
                    pass

            final_confidence = min(1.0, max(0.0, hypothesis["confidence"] + adjustment))

            # Extract supporting/contradicting evidence (simplified)
            supporting = []
            contradicting = []
            if "support" in analysis.lower():
                supporting.append("Analysis found supporting evidence from tool results")
            else:
                supporting.append("Hypothesis appears consistent with observations")
            if "contradict" in analysis.lower() or "against" in analysis.lower():
                contradicting.append("Analysis found contradicting evidence")

            result = {
                "hypothesis": hypothesis_text,
                "supporting_evidence": supporting,
                "contradicting_evidence": contradicting,
                "additional_context": [analysis[:500]],  # Increased to capture more detail
                "confidence_adjustment": adjustment,
                "final_confidence": final_confidence,
            }

            investigation_results.append(result)
            state["tools_used"].append(f"investigated_{i+1}")

            logger.info(f"Confidence adjustment: {adjustment:+.2f}")
            logger.info(f"Final confidence: {final_confidence:.2f}")
            logger.info(f"{'='*60}\n")

        state["investigation_results"] = investigation_results
        state["intermediate_outputs"].append(
            {"phase": "investigation", "num_investigated": len(investigation_results)}
        )

    except Exception as e:
        logger.error(f"Error in investigation phase: {e}")
        state["errors"].append(f"Investigation phase error: {str(e)}")

        # Fallback: mark hypotheses as investigated with neutral results
        state["investigation_results"] = [
            {
                "hypothesis": h,
                "supporting_evidence": ["Unable to complete investigation"],
                "contradicting_evidence": [],
                "additional_context": [],
                "confidence_adjustment": 0.0,
                "final_confidence": 0.5,
            }
            for h in state["selected_hypotheses"]
        ]

    return state


async def synthesize_node(state: AgentState, config: RunnableConfig, llm) -> AgentState:
    """Phase 4: Synthesis - Create final narrative.

    This node:
    1. Compares investigation results
    2. Combines related hypotheses
    3. Uses LLM to generate coherent narrative
    4. Identifies unexplained moves
    5. Generates forward-looking insights
    """
    logger.info("=== PHASE 4: SYNTHESIS ===")

    state["current_phase"] = "synthesis"

    try:
        synthesis_prompt = f"""You are a financial journalist writing a market wrap-up. Synthesize the following analysis into a cohesive narrative.

INITIAL OBSERVATIONS:
{state['initial_summary']}

INVESTIGATED HYPOTHESES:
{json.dumps(state['investigation_results'], indent=2, default=str)}

Create a narrative with these sections:

1. PRIMARY NARRATIVE (2-3 paragraphs):
   - Main story of the day
   - What drove the market movements
   - Connect multiple factors into a coherent explanation

2. SUPPORTING POINTS (3-4 bullet points):
   - Additional context and details
   - Sector-specific movements
   - Notable individual stock stories

3. UNEXPLAINED MOVES (if any):
   - Significant moves that don't fit the main narrative

4. LOOKING AHEAD (1 paragraph):
   - What to watch for next
   - Potential implications
   - Key upcoming events or catalysts

Write in a clear, professional style. Focus on facts and evidence. Avoid hype or speculation.

Provide your response in this JSON format:
{{
    "headline": "...",
    "primary_narrative": "...",
    "supporting_narratives": ["point 1", "point 2", ...],
    "unexplained_moves": ["move 1", ...],
    "looking_ahead": "...",
    "confidence_score": 0.75
}}

HEADLINE should be a concise, informative title (5-10 words) that captures the day's main story."""

        response = await llm.ainvoke([HumanMessage(content=synthesis_prompt)])
        content = response.content.strip()

        # Parse JSON response
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        synthesis = json.loads(content)

        state["headline"] = synthesis.get("headline", "")
        state["primary_narrative"] = synthesis.get("primary_narrative", "")
        state["supporting_narratives"] = synthesis.get("supporting_narratives", [])
        state["unexplained_moves"] = synthesis.get("unexplained_moves", [])
        state["looking_ahead"] = synthesis.get("looking_ahead", "")
        state["confidence_score"] = synthesis.get("confidence_score", 0.7)

        # Extract key moves explained (simplified)
        state["key_moves_explained"] = {}

        logger.info("Narrative synthesis complete")
        logger.info(f"Primary narrative ({len(state['primary_narrative'])} chars):")
        logger.info(f"  {state['primary_narrative'][:200]}...")
        logger.info(f"Supporting narratives: {len(state['supporting_narratives'])} points")
        logger.info(f"Unexplained moves: {len(state['unexplained_moves'])}")
        logger.info(f"Overall confidence: {state['confidence_score']:.2f}")

        state["intermediate_outputs"].append(
            {
                "phase": "synthesis",
                "narrative_length": len(state["primary_narrative"]),
                "num_supporting": len(state["supporting_narratives"]),
            }
        )

    except Exception as e:
        logger.error(f"Error in synthesis phase: {e}")
        state["errors"].append(f"Synthesis phase error: {str(e)}")

        # Fallback: create a basic narrative
        state["headline"] = f"Market Analysis for {state['date'].strftime('%Y-%m-%d')}"
        state["primary_narrative"] = (
            f"Market analysis for {state['date'].strftime('%Y-%m-%d')}. "
            f"{state['initial_summary']}"
        )
        state["supporting_narratives"] = ["Analysis based on available data"]
        state["unexplained_moves"] = []
        state["looking_ahead"] = "Continue monitoring market developments."
        state["confidence_score"] = 0.5

    return state


# =============================================================================
# Helper Functions
# =============================================================================


def should_continue_investigation(state: AgentState) -> Literal["investigate", "synthesize"]:
    """Determine if we should continue investigating or move to synthesis.

    This is a conditional edge function for more advanced workflows.
    """
    # For now, always proceed to synthesis
    # In future, could check if we need more investigation
    return "synthesize"
