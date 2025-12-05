# Entity CSV Export Guide

## Overview

Export your cleaned and validated metadata entities to CSV format for analysis in Excel, Google Sheets, or other tools.

---

## Quick Start

### Method 1: Command Line (Easiest)

```bash
# Export all entities
python scripts/export_entities_csv.py

# Export only people
python scripts/export_entities_csv.py --type people --output people.csv

# Export with document IDs
python scripts/export_entities_csv.py --type people --with-documents --output people_docs.csv

# Export frequently mentioned entities (5+ mentions)
python scripts/export_entities_csv.py --type people --min-freq 5 --output frequent_people.csv

# Comprehensive export (all formats)
python scripts/export_entities_csv.py --comprehensive --output-dir exports
```

### Method 2: Python API

```python
from src.export_entities import export_entities_to_csv, export_all_entities

# Simple export
export_entities_to_csv('exports/entities.csv', entity_type='all')

# Comprehensive export
exports = export_all_entities(output_dir='exports')
```

---

## Export Formats

### 1. **Entities with Frequencies**

Shows each entity and how many documents it appears in.

**Columns:** Entity Type, Entity, Document Count

```csv
Entity Type,Entity,Document Count
people,Jeffrey Epstein,45
people,Ghislaine Maxwell,32
locations,Paris,28
organizations,Clinton Foundation,23
```

**Command:**
```bash
python scripts/export_entities_csv.py --output entities_frequencies.csv
```

**Python:**
```python
from src.metadata_store import MetadataStore
from src.export_entities import EntityCSVExporter

store = MetadataStore("data/metadata.db")
exporter = EntityCSVExporter(store)
exporter.export_entities_with_frequencies('output.csv', entity_type='all')
store.close()
```

---

### 2. **Entities with Document IDs**

Shows which specific documents each entity appears in.

**Columns:** Entity, Document Count, Document IDs

```csv
Entity,Document Count,Document IDs
Jeffrey Epstein,45,"doc_001; doc_003; doc_007; ..."
Ghislaine Maxwell,32,"doc_001; doc_005; doc_012; ..."
```

**Command:**
```bash
python scripts/export_entities_csv.py --type people --with-documents --output people_docs.csv
```

**Python:**
```python
exporter.export_entities_with_documents(
    'output.csv',
    entity_type='people',
    limit=100  # Top 100 most frequent
)
```

---

### 3. **Document Metadata**

Shows all entities for each document.

**Columns:** Document ID, Word Count, People, Organizations, Locations, Dates, Emails, [Counts]

```csv
Document ID,Word Count,People,Organizations,Locations,Dates,Emails,People Count,Organizations Count,...
doc_001,1500,"Jeffrey Epstein; Ghislaine Maxwell","Clinton Foundation","Paris; New York","2015-07-12",,2,1,...
```

**Command:**
```bash
python scripts/export_entities_csv.py --type all --output documents.csv
# Note: This requires using document metadata export (see comprehensive export)
```

**Python:**
```python
exporter.export_document_metadata('output.csv')
```

---

### 4. **Co-occurrence Matrix**

Shows which entities appear together in documents.

**Format:** Matrix with entities as both rows and columns, values are co-occurrence counts.

```csv
Entity,Jeffrey Epstein,Ghislaine Maxwell,Bill Clinton
Jeffrey Epstein,0,28,15
Ghislaine Maxwell,28,0,12
Bill Clinton,15,12,0
```

**Command:**
```bash
python scripts/export_entities_csv.py --matrix --type people --top 50 --output cooccurrence.csv
```

**Python:**
```python
exporter.export_entity_matrix(
    'output.csv',
    entity_type='people',
    top_n=50
)
```

---

### 5. **Comprehensive Export**

Exports all formats at once:
- All entities with frequencies
- People with documents
- Organizations with documents
- Locations with documents
- Document metadata
- People co-occurrence matrix

**Command:**
```bash
python scripts/export_entities_csv.py --comprehensive --output-dir exports
```

**Python:**
```python
from src.export_entities import export_all_entities

exports = export_all_entities(output_dir='exports')
# Returns: {'all_frequencies': 'exports/all_entities_frequencies.csv', ...}
```

---

## Command-Line Options

```bash
python scripts/export_entities_csv.py [OPTIONS]

Options:
  --type, -t          Entity type (all, people, organizations, locations, dates, emails)
  --output, -o        Output CSV file path
  --output-dir, -d    Output directory for comprehensive export
  --min-freq, -m      Minimum document frequency to include
  --limit, -l         Limit number of entities to export
  --with-documents    Include list of document IDs for each entity
  --matrix            Export co-occurrence matrix
  --top               For matrix, number of top entities to include
  --comprehensive     Export all entities in multiple formats
  --db                Path to metadata database
  --help             Show help message
```

---

## Common Use Cases

### 1. Find Most Mentioned People

```bash
python scripts/export_entities_csv.py \
  --type people \
  --output top_people.csv
```

Open in Excel, sort by "Document Count" column (descending).

### 2. People Mentioned 10+ Times

```bash
python scripts/export_entities_csv.py \
  --type people \
  --min-freq 10 \
  --output frequent_people.csv
```

### 3. See Which Documents Mention "Jeffrey Epstein"

