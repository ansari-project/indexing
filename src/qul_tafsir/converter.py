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

    def __init__(self, corpus_key: str = "tafsirs", downloads_dir: Optional[Path] = None, init_vectara: bool = False):
        """
        Initialize the TafsirConverter.

        Args:
            corpus_key: The Vectara corpus key to use.
            downloads_dir: Directory for downloads (defaults to ./downloads).
            init_vectara: Whether to initialize Vectara client (only needed for Vectara operations).
        """
        self.corpus_key = corpus_key
        self.downloads_dir = downloads_dir or Path("./downloads").absolute()

        # Initialize logging
        self.logger = logging.getLogger("tafsir_converter")
        self.logger.setLevel(logging.INFO)

        # Initialize Vectara client only when needed
        self.client = None
        self.manager = None
        if init_vectara:
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

        Raises:
            ValueError: If ayah_key format is invalid.
        """
        if not ayah_key or ":" not in ayah_key:
            raise ValueError(f"Invalid ayah_key format: '{ayah_key}'. Expected 'surah:ayah'")

        parts = ayah_key.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid ayah_key format: '{ayah_key}'. Expected exactly one ':'")

        try:
            surah = int(parts[0])
            ayah = int(parts[1])
        except ValueError:
            raise ValueError(f"Invalid ayah_key format: '{ayah_key}'. Surah and ayah must be integers")

        return surah * 1000 + ayah

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

    def _generate_section_metadata(
        self,
        tafsir_name: str,
        surah: int,
        ayah_key: str,
        group_ayah_key: str,
        from_ayah: str,
        to_ayah: str,
        ayah_keys: str,
    ) -> dict:
        """
        Generate metadata dictionary for a tafsir section.

        Args:
            tafsir_name: Name of the tafsir (e.g., 'ibn-kathir')
            surah: Surah number
            ayah_key: The ayah key for this section
            group_ayah_key: The group ayah key (unique identifier)
            from_ayah: Starting ayah in format "surah:ayah"
            to_ayah: Ending ayah in format "surah:ayah"
            ayah_keys: Comma-separated list of ayah keys in this section

        Returns:
            Dictionary containing metadata for the section
        """
        return {
            "tafsir_name": tafsir_name,
            "surah": surah,
            "ayah_key": ayah_key,
            "group_ayah_key": group_ayah_key,
            "from_ayah": from_ayah,
            "to_ayah": to_ayah,
            "from_ayah_int": self.ayah_key_to_int(from_ayah),
            "to_ayah_int": self.ayah_key_to_int(to_ayah),
            "ayah_keys": ayah_keys,
        }

    def convert_to_agentset(
        self, tafsir_name: str, surah_range: Tuple[int, int] = (1, 2), output_dir: Optional[Path] = None
    ) -> None:
        """
        Convert tafsir sqlite file to agentset format.

        Creates individual text files with metadata for each tafsir section.
        Each section covers a range of ayahs and is stored as a separate file.

        Args:
            tafsir_name: The name of the tafsir to convert (e.g., 'ibn-kathir')
            surah_range: The range of surahs to convert (start, end)
            output_dir: Directory for output files (defaults to ./output)
        """
        db_path = self.downloads_dir / f"{tafsir_name}.sqlite"
        output_base = output_dir or Path("./output").absolute()

        # Use a context manager to connect to the sqlite database
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            for surah in range(*surah_range):
                # Create output directory for this surah
                surah_dir = output_base / tafsir_name / "sections" / f"surah-{surah:03d}"
                surah_dir.mkdir(parents=True, exist_ok=True)

                # Fetch all sections for the current surah
                cursor.execute(
                    """
                    SELECT ayah_key, group_ayah_key, from_ayah, to_ayah, ayah_keys, text
                    FROM tafsir
                    WHERE ayah_key LIKE ?;
                    """,
                    (f"{surah}:%",),
                )
                sections = cursor.fetchall()

                self.logger.info(f"Processing {len(sections)} sections for surah {surah}")

                for section in sections:
                    ayah_key, group_ayah_key, from_ayah, to_ayah, ayah_keys, html_text = section

                    # Check for NULL or empty html_text from database
                    if not html_text:
                        self.logger.warning(f"No HTML for section {group_ayah_key}, skipping")
                        continue

                    # Strip HTML tags to get plain text using faster lxml parser
                    soup = BeautifulSoup(html_text, "lxml")
                    plain_text = soup.get_text(separator="\n", strip=True)

                    if not plain_text:
                        self.logger.warning(f"Empty text for section {group_ayah_key}, skipping")
                        continue

                    # Sanitize group_ayah_key for Windows-compatible filenames (replace : with -)
                    safe_id = group_ayah_key.replace(":", "-")

                    # Generate filenames
                    section_filename = f"section-{safe_id}.txt"
                    metadata_filename = f"section-{safe_id}.metadata.json"

                    # Write text file
                    text_path = surah_dir / section_filename
                    with open(text_path, "w", encoding="utf-8") as f:
                        f.write(plain_text)

                    # Generate and write metadata
                    metadata = self._generate_section_metadata(
                        tafsir_name=tafsir_name,
                        surah=surah,
                        ayah_key=ayah_key,
                        group_ayah_key=group_ayah_key,
                        from_ayah=from_ayah,
                        to_ayah=to_ayah,
                        ayah_keys=ayah_keys,
                    )
                    metadata_path = surah_dir / metadata_filename
                    with open(metadata_path, "w", encoding="utf-8") as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)

                    self.logger.info(f"Created section {group_ayah_key}: {text_path}")

                self.logger.info(f"Completed surah {surah}")

    def ingest_to_agentset(self, tafsir_name: str, output_dir: Optional[Path] = None, api_token: Optional[str] = None, namespace_id: Optional[str] = None) -> None:
        """
        Ingest generated tafsir files into Agentset using batch upload per surah.

        Args:
            tafsir_name: The name of the tafsir to ingest
            output_dir: Directory containing the generated files (defaults to ./output)
            api_token: Agentset API token (uses AGENTSET_API_TOKEN env var if not provided)
            namespace_id: Agentset namespace ID (uses AGENTSET_NAMESPACE_ID env var if not provided)
        """
        import os
        import requests
        from dotenv import load_dotenv
        from agentset import Agentset
        from agentset.models import BatchPayload, BatchPayloadItemManagedFile, IngestJobConfig

        # Load environment variables
        load_dotenv()

        # Get API credentials
        token = api_token or os.getenv("AGENTSET_API_TOKEN")
        namespace = namespace_id or os.getenv("AGENTSET_NAMESPACE_ID")

        if not token:
            print("❌ AGENTSET_API_TOKEN not provided", flush=True)
            return
        if not namespace:
            print("❌ AGENTSET_NAMESPACE_ID not provided", flush=True)
            return

        output_base = output_dir or Path("./output").absolute()
        sections_dir = output_base / tafsir_name / "sections"

        if not sections_dir.exists():
            print(f"❌ Sections directory not found: {sections_dir}", flush=True)
            return

        # Initialize Agentset client
        client = Agentset(token=token, namespace_id=namespace)

        # Get all surah directories
        surah_dirs = sorted([d for d in sections_dir.iterdir() if d.is_dir() and d.name.startswith("surah-")])
        
        if not surah_dirs:
            print(f"❌ No surah directories found in {sections_dir}", flush=True)
            return

        print(f"\n📊 Found {len(surah_dirs)} surahs to process", flush=True)

        # Process each surah as a separate batch
        for surah_dir in surah_dirs:
            surah_name = surah_dir.name  # e.g., "surah-001"
            text_files = list(surah_dir.glob("*.txt"))
            
            if not text_files:
                print(f"\n⚠️  {surah_name}: No text files found, skipping", flush=True)
                continue

            print(f"\n📖 Processing {surah_name} ({len(text_files)} sections)", flush=True)

            # Upload files for this surah
            uploaded_keys = []
            uploaded_count = 0
            skipped_count = 0
            current_surah = None

            for text_file in text_files:
                metadata_file = text_file.parent / f"{text_file.stem}.metadata.json"

                if not metadata_file.exists():
                    print(f"⚠️  Missing metadata for {text_file.name}", flush=True)
                    skipped_count += 1
                    continue

                try:
                    with open(text_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)

                    # Show surah progress
                    surah = metadata.get('surah')
                    if surah != current_surah:
                        current_surah = surah
                        print(f"\n📖 Surah {surah}", flush=True)

                    # Upload to S3
                    file_size = text_file.stat().st_size
                    upload_result = client.uploads.create(
                        file_name=text_file.name,
                        content_type="text/plain",
                        file_size=float(file_size)
                    )

                    response = requests.put(
                        upload_result.data.url,
                        data=content.encode('utf-8'),
                        headers={"Content-Type": "text/plain"}
                    )
                    response.raise_for_status()

                    uploaded_keys.append(BatchPayloadItemManagedFile(
                        key=upload_result.data.key,
                        file_name=text_file.name,
                        config=IngestJobConfig(metadata=metadata)
                    ))
                    uploaded_count += 1

                except Exception as e:
                    print(f"   ❌ {text_file.name}: {str(e)}", flush=True)
                    skipped_count += 1

            if not uploaded_keys:
                print(f"   ❌ No files uploaded successfully for {surah_name}", flush=True)
                continue

            print(f"   ✅ Uploaded {uploaded_count} files ({skipped_count} failed)", flush=True)

            # Create batch ingest job for this surah
            try:
                batch_payload = BatchPayload(items=uploaded_keys)
                job = client.ingest_jobs.create(
                    payload=batch_payload,
                    name=f"{tafsir_name}-{surah_name}",
                    external_id=f"{tafsir_name}-{surah_name}",
                    config={   
                        "chunk_size": 4096,
                        "max_chunk_size": 4528,
                        "chunk_overlap": 256, 
                    }
                )
                job_id = job.data.id
                print(f"   ✅ Batch job created: {job_id}", flush=True)
            except Exception as e:
                print(f"   ❌ Failed to create batch job: {str(e)}", flush=True)
                continue

        print(f"\n🎉 All batches pushed to Agentset!", flush=True)

    def deduplicate_agentset(self, api_token: Optional[str] = None, namespace_id: Optional[str] = None, dry_run: bool = True, keep: str = "oldest") -> None:
        """Find and remove duplicate documents from Agentset.

        Args:
            api_token: Agentset API token (or set AGENTSET_API_TOKEN env var)
            namespace_id: Agentset namespace ID (or set AGENTSET_NAMESPACE_ID env var)
            dry_run: If True, only preview duplicates without deleting
            keep: Which duplicate to keep - 'oldest' or 'newest'
        """
        import os
        from dotenv import load_dotenv
        from collections import defaultdict

        load_dotenv()

        # Get credentials
        api_token = api_token or os.getenv("AGENTSET_API_TOKEN")
        namespace_id = namespace_id or os.getenv("AGENTSET_NAMESPACE_ID")

        if not api_token or not namespace_id:
            raise ValueError("AGENTSET_API_TOKEN and AGENTSET_NAMESPACE_ID must be set")

        # Initialize client
        from agentset import Agentset
        client = Agentset(token=api_token, namespace_id=namespace_id)

        print(f"\n📊 Fetching all documents from Agentset...", flush=True)

        # Fetch all documents with pagination
        all_docs = []
        cursor = None
        page = 1

        while True:
            print(f"   Fetching page {page}...", flush=True)
            response = client.documents.list(cursor=cursor, per_page=100)

            if not response or not response.result or not response.result.data:
                break

            all_docs.extend(response.result.data)

            # Check if there are more pages
            if not response.result.pagination.has_more:
                break

            cursor = response.result.pagination.next_cursor
            page += 1

        print(f"✅ Found {len(all_docs)} total documents", flush=True)

        # Group by name
        by_name = defaultdict(list)
        for doc in all_docs:
            name = doc.name if doc.name else "unnamed"
            by_name[name].append(doc)

        # Find duplicates
        duplicates = {name: docs for name, docs in by_name.items() if len(docs) > 1}

        if not duplicates:
            print(f"\n🎉 No duplicates found!", flush=True)
            return

        # Calculate statistics
        total_duplicate_count = sum(len(docs) - 1 for docs in duplicates.values())
        print(f"\n🔍 Found {len(duplicates)} unique files with duplicates", flush=True)
        print(f"   Total duplicate documents: {total_duplicate_count}", flush=True)

        # Preview or delete
        if dry_run:
            print(f"\n📋 DRY RUN - Preview of duplicates (keeping {keep}):\n", flush=True)

            for name, docs in sorted(duplicates.items()):
                # Sort by created_at
                docs_sorted = sorted(docs, key=lambda d: d.created_at)

                if keep == "oldest":
                    keep_doc = docs_sorted[0]
                    delete_docs = docs_sorted[1:]
                else:  # newest
                    keep_doc = docs_sorted[-1]
                    delete_docs = docs_sorted[:-1]

                print(f"📄 {name} ({len(docs)} copies)", flush=True)
                print(f"   ✓ KEEP: {keep_doc.id} (created: {keep_doc.created_at})", flush=True)
                for doc in delete_docs:
                    print(f"   ✗ DELETE: {doc.id} (created: {doc.created_at})", flush=True)
                print(flush=True)

            print(f"\n💡 To actually delete, run with --no-dry-run", flush=True)

        else:
            print(f"\n🗑️  Deleting duplicates (keeping {keep})...\n", flush=True)
            deleted_count = 0

            for name, docs in sorted(duplicates.items()):
                # Sort by created_at
                docs_sorted = sorted(docs, key=lambda d: d.created_at)

                if keep == "oldest":
                    keep_doc = docs_sorted[0]
                    delete_docs = docs_sorted[1:]
                else:  # newest
                    keep_doc = docs_sorted[-1]
                    delete_docs = docs_sorted[:-1]

                print(f"📄 {name} ({len(docs)} copies)", flush=True)
                print(f"   ✓ Keeping: {keep_doc.id}", flush=True)

                for doc in delete_docs:
                    try:
                        client.documents.delete(document_id=doc.id)
                        print(f"   ✗ Deleted: {doc.id}", flush=True)
                        deleted_count += 1
                    except Exception as e:
                        print(f"   ⚠️  Failed to delete {doc.id}: {e}", flush=True)

            print(f"\n✅ Deleted {deleted_count} duplicate documents", flush=True)