# Ansari Indexing - Islamic Text Converters

A collection of converters for processing Islamic texts, with a focus on Fiqh cards and Tafsir data.

## Overview

This project provides tools for converting Islamic jurisprudence (fiqh) documents from DOCX format to structured JSON using Claude Opus 4.1 AI for intelligent extraction.

## Features

### Fiqh Card Converter
- **AI-Powered Extraction**: Uses Claude Opus 4.1 to intelligently parse complex Arabic fiqh texts
- **Structured JSON Output**: Converts unstructured DOCX tables into well-organized JSON
- **Handles Multiple Opinions**: Correctly separates and attributes different scholarly positions
- **Markdown Preview**: View how documents are converted before processing

## Installation

### Prerequisites
- Python 3.11 or higher
- UV package manager

### Setup

1. Clone the repository:
```bash
git clone [repository-url]
cd indexing
```

2. Install dependencies using UV:
```bash
uv sync
```

3. Set up environment variables:
Create a `.env` file in the project root with your Anthropic API key:
```env
ANTHROPIC_API_KEY=your-api-key-here
```

## Usage

### Fiqh Card Converter

The fiqh card converter uses Claude Opus 4.1 to extract structured information from Islamic jurisprudence documents.

#### Preview Markdown Conversion
To see how a DOCX file will be converted to markdown (without calling the API):
```bash
PYTHONPATH=src uv run python -m fiqh_card_converter.claude_cli preview
```

#### Test on Sample File
To test the converter on the sample file:
```bash
PYTHONPATH=src uv run python -m fiqh_card_converter.claude_cli test
```

This will:
- Process `sample_input_data/fiqh_cards/sample.docx`
- Save output to `sample_output_data/fiqh_cards/sample_claude.json`
- Display a summary of extracted issues

#### Convert All Files in Directory
To process all DOCX files in a directory:
```bash
PYTHONPATH=src uv run python -m fiqh_card_converter.claude_cli convert \
    sample_input_data/fiqh_cards \
    sample_output_data/fiqh_cards
```

### JSON Output Structure

The converter extracts the following information from each fiqh issue:

```json
{
  "issue_number": 1,
  "question": "The main fiqh question",
  "context": "Background and context of the disagreement",
  "opinions": [
    {
      "position": "The opinion/ruling",
      "scholars": ["Scholar1", "Scholar2"]
    }
  ],
  "disagreement_reason": "Why scholars disagree",
  "evidence": {
    "Evidence_1": "Quranic verses and hadiths",
    "Evidence_2": "Additional proofs"
  },
  "preferred_opinion": "The strongest opinion",
  "practical_impact": "Real-world implications",
  "references": "Source references"
}
```

## Project Structure

```
indexing/
├── src/
│   ├── fiqh_card_converter/
│   │   ├── __init__.py
│   │   ├── claude_converter.py  # Core converter using Claude AI
│   │   └── claude_cli.py        # Command-line interface
│   └── qul_tafsir/              # Tafsir converter (to be ported to Goodmem)
├── sample_input_data/
│   └── fiqh_cards/              # Sample DOCX files
├── sample_output_data/
│   └── fiqh_cards/              # Generated JSON output
├── .env                         # Environment variables (create this)
├── pyproject.toml               # Project configuration
└── README.md                    # This file
```

## How It Works

1. **Table Extraction**: Reads tables from DOCX files containing fiqh issues
2. **Markdown Conversion**: Converts table data to clean markdown format
3. **AI Processing**: Sends markdown to Claude Opus 4.1 with a structured prompt
4. **JSON Generation**: Claude extracts and returns structured JSON data
5. **Validation**: Ensures all required fields are present in the output

## API Requirements

This project requires an Anthropic API key with access to Claude Opus 4.1. The model used is:
- Model ID: `claude-opus-4-1-20250805`
- Max tokens: 16384
- Temperature: 0 (for consistent output)

## Development

### Adding New Features

The converter is designed to be extensible. To modify the extraction schema, edit the `FIQH_ISSUE_SCHEMA` in `claude_converter.py`.

### Testing

Always test changes using the preview command first to see the markdown conversion without consuming API credits:
```bash
PYTHONPATH=src uv run python -m fiqh_card_converter.claude_cli preview
```

## TODO

- Port qul_tafsir converter from Vectara to Goodmem
- Add batch processing with progress tracking
- Implement caching to avoid reprocessing files

## License

[Add license information here]

## Contact

[Add contact information here]