import bz2
import json
import logging
import shutil
import sqlite3
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from vectara.factory import Factory

tafsirs = {
    "qurtubi": "https://s3.us-east-1.wasabisys.com/static-cdn.tarteel.ai/qul-exports/tafsir/1722589836-w9ne3-ar-tafseer-al-qurtubi.db.bz2",
    "ibn-kathir": "https://s3.us-east-1.wasabisys.com/static-cdn.tarteel.ai/qul-exports/tafsir/1722592431-won0o-en-tafisr-ibn-kathir.db.bz2",
}

CORPUS_KEY = "tafsirs"
DOWNLOADS_DIR = Path("./downloads").absolute()

# Initialize the client
lg = logging.getLogger("import_tafsir")
lg.setLevel(logging.INFO)

client = Factory(profile="lab").build()
manager = client.corpus_manager

# A note on "Ayah ints": Ayah ints are the integer representation of the ayah key.
# It is the same as the surah number multiplied by 1000 and added to the ayah number.
# For example, ayah 1 of surah 1 has an ayah int of 1001, and ayah 2 of surah 1 has an ayah int of 1002.
# This is useful because you can then have ranges between any ayahs, and you can easily compare ayahs.
# For example, if you want to get all ayahs between ayah 1 of surah 1 and ayah 2 of surah 2,
# you can use the range (1001, 2002).


def ayah_key_to_int(ayah_key: str) -> int:
    """
    Get the ayah int from the ayah key.

    Args:
        ayah_key (str): The ayah key to convert.

    Returns:
        int: The ayah int.
    """
    surah, ayah = ayah_key.split(":")
    return int(surah) * 1000 + int(ayah)


def ayah_int_to_key(ayah_int: int) -> str:
    """
    Get the ayah key from the ayah int.

    Args:
        ayah_int (int): The ayah int to convert.

    Returns:
        str: The ayah key.
    """
    surah = ayah_int // 1000
    ayah = ayah_int % 1000
    return f"{surah}:{ayah}"


def split_html_by_tags(html):
    """
    Split HTML content into individual <h1> and <p> elements.

    Args:
        html (str): The HTML content to split.

    Returns:
        list: A list of split elements containing <h1> and <p> tags.
    """
    soup = BeautifulSoup(html, "html.parser")
    split_elements = []
    for element in soup.find_all(["h1", "h2", "p"]):
        split_elements.append(str(element.get_text()))
    lg.info(f"Split elements: {split_elements}")
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


def generate_ayah_mapping(tafsir_name: str) -> None:
    """
    Generate a mapping of ayah keys to group ayah keys.

    Args:
        tafsir_name (str): The name of the tafsir to generate mapping for.
    """
    db_path = DOWNLOADS_DIR / f"{tafsir_name}.sqlite"

    # Use a context manager to connect to the sqlite database
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ayah_key, group_ayah_key FROM tafsir;")
        ayah_raw = cursor.fetchall()
        ayah_mapping = {ayah[0]: ayah[1] for ayah in ayah_raw}

    # Save the mapping to a JSON file
    mapping_file_path = DOWNLOADS_DIR / f"{tafsir_name}-ayah-mapping.json"
    with open(mapping_file_path, "w", encoding="utf-8") as json_file:
        json.dump(ayah_mapping, json_file, indent=4, ensure_ascii=False)
    lg.info(f"Ayah mapping for {tafsir_name} saved to {mapping_file_path}")


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
                SELECT ayah_key, group_ayah_key, from_ayah, to_ayah, ayah_keys, text 
                FROM tafsir 
                WHERE ayah_key LIKE ?;
                """,
                (f"{surah}:%",),
            )
            ayahs = cursor.fetchall()
            v_ayahs = []
            core_doc = {
                "type": "core",
                "id": f"{tafsir_name}-{surah:0>3}",
                "metadata": {"tafsir": tafsir_name, "surah": f"{surah:0>3}"},
                "document_parts": v_ayahs,
            }

            for ayah in ayahs:
                lg.info("Processing ayah: " + ayah[0])
                parts = split_html_by_tags(ayah[5])
                # Add document parts for each tag extracted from the ayah text
                for part in parts:
                    if part:
                        v_ayahs.append(
                            {
                                "metadata": {
                                    "ayah_key": ayah[0],
                                    "group_ayah_key": ayah[1],
                                    "from_ayah": ayah[2],
                                    "to_ayah": ayah[3],
                                    "from_ayah_int": ayah_key_to_int(ayah[2]),
                                    "to_ayah_int": ayah_key_to_int(ayah[3]),
                                    "ayah_keys": ayah[4],
                                },
                                "text": part,
                            }
                        )

            # Log total number of parts extracted
            lg.info(f"Total parts: {len(v_ayahs)}")
            if len(v_ayahs) != 0:
                # Save core document to JSON file
                json_file_path = DOWNLOADS_DIR / f"{tafsir_name}-{surah}.json"
                with open(json_file_path, "w", encoding="utf-8") as json_file:
                    json.dump(core_doc, json_file, indent=4, ensure_ascii=False)

                # Delete the document if it already exists
                lg.info(f"Deleting surah {surah} from Vectara")
                try:
                    client.documents.delete(
                        corpus_key=CORPUS_KEY, document_id=f"{tafsir_name}-{surah}"
                    )
                except Exception as e:
                    lg.info("Could not delete document: " + str(e))
                # Upload the document to Vectara
                lg.info(f"Uploading surah {surah} to Vectara")
                client.documents.create(
                    corpus_key=CORPUS_KEY,
                    request=core_doc,
                    request_timeout=900,
                    request_options={"timeout": 900},
                )
            else:
                lg.info(f"No parts extracted for surah {surah}")


# Example usage
download_tafsir("ibn-kathir")
generate_ayah_mapping("ibn-kathir")
convert_to_vectara("ibn-kathir", surah_range=(1, 115))

# Make a test query to check if the document was uploaded successfully
response = client.corpora.query(
    CORPUS_KEY,
    query="What is the significance of comparing women to coral?",
    # Filter the query to only search ayah 55:58 --> 55058 as an ayah_int
    search={
        "limit": 100,
        "metadata_filter": "part.to_ayah_int <= 55058 and part.from_ayah_int >= 55058",
    },
)

lg.info(f"Result: {response}")
