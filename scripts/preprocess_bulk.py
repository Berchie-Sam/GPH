"""
Batch Hansard Preprocessing

Process all downloaded Hansard text files through the parsing,
validation, and enrichment pipeline.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional
import json
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from preprocessing import (
    HansardParser,
    validate_hansard,
    enrich_hansard,
    print_enrichment_report,
    build_reference_offline,
)


def process_single_hansard(
    txt_path: Path,
    output_dir: Path,
    ref_path: Optional[Path] = None,
    validate: bool = True,
    enrich: bool = True,
) -> dict:
    """
    Process a single Hansard text file through full pipeline.
    
    Args:
        txt_path: Path to extracted text file
        output_dir: Directory for output files
        ref_path: Path to MP reference CSV (optional)
        validate: Run validation suite
        enrich: Enrich with MP data
        
    Returns:
        Processing summary dict
    """
    print(f"\nProcessing: {txt_path.name}")
    
    result = {
        "file": txt_path.name,
        "status": "started",
        "rows": 0,
        "validation": {},
        "enrichment": {},
    }
    
    try:
        # Step 1: Parse
        print("  Parsing...")
        parser = HansardParser(str(txt_path))
        
        parsed_path = output_dir / txt_path.name.replace(".txt", "_parsed.csv")
        parser.to_csv(str(parsed_path))
        
        result["rows"] = len(parser.statements)
        result["speakers"] = len(set(
            s.name for s in parser.statements 
            if not s.is_stage_direction
        ))
        print(f"    ✓ {result['rows']} rows, {result['speakers']} speakers")
        
        # Step 2: Validate
        if validate:
            print("  Validating...")
            from preprocessing.validator import (
                print_report, write_fix_report, load_csv, save_csv
            )
            
            results = validate_hansard(str(parsed_path), str(txt_path), apply_fix=True)
            print_report(results, str(parsed_path), str(txt_path), apply_fix=True)
            
            # Save fixed version
            fixed_path = output_dir / txt_path.name.replace(".txt", "_validated.csv")
            rows = load_csv(str(parsed_path))
            save_csv(rows, str(fixed_path))
            
            # Count failures/warnings
            failures = sum(1 for r in results if r.status == "FAIL")
            warnings = sum(1 for r in results if r.status == "WARN")
            result["validation"] = {
                "failures": failures,
                "warnings": warnings,
                "passed": len(results) - failures - warnings,
            }
            print(f"    ✓ Validation: {failures} failures, {warnings} warnings")
            
            csv_to_enrich = fixed_path
        else:
            csv_to_enrich = parsed_path
        
        # Step 3: Enrich
        if enrich and ref_path and ref_path.exists():
            print("  Enriching...")
            enriched, report, out_csv = enrich_hansard(
                str(csv_to_enrich),
                str(ref_path),
                str(output_dir / txt_path.name.replace(".txt", "_enriched.csv"))
            )
            
            result["enrichment"] = {
                "matched": report["matched"],
                "total_speakers": report["speaker_rows"],
                "rate": report["matched"] / report["speaker_rows"] if report["speaker_rows"] > 0 else 0,
            }
            print(f"    ✓ Enrichment: {result['enrichment']['matched']}/{result['enrichment']['total_speakers']} matched")
        
        result["status"] = "success"
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"    ✗ ERROR: {e}")
    
    return result


def batch_process(
    input_dir: Path,
    output_dir: Path,
    ref_path: Optional[Path] = None,
    pattern: str = "*.txt",
    validate: bool = True,
    enrich: bool = True,
) -> List[dict]:
    """
    Process all Hansard text files in directory.
    
    Args:
        input_dir: Directory with .txt files
        output_dir: Directory for output CSVs
        ref_path: Path to MP reference CSV
        pattern: File pattern to match
        validate: Run validation
        enrich: Run enrichment
        
    Returns:
        List of processing summaries
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all text files
    txt_files = sorted(input_dir.glob(pattern))
    print(f"Found {len(txt_files)} text files to process")
    
    if not txt_files:
        print("No files found!")
        return []
    
    # Process each
    results = []
    for i, txt_path in enumerate(txt_files, 1):
        print(f"\n[{i}/{len(txt_files)}] ", end="")
        result = process_single_hansard(
            txt_path, output_dir, ref_path, validate, enrich
        )
        results.append(result)
    
    return results


def print_summary_report(results: List[dict], output_path: Path):
    """Print and save batch processing summary."""
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    errors = sum(1 for r in results if r["status"] == "error")
    
    total_rows = sum(r.get("rows", 0) for r in results)
    total_speakers = sum(r.get("speakers", 0) for r in results)
    
    avg_enrichment = 0
    enrichment_rates = [r["enrichment"].get("rate", 0) for r in results if r.get("enrichment")]
    if enrichment_rates:
        avg_enrichment = sum(enrichment_rates) / len(enrichment_rates)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_files": total,
            "successful": success,
            "errors": errors,
            "total_rows": total_rows,
            "total_speakers": total_speakers,
            "avg_enrichment_rate": avg_enrichment,
        },
        "files": results,
    }
    
    # Print summary
    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)
    print(f"  Total files:    {total}")
    print(f"  Successful:     {success}")
    print(f"  Errors:         {errors}")
    print(f"  Total rows:     {total_rows:,}")
    print(f"  Total speakers: {total_speakers:,}")
    if avg_enrichment > 0:
        print(f"  Avg enrichment: {avg_enrichment:.1%}")
    print("=" * 60)
    
    # Save JSON report
    report_path = output_path / "_processing_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved → {report_path}")
    
    # Save CSV summary
    csv_path = output_path / "_processing_summary.csv"
    with open(csv_path, "w", newline="") as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=["file", "status", "rows", "speakers"])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "file": r["file"],
                "status": r["status"],
                "rows": r.get("rows", 0),
                "speakers": r.get("speakers", 0),
            })
    print(f"Summary saved → {csv_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch preprocess Hansard text files"
    )
    parser.add_argument(
        "--input-dir",
        default="data/hansards/txt",
        help="Input directory with .txt files",
    )
    parser.add_argument(
        "--output-dir",
        default="data/hansards/processed",
        help="Output directory for CSVs",
    )
    parser.add_argument(
        "--ref",
        default=None,
        help="Path to MP reference CSV (optional)",
    )
    parser.add_argument(
        "--pattern",
        default="*.txt",
        help="File pattern to match (default: *.txt)",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip validation",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip enrichment",
    )
    parser.add_argument(
        "--build-ref",
        action="store_true",
        help="Build MP reference first (offline mode)",
    )
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    # Build reference if requested
    ref_path = None
    if args.build_ref:
        print("Building offline MP reference...")
        ref_path = output_dir / "ghana_mps_9th_parliament.csv"
        records = build_reference_offline()
        import csv
        with open(ref_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
        print(f"Reference saved → {ref_path}")
    elif args.ref:
        ref_path = Path(args.ref)
    
    # Run batch processing
    results = batch_process(
        input_dir=input_dir,
        output_dir=output_dir,
        ref_path=ref_path,
        pattern=args.pattern,
        validate=not args.no_validate,
        enrich=not args.no_enrich,
    )
    
    # Print summary
    print_summary_report(results, output_dir)
    
    print("\nDone!")


if __name__ == "__main__":
    main()
