import requests
import os
import shutil
import bz2
import sqlite3
import logging as logging
from vectara.factory import Factory
from bs4 import BeautifulSoup   
CRP_ID = 'tafsirs'
import json



tafsirs = {
"qurtubi": "https://s3.us-east-1.wasabisys.com/static-cdn.tarteel.ai/qul-exports/tafsir/1722589836-w9ne3-ar-tafseer-al-qurtubi.db.bz2",
"ibn-kathir": "https://s3.us-east-1.wasabisys.com/static-cdn.tarteel.ai/qul-exports/tafsir/1722592431-won0o-en-tafisr-ibn-kathir.db.bz2",
}

# Initialize the client
lg = logging.getLogger("import_tafsir")
lg.setLevel(logging.INFO)
client = Factory(profile="lab").build()
manager = client.corpus_manager
for corpus in manager.find_corpora_with_filter():
    lg.info(f'Available corpus: {corpus}')

def split_html_by_tags(html):
    soup = BeautifulSoup(html, 'html.parser')
    split_elements = []
    for element in soup.recursiveChildGenerator():
        if element.name:  # It's a tag
            split_elements.append(str(element))
        elif element.string:  # It's a text node
            split_elements.append(element.string.strip())
    # Filter out empty strings
    split_elements = [element for element in split_elements if element]
    return split_elements


def download_tafsir(tafsir_name):
    """
    Download tafsir sqlite file from qul.tarteel.ai
    """

    # TODO(mwk): Check if downloads/ exist
    # TODO(mwk): Check if file already downloaded

    url = tafsirs.get(tafsir_name)
    if url:
        r = requests.get(url, stream=True)
        with open(f"downloads/{tafsir_name}.sqlite.bz2", "wb") as f:
            shutil.copyfileobj(r.raw, f)
        lg.info(f"downloads/{tafsir_name}.sqlite.bz2 downloaded")
        with bz2.open(f"downloads/{tafsir_name}.sqlite.bz2", "rb") as f:
            # Decompress data from file
            content = f.read()
            # Write decompressed data to file
            with open(f"downloads/{tafsir_name}.sqlite", "wb") as f:
                f.write(content)
            lg.info(f"downloads/{tafsir_name}.sqlite.bz2 decompressed")


def convert_to_vectara(tafsir_name):
    """
    Convert tafsir sqlite file to vectara format
    """
    # Open sqlite file
    conn = sqlite3.connect(f"downloads/{tafsir_name}.sqlite")
    cursor = conn.cursor()

    # Example SQLite call: Fetch all tables
    cursor.execute("SELECT ayah_key, group_ayah_key, from_ayah, to_ayah, ayah_keys, text from tafsir;")
    ayahs = cursor.fetchall()
    print(f"Ayahs in {tafsir_name}: {len(ayahs)}")
    v_ayahs = []
    core_doc = {
        "type": "core",
        "id": tafsir_name,
        "document_parts": v_ayahs
    }



    for ayah in ayahs:
        tags = split_html_by_tags(ayah[5])
        lg.info("Processing ayah: " + ayah[0])
        for tag in tags:
            #lg.info("Processing tag: " + tag)
            v_ayahs.append({
                "metadata": {
                    "ayah_key": ayah[0],
                    "group_ayah_key": ayah[1],
                    "from_ayah": ayah[2],
                    "to_ayah": ayah[3],
                    "ayah_keys": ayah[4],
                },
                "text": tag
            })

    lg.info(f'Total parts: {len(v_ayahs)}')
    json.dump(core_doc, open(f"downloads/{tafsir_name}.json", "w"), indent=4)
    client.documents.create(corpus_key=CRP_ID, request=core_doc, request_timeout = 900, request_options={"timeout": 900})




    # Close the connection
    conn.close()

# Example usage
download_tafsir("ibn-kathir")
convert_to_vectara("ibn-kathir")