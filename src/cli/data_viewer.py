"""Data viewer CLI for browsing and analyzing program data."""

import logging
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress

from ..core.config import get_settings
from ..database.repositories import ProgramRepository
from ..models.university import UniversityProgram

logger = logging.getLogger(__name__)
console = Console()


class DataViewer:
    """Interactive data viewer for program information."""

    def __init__(self):
        self.settings = get_settings()
        self.repository = ProgramRepository()

    def view_programs_table(self,
                          programs: List[UniversityProgram],
                          title: str = "Programs") -> None:
        """Display programs in a table format."""
        if not programs:
            console.print("[yellow]No programs to display.[/yellow]")
            return

        table = Table(title=title)
        table.add_column("University", style="cyan", max_width=25)
        table.add_column("Program", style="green", max_width=35)
        table.add_column("Degree", style="blue", max_width=15)
        table.add_column("Country", style="magenta", max_width=15)
        table.add_column("Completeness", style="yellow", max_width=12)
        table.add_column("Updated", style="dim", max_width=12)

        for program in programs:
            completeness = f"{program.data_completeness:.1%}"
            updated = program.last_updated.strftime("%Y-%m-%d") if program.last_updated else "N/A"

            table.add_row(
                program.university_name[:23] + "..." if len(program.university_name) > 23 else program.university_name,
                program.program_name[:33] + "..." if len(program.program_name) > 33 else program.program_name,
                program.degree_type[:13] + "..." if len(program.degree_type) > 13 else program.degree_type,
                program.country[:13] + "..." if len(program.country or "") > 13 else (program.country or "N/A"),
                completeness,
                updated
            )

        console.print(table)

    def view_program_details(self, program: UniversityProgram) -> None:
        """Display detailed information about a single program."""
        details = f"""
[bold cyan]🏛️  {program.university_name}[/bold cyan]
[bold green]📚 {program.program_name}[/bold green]

[bold blue]Basic Information:[/bold blue]
• Degree: {program.degree_type}
• Country: {program.country or 'N/A'}
• City: {program.city or 'N/A'}
• Duration: {program.duration_years or 'N/A'} years

[bold blue]Academic Requirements:[/bold blue]
• GPA: {program.gpa_requirement_min or 'N/A'}
• TOEFL: {program.language_requirements.toefl_min or 'N/A'}
• IELTS: {program.language_requirements.ielts_min or 'N/A'}
• Prerequisites: {', '.join(program.prerequisites) if program.prerequisites else 'N/A'}

[bold blue]Financial Information:[/bold blue]
• Tuition (Domestic): ${program.tuition_fees.domestic_per_year or 'N/A':,}
• Tuition (International): ${program.tuition_fees.international_per_year or 'N/A':,}
• Application Fee: ${program.application_fee or 'N/A':,}

[bold blue]Rankings:[/bold blue]
• QS World: #{program.rankings.qs_world_ranking or 'N/A'}
• THE World: #{program.rankings.the_world_ranking or 'N/A'}
• US News: #{program.rankings.us_news_ranking or 'N/A'}

[bold blue]Description:[/bold blue]
{program.program_description or 'N/A'}

[bold blue]Specializations:[/bold blue]
{', '.join(program.specializations) if program.specializations else 'N/A'}

[bold blue]Research Interests:[/bold blue]
{', '.join(program.faculty_research_interests) if program.faculty_research_interests else 'N/A'}

[dim]Source: {program.source_url}[/dim]
[dim]Last Updated: {program.last_updated.strftime('%Y-%m-%d %H:%M') if program.last_updated else 'N/A'}[/dim]
[dim]Confidence: {program.confidence_score:.1%} | Completeness: {program.data_completeness:.1%}[/dim]
        """

        console.print(Panel(details, title="Program Details", border_style="blue"))

    def search_programs(self) -> None:
        """Interactive program search."""
        console.print("[bold]🔍 Program Search[/bold]")
        console.print("Search by university name, program name, or keywords")
        console.print()

        query = Prompt.ask("Enter search query").strip()

        if not query:
            console.print("[yellow]Empty query, showing all programs...[/yellow]")
            programs = self.repository.get_all_programs(limit=50)
        else:
            programs = self.repository.search(query=query, limit=50)

        if not programs:
            console.print(f"[yellow]No programs found matching: {query}[/yellow]")
            return

        console.print(f"[green]Found {len(programs)} programs:[/green]")
        self.view_programs_table(programs, f"Search Results: {query}")

        # Option to view details
        if len(programs) <= 10 and Confirm.ask("View details for all results?"):
            for i, program in enumerate(programs, 1):
                console.print(f"\n[bold]--- Program {i} ---[/bold]")
                self.view_program_details(program)
                if i < len(programs) and not Confirm.ask("Continue to next program?"):
                    break

    def browse_by_university(self) -> None:
        """Browse programs by university."""
        console.print("[bold]🏛️ Browse by University[/bold]")

        # Get unique universities
        programs = self.repository.get_all_programs()
        universities = sorted(set(p.university_name for p in programs))

        if not universities:
            console.print("[yellow]No universities found.[/yellow]")
            return

        console.print(f"Found {len(universities)} universities:")
        for i, uni in enumerate(universities, 1):
            console.print(f"{i:2d}. {uni}")

        try:
            choice = Prompt.ask("Select university number", default="1")
            idx = int(choice) - 1

            if 0 <= idx < len(universities):
                selected_uni = universities[idx]
                uni_programs = self.repository.get_by_university(selected_uni)

                console.print(f"\n[green]Programs at {selected_uni}:[/green]")
                self.view_programs_table(uni_programs, f"Programs at {selected_uni}")

                # Option to view details
                if Confirm.ask("View program details?"):
                    for program in uni_programs:
                        self.view_program_details(program)
                        if not Confirm.ask("Continue to next program?"):
                            break
            else:
                console.print("[red]Invalid selection.[/red]")

        except ValueError:
            console.print("[red]Invalid input. Please enter a number.[/red]")

    def show_statistics(self) -> None:
        """Display database statistics."""
        console.print("[bold]📊 Database Statistics[/bold]")

        try:
            stats = self.repository.get_statistics()

            if not stats:
                console.print("[yellow]No statistics available.[/yellow]")
                return

            stats_text = f"""
[bold blue]Overview:[/bold blue]
• Total Programs: {stats['total_programs']}
• Average Completeness: {stats['avg_completeness']:.1%}
• Average Confidence: {stats['avg_confidence']:.1%}

[bold blue]Geographic Distribution:[/bold blue]
"""

            for country_info in stats['countries'][:10]:  # Top 10 countries
                stats_text += f"• {country_info['_id']}: {country_info['count']} programs\n"

            stats_text += f"\n[bold blue]Degree Types:[/bold blue]\n"
            for degree, count in stats['degree_types'].items():
                stats_text += f"• {degree}: {count} programs\n"

            if 'tuition_range' in stats:
                tuition = stats['tuition_range']
                stats_text += f"\n[bold blue]Tuition Range:[/bold blue]\n"
                stats_text += f"• Minimum: ${tuition.get('min', 'N/A'):,}\n"
                stats_text += f"• Maximum: ${tuition.get('max', 'N/A'):,}\n"
                stats_text += f"• Average: ${tuition.get('avg', 'N/A'):,}\n"

            console.print(Panel(stats_text, title="Statistics", border_style="green"))

        except Exception as e:
            console.print(f"[red]Error loading statistics: {e}[/red]")

    def run_interactive(self) -> None:
        """Run interactive data viewer."""
        console.print("[bold green]📊 Data Viewer Mode[/bold green]")
        console.print("Browse and analyze university program data")
        console.print()

        while True:
            console.print("\n[bold cyan]Data Viewer Options:[/bold cyan]")
            console.print("1. 🔍 Search programs")
            console.print("2. 🏛️ Browse by university")
            console.print("3. 📊 Show statistics")
            console.print("4. 📋 View all programs")
            console.print("0. 🔙 Back to main menu")

            choice = Prompt.ask("Select option", default="0")

            if choice == "0":
                break
            elif choice == "1":
                self.search_programs()
            elif choice == "2":
                self.browse_by_university()
            elif choice == "3":
                self.show_statistics()
            elif choice == "4":
                programs = self.repository.get_all_programs(limit=100)
                self.view_programs_table(programs, "All Programs")
            else:
                console.print("[red]Invalid option. Please try again.[/red]")

            if choice != "0":
                input("\nPress Enter to continue...")