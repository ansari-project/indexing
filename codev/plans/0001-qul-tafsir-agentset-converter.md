# TICK Plan: Qul Tafsir Agentset Converter

## Metadata
- **ID**: 0001-qul-tafsir-agentset-converter
- **Protocol**: TICK
- **Specification**: [codev/specs/0001-qul-tafsir-agentset-converter.md](../specs/0001-qul-tafsir-agentset-converter.md)
- **Created**: 2025-10-19
- **Status**: autonomous

## Implementation Approach
Add a `convert_to_agentset` method to TafsirConverter that processes the SQLite database and generates individual text files with metadata for each tafsir section. Each section represents a commentary on a range of ayahs, and will be stored as a separate file with accompanying metadata.json.

## Implementation Steps

### Step 1: Add convert_to_agentset method
**Files**: `src/qul_tafsir/converter.py`
**Changes**:
- Add `convert_to_agentset` method that accepts tafsir_name and surah_range parameters
- Query SQLite database for tafsir sections
- Create output directory structure: `output/{tafsir_name}/sections/surah-{###}/`
- Strip HTML tags from text content using BeautifulSoup
- For each section, write text file and metadata.json

### Step 2: Implement metadata generation
**Files**: `src/qul_tafsir/converter.py`
**Changes**:
- Create helper method `_generate_section_metadata` to build metadata dict
- Include fields: ayah_key, group_ayah_key, from_ayah, to_ayah, from_ayah_int, to_ayah_int, ayah_keys, tafsir_name, surah
- Use descriptive filename pattern: `section-{group_ayah_key}.txt`
- Write metadata to `section-{group_ayah_key}.metadata.json` in same directory

### Step 3: Add ingest_to_agentset stub method
**Files**: `src/qul_tafsir/converter.py`
**Changes**:
- Add `ingest_to_agentset` method with parameters: tafsir_name, output_dir
- Method should iterate through all generated files
- For now, just log the files that would be ingested (stub implementation)
- Add TODO comment for future Agentset SDK integration

### Step 4: Add CLI command
**Files**: `src/qul_tafsir/cli.py`
**Changes**:
- Add `convert_agentset` command using @app.command() decorator
- Accept tafsir_name, start_surah, end_surah parameters
- Call converter.convert_to_agentset method
- Display progress using rich console output

### Step 5: Add ingest CLI command
**Files**: `src/qul_tafsir/cli.py`
**Changes**:
- Add `ingest_agentset` command for future use
- Accept tafsir_name and optional output_dir parameters
- Call converter.ingest_to_agentset method
- Display summary of files to be ingested

## Files to Create/Modify

### New Files
None (all changes to existing files)

### Modified Files
- `src/qul_tafsir/converter.py` - Add convert_to_agentset, _generate_section_metadata, ingest_to_agentset methods
- `src/qul_tafsir/cli.py` - Add convert_agentset and ingest_agentset CLI commands

## Testing Strategy

### Manual Testing
1. Download Ibn Kathir database: `PYTHONPATH=src python -m qul_tafsir.cli download ibn-kathir`
2. Convert single surah: `PYTHONPATH=src python -m qul_tafsir.cli convert-agentset ibn-kathir --start-surah 1 --end-surah 2`
3. Verify output directory structure exists: `output/ibn-kathir/sections/surah-001/`
4. Check that files are created with correct naming pattern
5. Verify metadata.json files contain all required fields
6. Test ingest command lists files correctly

### Automated Tests (if applicable)
- Not adding automated tests for this TICK task (< 300 lines)
- Manual verification sufficient for initial implementation

## Success Criteria
- [ ] convert_to_agentset method creates files for each section
- [ ] Metadata files include all required fields
- [ ] HTML tags stripped from text content
- [ ] CLI commands work with surah range parameters
- [ ] Directory structure follows pattern: output/{tafsir}/sections/surah-{###}/
- [ ] Ingest stub method logs files correctly
- [ ] Manual tests pass
- [ ] No breaking changes to existing code

## Risks
| Risk | If Occurs |
|------|-----------|
| HTML parsing fails | Use BeautifulSoup .get_text() with proper error handling |
| Too many files in one directory | Organize by surah subdirectories |
| Metadata format changes | Use flexible dict structure, easy to update |

## Dependencies
- agentset SDK (already installed via uv)
- Existing SQLite databases from qul_tafsir
- BeautifulSoup4 (already available in python-docx dependencies)

## Notes
- Focus on Ibn Kathir only for this iteration
- Agentset ingestion will be implemented in future task
- Keep file structure simple and flat within surah directories
- Use group_ayah_key as unique identifier for sections
