"""CLI dashboard for the University Recommendation System."""

import logging
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns

from ..core.config import get_settings
from ..database.repositories import ProgramRepository
from ..analyzers.quality_analyzer import QualityAnalyzer

logger = logging.getLogger(__name__)
console = Console()


class Dashboard:
    """Interactive CLI dashboard for the system."""

    def __init__(self):
        self.settings = get_settings()
        self.repository = ProgramRepository()
        self.analyzer = QualityAnalyzer()

    def show_welcome(self) -> None:
        """Display welcome message and system status."""
        welcome_text = """
[bold blue]🏛️  UNIVERSITY RECOMMENDATION SYSTEM[/bold blue]
[green]AI-Powered Computer Science Program Analysis[/green]

[dim]Comprehensive data collection from 25+ global universities[/dim]
        """

        console.print(Panel(welcome_text, title="Welcome", border_style="blue"))

    def show_system_status(self) -> None:
        """Display system status and statistics."""
        try:
            # Get database statistics
            stats = self.repository.get_statistics()

            # Create status table
            status_table = Table(title="System Status")
            status_table.add_column("Component", style="cyan")
            status_table.add_column("Status", style="green")
            status_table.add_column("Details", style="yellow")

            # Database status
            db_status = "✅ Connected" if stats else "❌ Disconnected"
            db_details = f"{stats.get('total_programs', 0)} programs" if stats else "N/A"

            status_table.add_row("Database", db_status, db_details)
            status_table.add_row("Configuration", "✅ Loaded", f"Model: {self.settings.llm.model}")
            status_table.add_row("Scraping", "✅ Ready", f"Timeout: {self.settings.scraping.timeout}s")

            console.print(status_table)

        except Exception as e:
            console.print(f"[red]Error loading system status: {e}[/red]")

    def show_data_overview(self) -> None:
        """Display data overview and quality metrics."""
        try:
            programs = self.repository.get_all_programs(limit=1000)  # Sample for performance

            if not programs:
                console.print("[yellow]No programs found in database.[/yellow]")
                return

            # Quality analysis
            analysis = self.analyzer.analyze_data_quality(programs)

            # Create overview table
            overview_table = Table(title="Data Overview")
            overview_table.add_column("Metric", style="cyan")
            overview_table.add_column("Value", style="green")
            overview_table.add_column("Status", style="yellow")

            overview_table.add_row(
                "Total Programs",
                str(analysis.total_programs),
                "✅" if analysis.total_programs > 0 else "❌"
            )

            completeness_pct = f"{analysis.average_completeness:.1%}"
            completeness_status = "✅" if analysis.average_completeness >= 0.7 else "⚠️"
            overview_table.add_row("Avg Completeness", completeness_pct, completeness_status)

            quality_pct = f"{analysis.quality_score:.1%}"
            quality_status = "✅" if analysis.quality_score >= 0.7 else "⚠️"
            overview_table.add_row("Quality Score", quality_pct, quality_status)

            console.print(overview_table)

            # Show issues if any
            if analysis.issues_found:
                issues_panel = Panel(
                    "\n".join(f"• {issue}" for issue in analysis.issues_found[:5]),
                    title=f"Top Issues ({len(analysis.issues_found)} total)",
                    border_style="red"
                )
                console.print(issues_panel)

        except Exception as e:
            console.print(f"[red]Error loading data overview: {e}[/red]")

    def show_recent_activity(self) -> None:
        """Display recent scraping activity."""
        try:
            recent_programs = self.repository.get_recent_programs(days=7)

            if not recent_programs:
                console.print("[dim]No recent activity (last 7 days)[/dim]")
                return

            # Create activity table
            activity_table = Table(title="Recent Activity (Last 7 Days)")
            activity_table.add_column("University", style="cyan", max_width=30)
            activity_table.add_column("Program", style="green", max_width=40)
            activity_table.add_column("Updated", style="yellow")

            for program in recent_programs[:10]:  # Show last 10
                updated_str = program.last_updated.strftime("%Y-%m-%d %H:%M") if program.last_updated else "N/A"
                activity_table.add_row(
                    program.university_name[:28] + "..." if len(program.university_name) > 28 else program.university_name,
                    program.program_name[:38] + "..." if len(program.program_name) > 38 else program.program_name,
                    updated_str
                )

            console.print(activity_table)

        except Exception as e:
            console.print(f"[red]Error loading recent activity: {e}[/red]")

    def show_quick_actions(self) -> None:
        """Display quick action menu."""
        actions_text = """
[dim]Quick Actions:[/dim]

[1] 🔍 [link=command:urs search]Search Programs[/link]          [6] 📊 [link=command:urs analyze]Quality Analysis[/link]
[2] 🆕 [link=command:urs scrape]Scrape New Data[/link]          [7] 📤 [link=command:urs export]Export Data[/link]
[3] 👀 [link=command:urs view]View Programs[/link]              [8] 🔧 [link=command:urs config]Configuration[/link]
[4] ✅ [link=command:urs validate]Validate URLs[/link]          [9] 📋 [link=command:urs monitor]Monitor Quality[/link]
[5] 🏛️ [link=command:urs universities]University Stats[/link]   [0] ❌ [link=command:urs exit]Exit[/link]

[dim]Type 'urs <command>' or use the links above[/dim]
        """

        console.print(Panel(actions_text, title="Quick Actions", border_style="green"))

    def display_full_dashboard(self) -> None:
        """Display the complete dashboard."""
        console.clear()

        self.show_welcome()
        console.print()

        # Create columns for status and overview
        status_col = Columns([])
        self.show_system_status()

        console.print()
        self.show_data_overview()

        console.print()
        self.show_recent_activity()

        console.print()
        self.show_quick_actions()

    def run_interactive(self) -> None:
        """Run interactive dashboard mode."""
        try:
            while True:
                self.display_full_dashboard()

                console.print("\n[dim]Press Enter to refresh, 'q' to quit:[/dim] ", end="")
                choice = input().strip().lower()

                if choice in ['q', 'quit', 'exit']:
                    console.print("[green]Goodbye! 👋[/green]")
                    break
                elif choice == '':
                    continue  # Refresh
                else:
                    console.print(f"[yellow]Unknown command: {choice}[/yellow]")
                    console.print("[dim]Type 'q' to quit or press Enter to refresh[/dim]")
                    input()

        except KeyboardInterrupt:
            console.print("\n[green]Goodbye! 👋[/green]")
        except Exception as e:
            console.print(f"[red]Dashboard error: {e}[/red]")