#!/usr/bin/env python3
"""
CLI for Unified Document Injector
Process documents from Box folders using the unified document management system
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.document_injector_unified import UnifiedDocumentInjector


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Process legal documents from Box folders using unified document management"
    )

    parser.add_argument("--folder-id", required=True, help="Box folder ID to process")

    parser.add_argument(
        "--max-documents",
        type=int,
        help="Maximum number of documents to process (for testing)",
    )

    parser.add_argument(
        "--no-context", action="store_true", help="Skip context generation for chunks"
    )

    parser.add_argument("--no-facts", action="store_true", help="Skip fact extraction")

    parser.add_argument(
        "--no-cost-tracking", action="store_true", help="Disable API cost tracking"
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    parser.add_argument("--search", help="Search query to run after processing")

    parser.add_argument(
        "--test-connection", action="store_true", help="Test connections and exit"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Test connection if requested
    if args.test_connection:
        from src.document_injector_unified import test_unified_connection

        test_unified_connection()
        return

    try:
        # Initialize injector
        injector = UnifiedDocumentInjector(
            enable_cost_tracking=not args.no_cost_tracking,
            no_context=args.no_context,
            enable_fact_extraction=not args.no_facts,
        )

        # Process folder
        results = injector.process_case_folder(
            args.folder_id, max_documents=args.max_documents
        )

        # Print results summary
        print("\n" + "=" * 60)
        print("PROCESSING COMPLETE")
        print("=" * 60)

        successful = sum(1 for r in results if r.status == "success")
        duplicates = sum(1 for r in results if r.is_duplicate)
        failed = sum(1 for r in results if r.status == "failed")

        print(f"Total documents: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Duplicates: {duplicates}")
        print(f"Failed: {failed}")

        # Show document types processed
        doc_types = {}
        for r in results:
            if r.document_type:
                doc_types[r.document_type] = doc_types.get(r.document_type, 0) + 1

        if doc_types:
            print("\nDocument Types:")
            for doc_type, count in sorted(doc_types.items()):
                print(f"  {doc_type}: {count}")

        # Show failed documents
        failed_docs = [r for r in results if r.status == "failed"]
        if failed_docs:
            print("\nFailed Documents:")
            for doc in failed_docs:
                print(f"  - {doc.file_name}: {doc.error_message}")

        # Show cost report if tracking enabled
        if not args.no_cost_tracking:
            cost_report = injector.get_cost_report()
            if cost_report:
                print("\nCost Report:")
                print(f"  Total cost: ${cost_report.get('total_cost', 0):.4f}")
                print(
                    f"  Documents processed: {cost_report.get('documents_processed', 0)}"
                )

        # Run search if requested
        if args.search and results:
            print(f"\nSearching for: {args.search}")
            case_name = results[0].case_name

            search_results = injector.search_documents(
                case_name=case_name, query=args.search, limit=5
            )

            print(f"\nFound {len(search_results)} results:")
            for i, result in enumerate(search_results, 1):
                print(f"\n{i}. {result['title']} ({result['type']})")
                print(f"   Score: {result['score']:.3f}")
                print(f"   Summary: {result['summary'][:200]}...")
                if result["key_facts"]:
                    print(f"   Key Facts: {', '.join(result['key_facts'][:3])}")

    except Exception as e:
        logging.error(f"Error during processing: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
