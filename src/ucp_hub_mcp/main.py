
import typer
import sys
from .client import UCPClient
from .exceptions import UCPError
from rich.console import Console
from rich import print_json
from .config import settings

app = typer.Typer(help="UCP to MCP Hub - Orchestrator CLI")
console = Console()

@app.command()
def discover(url: str = typer.Option(settings.ucp_server_url, help="The URL of the UCP Server to discover", prompt=False if settings.ucp_server_url else "UCP Server URL")):
    """
    Performs dynamic discovery against a UCP Server.
    """
    client = UCPClient()
    console.print(f"[bold blue]Discovering services at {url}...[/bold blue]")

    try:
        discovery_data = client.discover_services(url)
        console.print("[bold green]Success! Found the following capabilities:[/bold green]")
        
        # Dump the Pydantic model to JSON for pretty printing
        json_output = discovery_data.model_dump_json(indent=2, exclude_none=True)
        print_json(json_output)
        
    except UCPError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        sys.exit(1)

def main():
    app()

if __name__ == "__main__":
    main()