Export with documents, then search in Excel:

```bash
python scripts/export_entities_csv.py \
  --type people \
  --with-documents \
  --output people_docs.csv
```

Open in Excel, filter for "Jeffrey Epstein" in Entity column.

### 4. Find People Who Appear Together

```bash
python scripts/export_entities_csv.py \
  --matrix \
  --type people \
  --top 100 \
  --output people_network.csv
```

Use for network analysis or import into graph visualization tools.

### 5. Export All for Analysis

```bash
python scripts/export_entities_csv.py --comprehensive --output-dir my_analysis
```

Creates 6 different CSV files for comprehensive analysis.

---

## Python API Examples

### Example 1: Basic Export

```python
from src.export_entities import export_entities_to_csv

# One-liner
export_entities_to_csv('output.csv', entity_type='people', min_frequency=5)
```

### Example 2: Multiple Exports

```python
from src.metadata_store import MetadataStore
from src.export_entities import EntityCSVExporter

store = MetadataStore("data/metadata.db")
exporter = EntityCSVExporter(store)

# Export people
exporter.export_entities_with_frequencies('people.csv', entity_type='people')

# Export locations
exporter.export_entities_with_frequencies('locations.csv', entity_type='locations')

# Export people with documents
exporter.export_entities_with_documents('people_docs.csv', entity_type='people')

store.close()
```

### Example 3: Custom Analysis

```python
from src.metadata_store import MetadataStore
from src.metadata_tags import MetadataTagsRetriever
import csv

store = MetadataStore("data/metadata.db")
retriever = MetadataTagsRetriever(store)

# Get frequencies
frequencies = retriever.get_tag_frequencies('people')

# Filter and export custom subset
with open('custom_export.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Person', 'Mentions', 'Category'])
    
    for person, count in frequencies['people'].items():
        # Custom logic
        category = 'High' if count >= 10 else 'Medium' if count >= 5 else 'Low'
        writer.writerow([person, count, category])

store.close()
```

---

## Output Locations

By default, files are saved to `exports/` directory:

```
exports/
├── entities.csv                          # Default output
├── all_entities_frequencies.csv          # Comprehensive export
├── people_with_documents.csv
├── organizations_with_documents.csv
├── locations_with_documents.csv
├── document_metadata.csv
└── people_cooccurrence_matrix.csv
```

---

## Analyzing in Excel/Google Sheets

### Excel Tips

1. **Sort by Frequency**
   - Click any cell in "Document Count" column
   - Data → Sort → Largest to Smallest

2. **Filter by Entity Type**
   - Click any cell in "Entity Type" column
   - Data → Filter → Select types to show

3. **Search for Specific Entity**
   - Ctrl+F → Type entity name
   - Or use Data → Filter

4. **Pivot Table Analysis**
   - Select data → Insert → Pivot Table
   - Analyze frequency distributions

### Google Sheets Tips

1. **Import CSV**
   - File → Import → Upload
   - Select "Comma" as separator

2. **Create Charts**
   - Select data
   - Insert → Chart
   - Visualization of top entities

---

## Performance

- **Small corpus** (<100 docs): All exports < 1 second
- **Medium corpus** (100-1000 docs): Exports in 1-5 seconds
- **Large corpus** (1000+ docs): Exports in 5-30 seconds
- **Co-occurrence matrix**: Slower for large N (top_n > 100)

---

## Troubleshooting

### Error: "No such file: data/metadata.db"

**Solution:** Build the metadata index first:
```bash
python build_metadata_index.py
```

### Empty CSV File

**Solution:** Check if entities exist:
```bash
python scripts/list_metadata_tags.py --stats
```

### Large File Size

**Solution:** Use filters:
```bash
# Only entities mentioned 5+ times
python scripts/export_entities_csv.py --min-freq 5 --output filtered.csv
```

### Memory Issues with Large Matrices

**Solution:** Reduce matrix size:
```bash
# Top 50 instead of 100
python scripts/export_entities_csv.py --matrix --top 50 --output matrix.csv
```

---

## Integration with Other Tools

### Import into Python/Pandas

```python
import pandas as pd

# Load exported CSV
df = pd.read_csv('exports/people.csv')

# Analyze
print(df.head())
print(df.describe())
print(df[df['Document Count'] >= 10])
```

### Import into R

```r
# Load CSV
data <- read.csv('exports/people.csv')

# Analyze
summary(data)
subset(data, Document.Count >= 10)
```

### Import into SQL

```sql
-- Import CSV into SQLite
.mode csv
.import exports/people.csv people_export
```

---

## Files Created

1. **`src/export_entities.py`** - Core export API (450+ lines)
2. **`scripts/export_entities_csv.py`** - Command-line tool (180+ lines)
3. **`examples/export_entities_example.py`** - Working examples (250+ lines)
4. **`ENTITY_CSV_EXPORT_GUIDE.md`** - This guide

---

## Next Steps

1. **Try it:** Run `python examples/export_entities_example.py`
2. **Export your data:** Run `python scripts/export_entities_csv.py --comprehensive`
3. **Analyze:** Open the CSV files in Excel/Google Sheets
4. **Custom exports:** Use the Python API for specific needs

---

**Date:** November 23, 2025  
**Status:** Production Ready

