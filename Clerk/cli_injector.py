#!/usr/bin/env python3
"""
CLI Document Injector for Clerk Legal AI System
Processes documents from Box folders into vector databases.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.document_injector import DocumentInjector
from src.utils.logger import setup_logging
from config.settings import settings


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Inject legal documents from Box into vector databases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single folder
  %(prog)s --folder-id 123456789
  
  # Process with document limit
  %(prog)s --folder-id 123456789 --max-documents 10
  
  # Process all case folders from root
  %(prog)s --root 987654321 --max-folders 5
  
  # Enable debug logging
  %(prog)s --folder-id 123456789 --log-level DEBUG
        """
    )
    
    # Mutually exclusive group for folder-id vs root
    folder_group = parser.add_mutually_exclusive_group(required=False)
    folder_group.add_argument(
        '--folder-id',
        type=str,
        help='Box folder ID to process as a single case'
    )
    folder_group.add_argument(
        '--root',
        type=str,
        help='Root folder ID containing multiple case folders'
    )
    
    # Processing limits
    parser.add_argument(
        '--max-documents',
        type=int,
        default=None,
        help='Maximum number of documents to process (excludes duplicates)'
    )
    parser.add_argument(
        '--max-folders',
        type=int,
        default=None,
        help='Maximum number of case folders to process (only with --root)'
    )
    
    # Options
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be processed without actually processing'
    )
    parser.add_argument(
        '--skip-cost-tracking',
        action='store_true',
        help='Disable API cost tracking'
    )
    parser.add_argument(
        '--save-cost-report',
        action='store_true',
        help='Save cost report after processing'
    )
    parser.add_argument(
        '--no-context',
        action='store_true',
        help='Skip context generation for chunks'
    )
    
    # Fact extraction options
    parser.add_argument(
        '--skip-facts',
        action='store_true',
        help='Skip fact, deposition, and exhibit extraction'
    )
    parser.add_argument(
        '--generate-timeline',
        action='store_true',
        help='Generate timeline after processing documents'
    )
    parser.add_argument(
        '--init-shared-knowledge',
        action='store_true',
        help='Initialize Florida statutes and FMCSR databases (run once)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.max_folders and not args.root:
        parser.error("--max-folders can only be used with --root")
    
    # Ensure either init-shared-knowledge OR folder processing is requested
    if not args.init_shared_knowledge and not args.folder_id and not args.root:
        parser.error("Either --init-shared-knowledge OR one of --folder-id/--root is required")
    
    return args


def process_single_folder(injector: DocumentInjector, folder_id: str,
                       max_documents: Optional[int] = None,
                       generate_timeline: bool = False) -> dict:
    try:
        # Process the folder
        results = injector.process_case_folder(
            folder_id=folder_id,
            max_documents=max_documents
        )
        
        # Summary
        success_count = sum(1 for r in results if r.status == "success")
        duplicate_count = sum(1 for r in results if r.status == "duplicate")
        failed_count = sum(1 for r in results if r.status == "error")
        
        logger = logging.getLogger(__name__)
        logger.info(f"Folder {folder_id} processing complete: "
                   f"{success_count} processed, "
                   f"{duplicate_count} duplicates, "
                   f"{failed_count} failed")
        
        # Generate timeline if requested
        if generate_timeline and success_count > 0:
            # Get case name from the first successful result
            case_name = None
            for r in results:
                if r.status == "success":
                    case_name = r.case_name
                    break
            
            if case_name:
                try:
                    logger.info(f"Generating timeline for case {case_name}...")
                    from src.utils.timeline_generator import TimelineGenerator
                    import asyncio
                    
                    timeline_gen = TimelineGenerator(case_name)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    timeline = loop.run_until_complete(timeline_gen.generate_timeline())
                    narrative = timeline_gen.generate_narrative_timeline(timeline, format="markdown")
                    
                    # Save timeline
                    timeline_path = f"timelines/{case_name}_timeline.md"
                    import os
                    os.makedirs("timelines", exist_ok=True)
                    
                    with open(timeline_path, 'w', encoding='utf-8') as f:
                        f.write(narrative)
                    
                    logger.info(f"Timeline saved to {timeline_path}")
                    loop.close()
                except Exception as e:
                    logger.error(f"Failed to generate timeline: {e}")
        
        return {
            "status": "complete",
            "folder_id": folder_id,
            "success": success_count,
            "duplicates": duplicate_count,
            "failed": failed_count
        }
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error processing folder {folder_id}: {str(e)}")
        return {"status": "error", "folder_id": folder_id, "error": str(e)}


def process_root_folder(injector: DocumentInjector, root_id: str,
                       max_folders: Optional[int] = None,
                       max_documents: Optional[int] = None,
                       dry_run: bool = False,
                       generate_timeline: bool = False) -> dict:
    """Process a root folder by processing each case folder within it."""
    logger = logging.getLogger(__name__)
    
    # Get the case folders under the root
    case_folders = injector.box_client.get_folder_items(root_id)
    case_folders = [f for f in case_folders if f['type'] == 'folder']
    
    if max_folders is not None:
        case_folders = case_folders[:max_folders]
    
    logger.info(f"Found {len(case_folders)} case folders under root {root_id}")
    
    if dry_run:
        logger.info("Dry run enabled, skipping actual processing")
        return {"status": "dry_run", "folders": len(case_folders)}
    
    # Process each case folder
    results = []
    for i, folder in enumerate(case_folders, 1):
        logger.info(f"\nProcessing case {i}/{len(case_folders)}: "
                   f"{folder['name']}")
        
        folder_result = process_single_folder(
            injector,
            folder_id=folder['id'],
            max_documents=max_documents,
            generate_timeline=generate_timeline
        )
        folder_result['case_name'] = folder['name']
        results.append(folder_result)
    
    # Summary
    total_success = sum(r.get('success', 0) for r in results)
    total_duplicates = sum(r.get('duplicates', 0) for r in results)
    total_failed = sum(r.get('failed', 0) for r in results)
    
    logger.info(f"Root folder processing complete: "
               f"{total_success} processed, "
               f"{total_duplicates} duplicates, "
               f"{total_failed} failed")
    
    return {
        "status": "complete",
        "root_id": root_id,
        "success": total_success,
        "duplicates": total_duplicates,
        "failed": total_failed,
        "folders": results
    }


def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Configure logging with UTF-8 support
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('clerk.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    logger.info("Clerk Document Injector starting...")
    logger.info(f"Configuration: {args}")
    
    # Handle shared knowledge initialization
    if args.init_shared_knowledge:
        logger.info("Initializing shared knowledge databases...")
        try:
            import asyncio
            from scripts.initialize_shared_knowledge import main as init_knowledge
            asyncio.run(init_knowledge())
            logger.info("Shared knowledge databases initialized successfully!")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Failed to initialize shared knowledge: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    # Validate settings
    if not settings.validate():
        logger.error("Invalid configuration. Please check your .env file.")
        sys.exit(1)
    
    try:
        # Initialize injector
        injector = DocumentInjector(
            enable_cost_tracking=not args.skip_cost_tracking,
            no_context=args.no_context,
            enable_fact_extraction=not args.skip_facts
        )
        
        # Test connections
        logger.info("Testing connections...")
        if not injector.box_client.check_connection():
            logger.error("Failed to connect to Box API")
            sys.exit(1)
        
        logger.info("Connections verified [OK]")
        
        # Process based on mode
        if args.folder_id:
            result = process_single_folder(
                injector, args.folder_id, 
                args.max_documents,
                args.generate_timeline
            )
        else:  # args.root
            result = process_root_folder(
                injector, args.root, args.max_folders,
                args.max_documents, args.dry_run,
                args.generate_timeline
            )
        
        # Save cost report if requested
        if args.save_cost_report and not args.skip_cost_tracking:
            if hasattr(injector, 'cost_tracker'):
                report_path = injector.cost_tracker.save_report()
                logger.info(f"Cost report saved to: {report_path}")
        
        # Print final status
        if result['status'] == 'complete':
            logger.info("Processing completed successfully!")
            sys.exit(0)
        else:
            logger.error("Processing failed or incomplete")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()