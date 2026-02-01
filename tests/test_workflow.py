"""Tests for the workflow layer."""

import pytest
from unittest.mock import patch, MagicMock


class TestWorkflowGraph:
    def test_workflow_has_all_nodes(self):
        """Test that workflow contains all expected nodes."""
        from src.workflow.graph import create_workflow

        workflow = create_workflow()
        graph = workflow.get_graph()
        nodes = list(graph.nodes.keys())

        expected_nodes = ["classify", "extract", "research", "draft", "review", "finalize"]
        for node in expected_nodes:
            assert node in nodes, f"Missing node: {node}"

    def test_workflow_compiles(self):
        """Test that workflow compiles without errors."""
        from src.workflow.graph import get_compiled_workflow

        compiled = get_compiled_workflow()
        assert compiled is not None


class TestVisualization:
    def test_generate_mermaid(self):
        """Test Mermaid diagram generation."""
        from src.workflow.visualize import generate_mermaid

        mermaid = generate_mermaid()

        assert "graph" in mermaid.lower() or "flowchart" in mermaid.lower() or "statediagram" in mermaid.lower()
        assert "classify" in mermaid
        assert "finalize" in mermaid

    def test_generate_ascii(self):
        """Test ASCII diagram generation."""
        from src.workflow.visualize import generate_ascii

        ascii_diagram = generate_ascii()

        assert "classify" in ascii_diagram
        assert "extract" in ascii_diagram
        assert "research" in ascii_diagram
        assert "draft" in ascii_diagram
        assert "review" in ascii_diagram
        assert "finalize" in ascii_diagram


class TestWorkflowNodes:
    @patch("src.workflow.nodes.llm")
    def test_classify_node_returns_classification(self, mock_llm):
        """Test classify node returns valid classification."""
        from src.workflow.nodes import classify_node
        from src.workflow.state import WorkflowState

        mock_llm.invoke.return_value = MagicMock(content="account")

        state = WorkflowState(
            ticket_id="test-123",
            customer_id="cust1",
            subject="Cannot login",
            body="I forgot my password",
        )

        result = classify_node(state)

        assert "classification" in result
        assert result["classification"] in ["billing", "technical", "account", "general"]

    @patch("src.workflow.nodes.llm")
    def test_extract_node_returns_entities(self, mock_llm):
        """Test extract node returns entities dict."""
        from src.workflow.nodes import extract_node
        from src.workflow.state import WorkflowState

        mock_llm.invoke.return_value = MagicMock(
            content='{"order_id": null, "product": null, "issue_type": "login", "urgency": "medium"}'
        )

        state = WorkflowState(
            ticket_id="test-123",
            customer_id="cust1",
            subject="Cannot login",
            body="I forgot my password",
        )

        result = extract_node(state)

        assert "entities" in result
        assert isinstance(result["entities"], dict)
