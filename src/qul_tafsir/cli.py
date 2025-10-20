from pathlib import Path
from typing import Tuple

import typer
from rich.console import Console

from .converter import TafsirConverter

app = typer.Typer()
console = Console()


@app.command()
def download(
    tafsir_name: str = typer.Argument(..., help="Name of the tafsir (e.g., 'ibn-kathir', 'qurtubi')")
):
    """Download a tafsir database from Qul."""
    console.print(f"[bold blue]Downloading {tafsir_name} tafsir...[/bold blue]")
    converter = TafsirConverter()
    converter.download_tafsir(tafsir_name)
    console.print("[green]✓ Download complete![/green]")


@app.command()
def generate_mapping(
    tafsir_name: str = typer.Argument(..., help="Name of the tafsir")
):
    """Generate ayah mapping for a tafsir."""
    console.print(f"[bold blue]Generating ayah mapping for {tafsir_name}...[/bold blue]")
    converter = TafsirConverter()
    converter.generate_ayah_mapping(tafsir_name)
    console.print("[green]✓ Mapping generated![/green]")


@app.command()
def convert(
    tafsir_name: str = typer.Argument(..., help="Name of the tafsir"),
    start_surah: int = typer.Option(1, help="Starting surah number"),
    end_surah: int = typer.Option(2, help="Ending surah number (exclusive)")
):
    """Convert tafsir to Vectara format and upload."""
    console.print(f"[bold blue]Converting {tafsir_name} (surahs {start_surah}-{end_surah-1})...[/bold blue]")
    converter = TafsirConverter(init_vectara=True)
    converter.convert_to_vectara(tafsir_name, surah_range=(start_surah, end_surah))
    console.print("[green]✓ Conversion complete![/green]")


@app.command()
def process(
    tafsir_name: str = typer.Argument(..., help="Name of the tafsir"),
    start_surah: int = typer.Option(1, help="Starting surah number"),
    end_surah: int = typer.Option(115, help="Ending surah number (exclusive)")
):
    """Download, generate mapping, and convert tafsir (complete pipeline)."""
    console.print(f"[bold blue]Processing {tafsir_name}...[/bold blue]")
    converter = TafsirConverter(init_vectara=True)

    console.print("1. Downloading...")
    converter.download_tafsir(tafsir_name)

    console.print("2. Generating ayah mapping...")
    converter.generate_ayah_mapping(tafsir_name)

    console.print(f"3. Converting surahs {start_surah}-{end_surah-1}...")
    converter.convert_to_vectara(tafsir_name, surah_range=(start_surah, end_surah))

    console.print("[green]✓ Complete pipeline finished![/green]")


@app.command()
def test_query():
    """Test query to verify upload was successful."""
    converter = TafsirConverter(init_vectara=True)
    result = converter.query_test(
        query="What is the significance of comparing women to coral?",
        metadata_filter="part.to_ayah_int >= 55058 and part.from_ayah_int <= 55058"
    )
    console.print("[green]✓ Query test complete![/green]")


@app.command()
def convert_agentset(
    tafsir_name: str = typer.Argument(..., help="Name of the tafsir (e.g., 'ibn-kathir')"),
    start_surah: int = typer.Option(1, help="Starting surah number"),
    end_surah: int = typer.Option(2, help="Ending surah number (exclusive)")
):
    """Convert tafsir to Agentset format (individual files with metadata)."""
    console.print(f"[bold blue]Converting {tafsir_name} to Agentset format (surahs {start_surah}-{end_surah-1})...[/bold blue]")
    converter = TafsirConverter()
    converter.convert_to_agentset(tafsir_name, surah_range=(start_surah, end_surah))
    console.print(f"[green]✓ Conversion complete! Files saved to output/{tafsir_name}/sections/[/green]")


@app.command()
def ingest_agentset(
    tafsir_name: str = typer.Argument(..., help="Name of the tafsir to ingest"),
    api_token: str = typer.Option(None, help="Agentset API token (or set AGENTSET_API_TOKEN)"),
    namespace_id: str = typer.Option(None, help="Agentset namespace ID (or set AGENTSET_NAMESPACE_ID)")
):
    """Ingest generated Agentset files using individual file uploads."""
    console.print(f"[bold blue]Ingesting {tafsir_name} to Agentset...[/bold blue]")
    converter = TafsirConverter()
    converter.ingest_to_agentset(tafsir_name, api_token=api_token, namespace_id=namespace_id)
    console.print("[green]✓ Ingestion complete![/green]")


if __name__ == "__main__":
    app()