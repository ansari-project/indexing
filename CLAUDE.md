# Project-Specific Instructions for Ansari Indexing

## Project Overview
This repository contains converters for Islamic text data, specifically:
1. **Fiqh Card Converter** - Converts DOCX files containing Islamic jurisprudence issues to structured JSON using Claude Opus 4.1
2. **Qul Tafsir Converter** - (To be ported from Vectara to Goodmem)

## Architecture Decisions

### Claude AI Integration
- Uses Claude Opus 4.1 (`claude-opus-4-1-20250805`) for intelligent text extraction
- Converts tables to markdown first for better AI comprehension
- Prefills assistant response with `{` to ensure JSON output
- Uses temperature=0 for consistent, deterministic results

### Data Processing Pipeline
1. Extract tables from DOCX files
2. Convert to clean markdown format
3. Send to Claude with structured schema
4. Parse and validate JSON response

## Code Standards

### Python Patterns
- Use `uv run python` to run modules (automatically handles environment and dependencies)
- All converters should be under `src/` directory
- Use python-dotenv for environment variables
- Follow modular design with separate converter and CLI files

### Error Handling
- Fail fast - don't implement fallbacks
- Log errors clearly with context
- Skip problematic tables/files but continue processing others

### API Key Management
- Always use `.env` file for API keys
- Never commit API keys to repository
- Support both environment variable and CLI parameter for API key

## JSON Schema Design

The fiqh converter uses a lightweight JSON schema (not Pydantic) defined directly in the converter. This approach:
- Reduces dependencies
- Makes the schema visible in the prompt to Claude
- Allows easy modification without changing models

## Testing Strategy

1. **Preview Mode**: Test markdown conversion without API calls
2. **Sample Testing**: Use provided sample files before batch processing
3. **API Conservation**: Use preview to verify structure before consuming API credits

## File Organization

```
src/
├── fiqh_card_converter/
│   ├── claude_converter.py  # Core logic
│   └── claude_cli.py        # CLI interface
└── qul_tafsir/              # To be ported
```

## Git Workflow
- Use descriptive commits focused on converter functionality
- Don't commit generated output files unless they're examples
- Keep sample data minimal but representative

## CLI Design Principles

Each converter should have:
- `preview` - Show intermediate format without API calls
- `test` - Process sample file with full pipeline
- `convert` - Batch process directory

## Future Improvements

### Priority
1. Port qul_tafsir to Goodmem
2. Add caching layer to avoid reprocessing
3. Implement progress bars for batch processing

### Consider
- Streaming API responses for large batches
- Parallel processing with rate limiting
- Output format options (JSON, CSV, etc.)

## Dependencies to Maintain
- `anthropic` - For Claude API access
- `python-docx` - For DOCX parsing
- `typer` - For CLI
- `rich` - For terminal output
- `python-dotenv` - For environment variables

## Important Notes

- The project uses UV as the package manager
- Python 3.11+ is required
- Always test with sample data first
- Monitor API usage to avoid unexpected costs

## Codev Methodology

This project uses the Codev context-driven development methodology.

### Active Protocol
- Protocol: SPIDER (with multi-agent consultation via Zen MCP)
- Location: `codev/protocols/spider/protocol.md`

### Directory Structure
- Specifications: `codev/specs/`
- Plans: `codev/plans/`
- Reviews: `codev/reviews/`
- Resources: `codev/resources/`

### Development Flow
For new features or significant changes, follow the SPIDER protocol:
- **S**pecify - Define what to build in clear, unambiguous language
- **P**lan - Break specifications into executable phases
- **For each phase:** **I**mplement → **D**efend → **E**valuate
  - **Implement**: Build the code to meet phase objectives
  - **Defend**: Write comprehensive tests that protect your code
  - **Evaluate**: Verify requirements are met, get user approval, then commit
- **R**eview - Capture lessons and improve the methodology

### Multi-Agent Consultation
When using SPIDER protocol, consult external AI models (GPT-5, Gemini Pro) via Zen MCP for:
- Specification reviews
- Plan reviews
- Implementation phase reviews

### Document Naming Convention
Use `####-descriptive-name.md` format for all specs, plans, and reviews (e.g., `0001-fiqh-card-converter.md`)

### Git Integration with SPIDER
- Each stage gets one pull request
- Phases can have multiple commits within the PR
- User approval required before creating PRs

See `codev/protocols/spider/protocol.md` for full protocol details.