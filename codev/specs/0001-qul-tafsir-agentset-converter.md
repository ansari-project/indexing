# TICK Specification: Qul Tafsir Agentset Converter

## Metadata
- **ID**: 0001-qul-tafsir-agentset-converter
- **Protocol**: TICK
- **Created**: 2025-10-19
- **Status**: autonomous

## Task Description
Create an agentset converter for qul_tafsir that converts Ibn Kathir tafsir sections into individual files with metadata for ingestion into Agentset. Each tafsir section (covering a range of ayahs) should become a separate file with accompanying metadata.

## Scope

### In Scope
- Add `convert_to_agentset` method to TafsirConverter class
- Generate one file per tafsir section (group of ayahs)
- Create metadata.json for each section with ayah range and tafsir information
- Organize output files in structured directory (output/[tafsir-name]/sections/)
- Add CLI command for agentset conversion
- Write ingest function to process all generated files for Agentset

### Out of Scope
- Actual upload/ingestion to Agentset service (only file generation)
- Support for Qurtubi tafsir (focus on Ibn Kathir only)
- Migration of existing Vectara data
- Batch processing optimizations (handle sequentially)

## Success Criteria
- [ ] `convert_to_agentset` method creates one file per tafsir section
- [ ] Each section file contains the text content for that ayah range
- [ ] metadata.json files include: ayah_key, group_ayah_key, from_ayah, to_ayah, from_ayah_int, to_ayah_int, ayah_keys, tafsir_name
- [ ] Files organized in directory structure: output/[tafsir]/sections/[section-id].txt + metadata.json
- [ ] CLI command `convert-agentset` added with surah range parameters
- [ ] Ingest function stub created (for future implementation)
- [ ] Tests pass for file generation and metadata
- [ ] No breaking changes to existing Vectara conversion

## Constraints
- Must use existing SQLite database structure from qul_tafsir
- Follow fail-fast principles (no fallbacks)
- Use uv package manager (agentset already installed)
- Maintain existing TafsirConverter interface

## Assumptions
- SQLite database files already downloaded via existing download command
- Agentset SDK accepts directory of files with metadata
- Each section is self-contained (from_ayah to to_ayah range)
- Metadata format is flexible JSON

## Implementation Approach
Add a new method `convert_to_agentset` to the existing TafsirConverter class that:
1. Queries SQLite database for tafsir sections
2. Creates output directory structure
3. For each section, writes text content to a file
4. Generates corresponding metadata.json with ayah range info
5. Uses section ID as filename (e.g., section-001-ayah-1:1-to-1:7.txt)

### Key Changes
- `src/qul_tafsir/converter.py`: Add `convert_to_agentset` method
- `src/qul_tafsir/cli.py`: Add `convert-agentset` CLI command
- `src/qul_tafsir/converter.py`: Add `ingest_to_agentset` stub method for future use

## Risks
| Risk | Mitigation |
|------|------------|
| Metadata format incompatible with Agentset | Research Agentset docs, use flexible JSON structure |
| Large file count (1000s of sections) | Organize in subdirectories by surah |
| HTML content in text | Strip HTML tags, convert to plain text |

## Testing Approach
### Test Scenarios
1. Happy path: Convert single surah (Al-Fatihah) to agentset format
2. Edge case: Handle sections spanning multiple ayahs (from_ayah != to_ayah)
3. Error scenario: Handle missing/corrupt SQLite database gracefully
4. Verify metadata.json contains all required fields
5. Verify file naming convention is consistent

## Notes
- This replaces the Vectara conversion for new agentset-based architecture
- Future work: Implement actual Agentset SDK ingestion in ingest_to_agentset method
- Consider adding progress bar for batch conversions
