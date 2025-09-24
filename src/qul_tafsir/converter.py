import bz2
import json
import logging
import shutil
import sqlite3
from pathlib import Path
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup
from vectara.factory import Factory


class TafsirConverter:
    """Converter for downloading and processing Tafsir data from Qul."""

    TAFSIRS = {
        "qurtubi": "https://s3.us-east-1.wasabisys.com/static-cdn.tarteel.ai/qul-exports/tafsir/1722589836-w9ne3-ar-tafseer-al-qurtubi.db.bz2",
        "ibn-kathir": "https://s3.us-east-1.wasabisys.com/static-cdn.tarteel.ai/qul-exports/tafsir/1722592431-won0o-en-tafisr-ibn-kathir.db.bz2",
    }

    def __init__(self, corpus_key: str = "tafsirs", downloads_dir: Optional[Path] = None):
        """
        Initialize the TafsirConverter.

        Args:
            corpus_key: The Vectara corpus key to use.
            downloads_dir: Directory for downloads (defaults to ./downloads).
        """
        self.corpus_key = corpus_key
        self.downloads_dir = downloads_dir or Path("./downloads").absolute()

        # Initialize logging
        self.logger = logging.getLogger("tafsir_converter")
        self.logger.setLevel(logging.INFO)

        # Initialize Vectara client
        self.client = Factory(profile="lab").build()
        self.manager = self.client.corpus_manager

    def ayah_key_to_int(self, ayah_key: str) -> int:
        """
        Get the ayah int from the ayah key.

        Ayah ints are the integer representation of the ayah key.
        It is the same as the surah number multiplied by 1000 and added to the ayah number.
        For example, ayah 1 of surah 1 has an ayah int of 1001.

        Args:
            ayah_key: The ayah key to convert (format: "surah:ayah").

        Returns:
            The ayah int.
        """
        surah, ayah = ayah_key.split(":")
        return int(surah) * 1000 + int(ayah)

    def ayah_int_to_key(self, ayah_int: int) -> str:
        """
        Get the ayah key from the ayah int.

        Args:
            ayah_int: The ayah int to convert.

        Returns:
            The ayah key (format: "surah:ayah").
        """
        surah = ayah_int // 1000
        ayah = ayah_int % 1000
        return f"{surah}:{ayah}"

    def split_html_by_tags(self, html: str) -> list:
        """
        Split HTML content into individual <h1> and <p> elements.

        Args:
            html: The HTML content to split.

        Returns:
            A list of split elements containing <h1> and <p> tags.
        """
        soup = BeautifulSoup(html, "html.parser")
        split_elements = []
        for element in soup.find_all(["h1", "h2", "p"]):
            split_elements.append(str(element.get_text()))
        self.logger.info(f"Split elements: {split_elements}")
        return split_elements

    def download_tafsir(self, tafsir_name: str) -> None:
        """
        Download tafsir sqlite file from qul.tarteel.ai.

        Args:
            tafsir_name: The name of the tafsir to download.
        """
        # Check if downloads/ directory exists, if not, create it
        if not self.downloads_dir.exists():
            self.downloads_dir.mkdir()
            self.logger.info(f"{self.downloads_dir} directory created")

        # Check if file already downloaded
        file_path = self.downloads_dir / f"{tafsir_name}.sqlite"
        if file_path.exists():
            self.logger.info(f"{file_path} already exists, skipping download.")
            return

        # Download the tafsir file from the provided URL
        url = self.TAFSIRS.get(tafsir_name)
        if url:
            response = requests.get(url, stream=True)
            compressed_file_path = self.downloads_dir / f"{tafsir_name}.sqlite.bz2"
            # Save the downloaded compressed file
            with open(compressed_file_path, "wb") as f:
                shutil.copyfileobj(response.raw, f)
            self.logger.info(f"{compressed_file_path} downloaded")

            # Decompress data from file
            with bz2.open(compressed_file_path, "rb") as f:
                content = f.read()

            # Write decompressed data to file
            with open(file_path, "wb") as f:
                f.write(content)
            self.logger.info(f"{compressed_file_path} decompressed to {file_path}")

    def generate_ayah_mapping(self, tafsir_name: str) -> None:
        """
        Generate a mapping of ayah keys to group ayah keys.

        Args:
            tafsir_name: The name of the tafsir to generate mapping for.
        """
        db_path = self.downloads_dir / f"{tafsir_name}.sqlite"

        # Use a context manager to connect to the sqlite database
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ayah_key, group_ayah_key FROM tafsir;")
            ayah_raw = cursor.fetchall()
            ayah_mapping = {ayah[0]: ayah[1] for ayah in ayah_raw}

        # Save the mapping to a JSON file
        mapping_file_path = self.downloads_dir / f"{tafsir_name}-ayah-mapping.json"
        with open(mapping_file_path, "w", encoding="utf-8") as json_file:
            json.dump(ayah_mapping, json_file, indent=4, ensure_ascii=False)
        self.logger.info(f"Ayah mapping for {tafsir_name} saved to {mapping_file_path}")

    def convert_to_vectara(self, tafsir_name: str, surah_range: Tuple[int, int] = (1, 2)) -> None:
        """
        Convert tafsir sqlite file to vectara format.

        Args:
            tafsir_name: The name of the tafsir to convert.
            surah_range: The range of surahs to convert (start, end).
        """
        db_path = self.downloads_dir / f"{tafsir_name}.sqlite"

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
                    self.logger.info("Processing ayah: " + ayah[0])
                    parts = self.split_html_by_tags(ayah[5])
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
                                        "from_ayah_int": self.ayah_key_to_int(ayah[2]),
                                        "to_ayah_int": self.ayah_key_to_int(ayah[3]),
                                        "ayah_keys": ayah[4],
                                    },
                                    "text": part,
                                }
                            )

                # Log total number of parts extracted
                self.logger.info(f"Total parts: {len(v_ayahs)}")
                if len(v_ayahs) != 0:
                    # Save core document to JSON file
                    json_file_path = self.downloads_dir / f"{tafsir_name}-{surah}.json"
                    with open(json_file_path, "w", encoding="utf-8") as json_file:
                        json.dump(core_doc, json_file, indent=4, ensure_ascii=False)

                    # Delete the document if it already exists
                    self.logger.info(f"Deleting surah {surah} from Vectara")
                    try:
                        self.client.documents.delete(
                            corpus_key=self.corpus_key, document_id=f"{tafsir_name}-{surah}"
                        )
                    except Exception as e:
                        self.logger.info("Could not delete document: " + str(e))
                    # Upload the document to Vectara
                    self.logger.info(f"Uploading surah {surah} to Vectara")
                    self.client.documents.create(
                        corpus_key=self.corpus_key,
                        request=core_doc,
                        request_timeout=900,
                        request_options={"timeout": 900},
                    )
                else:
                    self.logger.info(f"No parts extracted for surah {surah}")

    def query_test(self, query: str, metadata_filter: str) -> dict:
        """
        Make a test query to check if documents were uploaded successfully.

        Args:
            query: The search query.
            metadata_filter: The metadata filter for the search.

        Returns:
            The query response.
        """
        response = self.client.corpora.query(
            self.corpus_key,
            query=query,
            search={
                "limit": 100,
                "metadata_filter": metadata_filter,
            },
        )
        self.logger.info(f"Result: {response}")
        return response