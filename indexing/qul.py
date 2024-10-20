import requests
import shutil
import bz2
import sqlite3
import logging
import json
from pathlib import Path
from vectara.factory import Factory
from bs4 import BeautifulSoup

tafsirs = {
    "qurtubi": "https://s3.us-east-1.wasabisys.com/static-cdn.tarteel.ai/qul-exports/tafsir/1722589836-w9ne3-ar-tafseer-al-qurtubi.db.bz2",
    "ibn-kathir": "https://s3.us-east-1.wasabisys.com/static-cdn.tarteel.ai/qul-exports/tafsir/1722592431-won0o-en-tafisr-ibn-kathir.db.bz2",
}

CRP_ID = 'tafsirs'
DOWNLOADS_DIR = Path("./downloads").absolute()

# Initialize the client
lg = logging.getLogger("import_tafsir")
lg.setLevel(logging.INFO)
client = Factory(profile="lab").build()
manager = client.corpus_manager

# Log available corpora from the manager
for corpus in manager.find_corpora_with_filter():
    lg.info(f"Available corpus: {corpus}")

def split_html_by_tags(html: str) -> list[str]:
    """
    Split HTML content into individual elements or text.
    
    Args:
        html (str): The HTML content to split.
    
    Returns:
        list: A list of split elements and text nodes.
    """
    soup = BeautifulSoup(html, 'html.parser')
    split_elements = []
    for element in soup.recursiveChildGenerator():
        if element.name:  # It's a tag
            # Only append the tag if it does not have a direct string child, to avoid duplication
            if not element.string or element.string.strip() == "":
                split_elements.append(str(element))
        elif element.string:  # It's a text node
            split_elements.append(element.string.strip())
    # Filter out empty strings
    split_elements = [element for element in split_elements if element]
    return split_elements

def download_tafsir(tafsir_name: str) -> None:
    """
    Download tafsir sqlite file from qul.tarteel.ai.
    
    Args:
        tafsir_name (str): The name of the tafsir to download.
    """

    # Check if downloads/ directory exists, if not, create it
    if not DOWNLOADS_DIR.exists():
        DOWNLOADS_DIR.mkdir()
        lg.info(f"{DOWNLOADS_DIR} directory created")

    # Check if file already downloaded
    file_path = DOWNLOADS_DIR / f"{tafsir_name}.sqlite"
    if file_path.exists():
        lg.info(f"{file_path} already exists, skipping download.")
        return

    # Download the tafsir file from the provided URL
    url = tafsirs.get(tafsir_name)
    if url:
        response = requests.get(url, stream=True)
        compressed_file_path = DOWNLOADS_DIR / f"{tafsir_name}.sqlite.bz2"
        # Save the downloaded compressed file
        with open(compressed_file_path, "wb") as f:
            shutil.copyfileobj(response.raw, f)
        lg.info(f"{compressed_file_path} downloaded")

        # Decompress data from file
        with bz2.open(compressed_file_path, "rb") as f:
            content = f.read()
        
        # Write decompressed data to file
        with open(file_path, "wb") as f:
            f.write(content)
        lg.info(f"{compressed_file_path} decompressed to {file_path}")

def convert_to_vectara(tafsir_name: str, surah_range: tuple[int, int] = (1, 2)) -> None:
    """
    Convert tafsir sqlite file to vectara format.
    
    Args:
        tafsir_name (str): The name of the tafsir to convert.
        surah_range (tuple): The range of surahs to convert (start, end).
    """
    db_path = DOWNLOADS_DIR / f"{tafsir_name}.sqlite"

    # Use a context manager to connect to the sqlite database
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        for surah in range(*surah_range):
            # Fetch all ayahs for the current surah, filtering out empty text fields
            cursor.execute(
                """
                SELECT from_ayah, to_ayah, ayah_keys, text 
                FROM tafsir 
                WHERE ayah_key LIKE ? AND text IS NOT NULL AND text != '';
                """,
                (f'{surah}:%',)
            )
            ayahs = cursor.fetchall()
            v_ayahs = []
            core_doc = {
                "type": "core",
                "id": f"{tafsir_name}-{surah}",
                "metadata": {
                    "tafsir": tafsir_name,
                    "surah": surah
                },
                "document_parts": v_ayahs
            }

            for ayah in ayahs:
                lg.info("Processing ayah: " + ayah[0])

                # Add document parts for each tag extracted from the ayah text
                v_ayahs.append({
                    "metadata": {
                        "from_ayah": ayah[0],
                        "to_ayah": ayah[1],
                        "ayah_keys": ayah[2],
                    },
                    "text": split_html_by_tags(ayah[3])
                })

            # Log total number of parts extracted
            lg.info(f"Total parts: {len(v_ayahs)}")

            # Save core document to JSON file
            json_file_path = DOWNLOADS_DIR / f"{tafsir_name}-{surah}.json"
            with open(json_file_path, "w", encoding="utf-8") as json_file:
                json.dump(core_doc, json_file, indent=4, ensure_ascii=False)

            # Upload the document to Vectara
            lg.info(f"Uploading surah {surah} to Vectara")
            client.documents.create(
                corpus_key=CRP_ID,
                request=core_doc,
                request_timeout=900,
                request_options={"timeout": 900}
            )

# Example usage
download_tafsir("ibn-kathir")
convert_to_vectara("ibn-kathir")
