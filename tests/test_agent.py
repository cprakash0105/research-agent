import pytest
from unittest.mock import patch, MagicMock
from app.agent import build_agent, planner_node, researcher_node, analyst_node, writer_node
from app.models import AgentState


class TestAgentGraph:
    """Test agent graph structure and compilation."""

    def test_agent_builds_successfully(self):
        agent = build_agent()
        assert agent is not None

    def test_agent_has_correct_nodes(self):
        agent = build_agent()
        # The compiled graph should have our nodes
        graph_nodes = agent.get_graph().nodes
        assert "planner" in graph_nodes
        assert "researcher" in graph_nodes
        assert "analyst" in graph_nodes
        assert "writer" in graph_nodes


class TestPlannerNode:
    """Test planner node logic."""

    @patch("app.agent._get_llm")
    def test_planner_returns_sub_questions(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = '["What is X?", "How does X work?", "Who uses X?"]'
        mock_response.response_metadata = {}
        mock_llm.return_value.invoke.return_value = mock_response

        state = {"query": "Tell me about X", "sub_questions": [], "sources": [], "vector_store": None, "analysis": "", "report": ""}
        result = planner_node(state)
        assert "sub_questions" in result
        assert len(result["sub_questions"]) == 3

    @patch("app.agent._get_llm")
    def test_planner_limits_to_5_questions(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = '["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7"]'
        mock_response.response_metadata = {}
        mock_llm.return_value.invoke.return_value = mock_response

        state = {"query": "Big topic", "sub_questions": [], "sources": [], "vector_store": None, "analysis": "", "report": ""}
        result = planner_node(state)
        assert len(result["sub_questions"]) <= 5

    @patch("app.agent._get_llm")
    def test_planner_handles_json_in_code_block(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = '```json\n["Q1", "Q2"]\n```'
        mock_response.response_metadata = {}
        mock_llm.return_value.invoke.return_value = mock_response

        state = {"query": "Test", "sub_questions": [], "sources": [], "vector_store": None, "analysis": "", "report": ""}
        result = planner_node(state)
        assert len(result["sub_questions"]) == 2

    @patch("app.agent._get_llm")
    def test_planner_fallback_on_invalid_json(self, mock_llm):
        mock_response = MagicMock()
        mock_response.content = "- Question one\n- Question two\n- Question three"
        mock_response.response_metadata = {}
        mock_llm.return_value.invoke.return_value = mock_response

        state = {"query": "Test", "sub_questions": [], "sources": [], "vector_store": None, "analysis": "", "report": ""}
        result = planner_node(state)
        assert len(result["sub_questions"]) > 0


class TestResearcherNode:
    """Test researcher node logic."""

    @patch("app.agent.build_vector_store")
    @patch("app.agent.search_web")
    def test_researcher_searches_all_questions(self, mock_search, mock_vs):
        from app.models import Source
        mock_search.return_value = [Source(title="Result", url="https://example.com", content="Content", query="q")]
        mock_vs.return_value = MagicMock()

        state = {"query": "Test", "sub_questions": ["Q1", "Q2", "Q3"], "sources": [], "vector_store": None, "analysis": "", "report": ""}
        result = researcher_node(state)
        assert mock_search.call_count == 3
        assert len(result["sources"]) == 3

    @patch("app.agent.build_vector_store")
    @patch("app.agent.search_web")
    def test_researcher_handles_search_failure(self, mock_search, mock_vs):
        mock_search.side_effect = Exception("API error")
        mock_vs.return_value = None

        state = {"query": "Test", "sub_questions": ["Q1"], "sources": [], "vector_store": None, "analysis": "", "report": ""}
        result = researcher_node(state)
        assert result["sources"] == []


class TestWriterNode:
    """Test writer node logic."""

    @patch("app.agent._get_llm")
    def test_writer_generates_report(self, mock_llm):
        from app.models import Source
        mock_response = MagicMock()
        mock_response.content = "# Research Report\n\nFindings here."
        mock_response.response_metadata = {}
        mock_llm.return_value.invoke.return_value = mock_response

        state = {
            "query": "Test",
            "sub_questions": ["Q1"],
            "sources": [Source(title="S1", url="https://example.com", content="Content", query="Q1")],
            "vector_store": None,
            "analysis": "Key finding: X is important.",
            "report": "",
        }
        result = writer_node(state)
        assert "report" in result
        assert len(result["report"]) > 0

    @patch("app.agent._get_llm")
    def test_writer_deduplicates_sources(self, mock_llm):
        from app.models import Source
        mock_response = MagicMock()
        mock_response.content = "Report"
        mock_response.response_metadata = {}
        mock_llm.return_value.invoke.return_value = mock_response

        # Same URL appears twice
        sources = [
            Source(title="S1", url="https://example.com/same", content="A", query="Q1"),
            Source(title="S1", url="https://example.com/same", content="B", query="Q2"),
        ]
        state = {"query": "Test", "sub_questions": ["Q1"], "sources": sources, "vector_store": None, "analysis": "Analysis", "report": ""}
        result = writer_node(state)
        # Should still produce a report (dedup happens internally)
        assert "report" in result
