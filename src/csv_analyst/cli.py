"""
Command-line interface for csv-analyst.

Usage:
    csv-analyst run data.csv --output report.md
    csv-analyst run data.csv --output report.md --charts-dir ./plots
    csv-analyst run data.csv --no-llm
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from csv_analyst import __version__
from csv_analyst.pipeline import AnalysisPipeline

console = Console()


@click.group()
@click.version_option(__version__, prog_name="csv-analyst")
def main() -> None:
    """CSV Analyst — AI-powered CSV data analysis agent.

    Auto-detect column types, generate statistical summaries, find
    anomalies, create charts, and produce markdown reports.
    """


@main.command()
@click.argument("csv_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("report.md"),
    help="Path for the output markdown report (default: report.md).",
    show_default=True,
)
@click.option(
    "--charts-dir",
    "-c",
    type=click.Path(path_type=Path),
    default=Path("./charts"),
    help="Directory to save chart PNGs (default: ./charts).",
    show_default=True,
)
@click.option(
    "--no-llm",
    is_flag=True,
    default=False,
    help="Skip LLM-based AI analysis (offline mode).",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show detailed progress information.",
)
def run(
    csv_file: Path,
    output: Path,
    charts_dir: Path,
    no_llm: bool,
    verbose: bool,
) -> None:
    """Analyse a CSV file and produce a markdown report with charts.

    \b
    Examples:
        csv-analyst run sales.csv
        csv-analyst run data.csv -o analysis.md -c ./plots
        csv-analyst run data.csv --no-llm
    """
    # ── Header ────────────────────────────────────────────────────────
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]CSV Analyst[/bold cyan] v{__version__}  •  [dim]AI-powered CSV data analysis[/dim]",
            border_style="cyan",
        )
    )
    console.print(f"[dim]Input:[/dim]  {csv_file}")
    console.print(f"[dim]Report:[/dim] {output}")
    console.print(f"[dim]Charts:[/dim] {charts_dir}")
    console.print(f"[dim]LLM:[/dim]    {'[red]Off[/red]' if no_llm else '[green]On[/green]'}")
    console.print()

    # ── Run pipeline ──────────────────────────────────────────────────
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]Analysing CSV...", total=None)

        try:
            pipeline = AnalysisPipeline(llm_enabled=not no_llm)
            result = pipeline.run(csv_file, output_dir=charts_dir)
        except FileNotFoundError as e:
            progress.stop()
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            progress.stop()
            console.print(f"[red]Unexpected error:[/red] {e}")
            if verbose:
                console.print_exception()
            sys.exit(1)

        progress.update(task, description="[green]Analysis complete![/green]")

    # ── Summary table ─────────────────────────────────────────────────
    console.print()
    table = Table(title="Analysis Summary", title_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("Rows", f"{result.profile.row_count:,}")
    table.add_row("Columns", str(result.profile.column_count))
    table.add_row("Anomalies", str(result.anomalies.total_count))
    table.add_row("Charts generated", str(len(result.charts)))
    table.add_row(
        "AI analysis",
        "✅ Included" if result.llm_analysis and result.llm_analysis.executive_summary else "⏭️ Skipped",
    )

    console.print(table)
    console.print()

    # ── Write report ──────────────────────────────────────────────────
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result.report_markdown, encoding="utf-8")
    console.print(f"[green]✅ Report written to[/green] [bold]{output}[/bold]")

    # ── Chart summary ─────────────────────────────────────────────────
    if result.charts:
        console.print(f"\n[dim]Charts saved to {charts_dir}/:[/dim]")
        for chart in result.charts:
            console.print(f"  📊 [cyan]{chart.file_name}[/cyan] — {chart.title}")

    # ── LLM summary snippet ───────────────────────────────────────────
    if result.llm_analysis and result.llm_analysis.executive_summary:
        console.print()
        console.print(
            Panel(
                result.llm_analysis.executive_summary,
                title="🤖 AI Summary",
                border_style="green",
            )
        )

    # ── Recommendations ───────────────────────────────────────────────
    if result.llm_analysis and result.llm_analysis.recommendations:
        console.print("[bold]🚀 Recommendations:[/bold]")
        for rec in result.llm_analysis.recommendations:
            console.print(f"  • {rec}")

    console.print()
    console.print("[dim]Done![/dim] ✨")


@main.command()
def version() -> None:
    """Print the version and exit."""
    console.print(f"csv-analyst v{__version__}")


if __name__ == "__main__":
    main()
