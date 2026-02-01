"""
Generate PNG visualization of the LangGraph workflow.

Usage:
    python -m src.workflow.visualize [output_path]
"""

import sys
from pathlib import Path

from src.workflow.graph import create_workflow


def generate_mermaid() -> str:
    """Generate Mermaid diagram syntax for the workflow."""
    workflow = create_workflow()
    graph = workflow.get_graph()
    return graph.draw_mermaid()


def generate_png(output_path: str = "workflow_graph.png") -> str:
    """
    Generate PNG image of the workflow graph.

    Args:
        output_path: Path to save the PNG file

    Returns:
        Path to the generated PNG file
    """
    workflow = create_workflow()
    graph = workflow.get_graph()

    # Try different methods to generate PNG
    try:
        # Method 1: Use draw_mermaid_png (requires mermaid CLI or API)
        png_data = graph.draw_mermaid_png()
        Path(output_path).write_bytes(png_data)
        return output_path
    except Exception:
        pass

    try:
        # Method 2: Use pygraphviz if available
        png_data = graph.draw_png()
        Path(output_path).write_bytes(png_data)
        return output_path
    except Exception:
        pass

    # Method 3: Fallback to Mermaid text file
    mermaid_path = output_path.replace(".png", ".mmd")
    mermaid_content = graph.draw_mermaid()
    Path(mermaid_path).write_text(mermaid_content)
    print(f"PNG generation failed. Mermaid diagram saved to: {mermaid_path}")
    print("You can render it at: https://mermaid.live")
    return mermaid_path


def generate_ascii() -> str:
    """Generate ASCII representation of the workflow."""
    return """
    ┌─────────────────────────────────────────────────────────┐
    │                    TICKET WORKFLOW                       │
    └─────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │    __start__    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    classify     │  Categorize ticket
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    extract      │  Extract entities
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    research     │  Query KB + history
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     draft       │  Generate response
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     review      │  Quality check
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    finalize     │  Final response
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     __end__     │
                    └─────────────────┘
    """


def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else "workflow_graph.png"

    print("Generating workflow visualization...")
    print()

    # Print ASCII representation
    print(generate_ascii())

    # Generate Mermaid
    print("\n--- Mermaid Diagram ---")
    print(generate_mermaid())

    # Generate PNG
    print(f"\n--- Generating PNG: {output_path} ---")
    result = generate_png(output_path)
    print(f"Saved to: {result}")


if __name__ == "__main__":
    main()
