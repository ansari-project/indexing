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
    converter = TafsirConverter()
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
    converter = TafsirConverter()

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
    converter = TafsirConverter()
    result = converter.query_test(
        query="What is the significance of comparing women to coral?",
        metadata_filter="part.to_ayah_int >= 55058 and part.from_ayah_int <= 55058"
    )
    console.print("[green]✓ Query test complete![/green]")


if __name__ == "__main__":
    app()