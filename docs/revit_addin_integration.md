# Revit Add-in Integration Guide

## 1) Integration Overview

Target runtime flow:

1. Revit add-in extracts BIM elements (rooms/spaces).
2. Add-in POSTs to backend endpoint `/integration/revit/check`.
3. Backend runs:
   - RAG retrieval over code document
   - LLM structured rule extraction
   - deterministic rule engine checks
4. Backend returns findings + visualization IDs.
5. Add-in highlights failed/passed elements and shows summary.

## 2) Backend Endpoint for Add-in

Primary endpoint:
- `POST /integration/revit/check`

Alias behavior:
- This endpoint maps to full flow endpoint `/agent/full-check`.

## 3) Request Contract

```json
{
  "elements": [
    {
      "id": "101",
      "name": "Bedroom 1",
      "category": "room",
      "level": "L1",
      "area": 8.5,
      "height": 2.7,
      "width": null
    }
  ],
  "question": "What is the minimum bedroom area requirement?",
  "code_file": "data/2015_International_Building_Code-238-323.pdf",
  "top_k": 6,
  "model": "qwen2.5:7b",
  "base_url": "http://localhost:11434",
  "embedding_model": "nomic-embed-text-v2-moe:latest",
  "embedding_base_url": "http://localhost:11434"
}
```

Required fields:
- `elements`
- `question`
- `code_file`

Recommended element properties:
- `id`, `name`, `category`, `level`, `area`, `height`, `width`

## 4) Response Contract

```json
{
  "status": "ok",
  "phase": "full-integration",
  "question": "...",
  "rules": [
    {
      "element": "room",
      "property": "area",
      "operator": ">=",
      "value": 9.0,
      "unit": "m2",
      "source_excerpt": "..."
    }
  ],
  "retrieval_hits": [
    {
      "rank": 1,
      "content": "...",
      "metadata": {"chunk_index": 12, "distance": 0.45}
    }
  ],
  "answer": "...",
  "engine": {
    "summary": {
      "total_elements": 2,
      "total_rules": 1,
      "pass_count": 1,
      "fail_count": 1,
      "manual_review_count": 0
    },
    "findings": [
      {
        "element_id": "101",
        "element_name": "Bedroom 1",
        "status": "fail",
        "reason": "Checked area >= 9.0 (8.5).",
        "actual_value": 8.5,
        "rule": {"property": "area", "operator": ">=", "value": 9.0}
      }
    ],
    "visualization": {
      "failed_ids": ["101"],
      "passed_ids": ["102"],
      "palette": {
        "fail": "#D32F2F",
        "pass": "#2E7D32",
        "manual": "#F9A825"
      }
    }
  }
}
```

## 5) C# Add-in Mapping Notes

- `failed_ids` -> select/highlight in red
- `passed_ids` -> select/highlight in green
- use `engine.findings` for issue list UI
- show `answer` and `rules` in details panel

## 6) Minimal C# HTTP Call Pattern

Pseudo-flow in C# (ExternalCommand):

1. Collect rooms with `FilteredElementCollector`.
2. Convert internal area units to your chosen unit system.
3. Serialize payload JSON.
4. Send with `HttpClient.PostAsync`.
5. Parse JSON response.
6. Apply element overrides by IDs from `failed_ids` / `passed_ids`.

## 7) Revit Add-in Requirements

- Revit API access in transaction-safe context
- Read access to room/space parameters
- UI support for listing findings (TaskDialog or WPF)
- Color override helpers for categories/elements
- Mapping strategy from backend string IDs -> Revit ElementId

## 8) Backend Runtime Requirements

- Python virtual environment with `requirements.txt`
- Running FastAPI service
- Running Ollama service and installed models
- Accessible code document path in backend workspace

## 9) Recommended UX in Revit

- Summary badge: pass/fail/manual counts
- Issue table: element name, check, reason, recommendation
- Click issue -> zoom/select element
- Optional "Why failed?" explanation dialog using `answer` + `source_excerpt`
