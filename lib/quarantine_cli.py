#!/usr/bin/env python3
"""
Quarantine CLI - Command line interface for managing quarantined prompts
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add lib directory to path
sys.path.append(str(Path(__file__).parent))

from secure_quarantine import SecureQuarantine


def list_quarantined_prompts(quarantine: SecureQuarantine, include_all: bool = False):
    """List quarantined prompts"""
    prompts = quarantine.list_quarantined_prompts(include_reviewed=include_all)
    
    if not prompts:
        print("📭 No quarantined prompts found")
        return
    
    print(f"📋 Found {len(prompts)} quarantined prompt(s)")
    print()
    
    for prompt in prompts:
        metadata = prompt["metadata"]
        filename = prompt["filename"]
        
        # Status indicators
        reviewed = metadata.get("reviewed", False)
        status_emoji = "✅" if reviewed else "⏳"
        
        # Source info
        source = metadata.get("source", "unknown")
        timestamp = metadata.get("quarantine_timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except:
                time_str = timestamp
        else:
            time_str = "Unknown"
        
        # Content info
        content_length = metadata.get("content_length", 0)
        content_hash = metadata.get("content_hash", "")[:8]
        
        print(f"{status_emoji} {filename}")
        print(f"   📅 Quarantined: {time_str}")
        print(f"   🌐 Source: {source}")
        print(f"   📏 Size: {content_length} bytes")
        print(f"   🔒 Hash: {content_hash}...")
        
        if reviewed:
            reviewer = metadata.get("reviewer", "unknown")
            review_time = metadata.get("review_timestamp", "")
            print(f"   👤 Reviewed by: {reviewer} at {review_time}")
        
        print()


def review_quarantined_prompt(quarantine: SecureQuarantine, filename: str):
    """Review a specific quarantined prompt"""
    file_path = quarantine.quarantine_root / filename
    
    if not file_path.exists():
        print(f"❌ Quarantine file not found: {filename}")
        return
    
    if not filename.startswith("Q-") or not filename.endswith(".md"):
        print(f"❌ Invalid quarantine filename format: {filename}")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse metadata
        if content.startswith("---\n"):
            parts = content.split("---\n", 2)
            if len(parts) >= 3:
                metadata_str = parts[1]
                file_content = parts[2]
                metadata = json.loads(metadata_str)
                
                print("🔍 QUARANTINE REVIEW")
                print("="*60)
                print()
                print(f"📄 File: {filename}")
                print(f"🌐 Source: {metadata.get('source', 'unknown')}")
                print(f"📅 Quarantined: {metadata.get('quarantine_timestamp', 'unknown')}")
                print(f"📏 Content Length: {metadata.get('content_length', 0)} bytes")
                print(f"🔒 Content Hash: {metadata.get('content_hash', 'unknown')}")
                print()
                
                if metadata.get("reviewed", False):
                    print("✅ ALREADY REVIEWED")
                    print(f"👤 Reviewer: {metadata.get('reviewer', 'unknown')}")
                    print(f"📅 Review Date: {metadata.get('review_timestamp', 'unknown')}")
                    review_notes = metadata.get('review_notes', '')
                    if review_notes:
                        print(f"📝 Notes: {review_notes}")
                    print()
                
                print("⚠️  WARNING: UNVERIFIED CONTENT BELOW ⚠️")
                print("="*60)
                print()
                print(file_content)
                print()
                print("="*60)
                print("⚠️  END OF UNVERIFIED CONTENT ⚠️")
                print()
                print("NEXT STEPS:")
                print("• To approve: computer quarantine approve -f {} -r YOUR_NAME".format(filename))
                print("• To reject:  computer quarantine reject -f {} -r YOUR_NAME".format(filename))
                print()
                print("🚨 NEVER execute this content without careful review and sanitization!")
                
    except Exception as e:
        print(f"❌ Error reading quarantine file: {e}")


def approve_quarantine(quarantine: SecureQuarantine, filename: str, reviewer: str, notes: str = ""):
    """Approve a quarantined prompt"""
    if not reviewer.strip():
        print("❌ Reviewer name cannot be empty")
        return
    
    if quarantine.mark_reviewed(filename, reviewer, f"APPROVED: {notes}"):
        print(f"✅ Quarantine {filename} approved by {reviewer}")
        if notes:
            print(f"📝 Notes: {notes}")
    else:
        print(f"❌ Failed to approve quarantine {filename}")


def reject_quarantine(quarantine: SecureQuarantine, filename: str, reviewer: str, notes: str = ""):
    """Reject a quarantined prompt"""
    if not reviewer.strip():
        print("❌ Reviewer name cannot be empty")
        return
    
    if quarantine.mark_reviewed(filename, reviewer, f"REJECTED: {notes}"):
        print(f"❌ Quarantine {filename} rejected by {reviewer}")
        if notes:
            print(f"📝 Notes: {notes}")
    else:
        print(f"❌ Failed to reject quarantine {filename}")


def show_quarantine_stats(quarantine: SecureQuarantine):
    """Show quarantine statistics"""
    stats = quarantine.get_quarantine_stats()
    
    print("📊 QUARANTINE STATISTICS")
    print("="*50)
    print()
    print(f"📁 Quarantine Directory: {stats['quarantine_path']}")
    print(f"📄 Total Files: {stats['total_files']}")
    print(f"✅ Reviewed: {stats['reviewed_count']}")
    print(f"⏳ Pending Review: {stats['pending_count']}")
    print(f"💾 Total Size: {stats['total_size_bytes']:,} bytes")
    print(f"🏠 Capacity Used: {stats['capacity_used_percent']:.1f}% of {stats['max_capacity']:,}")
    print()
    
    if stats['pending_count'] > 0:
        print("⚠️  ACTION REQUIRED:")
        print(f"   {stats['pending_count']} prompts need review")
        print("   Use: computer quarantine list")
        print()
    
    if stats['capacity_used_percent'] > 80:
        print("⚠️  WARNING: Quarantine approaching capacity")
        print("   Consider running: computer quarantine cleanup")
        print()


def cleanup_quarantine(quarantine: SecureQuarantine, days: int = 30):
    """Clean up old reviewed quarantine files"""
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    print(f"🧹 Cleaning quarantine files older than {days} days...")
    print(f"   Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    removed_count = 0
    total_size_removed = 0
    
    for file_path in quarantine.quarantine_root.glob("Q-*.md"):
        try:
            # Check if file is old enough
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
            if file_mtime >= cutoff_date:
                continue
            
            # Check if reviewed
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if content.startswith("---\n"):
                parts = content.split("---\n", 2)
                if len(parts) >= 3:
                    metadata = json.loads(parts[1])
                    if not metadata.get("reviewed", False):
                        continue  # Don't remove unreviewed items
            
            # Remove the file
            file_size = file_path.stat().st_size
            file_path.unlink()
            removed_count += 1
            total_size_removed += file_size
            
            print(f"🗑️  Removed: {file_path.name}")
            
        except Exception as e:
            print(f"⚠️  Error processing {file_path.name}: {e}")
    
    print()
    print(f"✅ Cleanup complete!")
    print(f"   Files removed: {removed_count}")
    print(f"   Space freed: {total_size_removed:,} bytes")
    
    if removed_count == 0:
        print("   No files met cleanup criteria")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Quarantine management CLI")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List quarantined prompts')
    list_parser.add_argument('--all', action='store_true', help='Include reviewed prompts')
    
    # Review command
    review_parser = subparsers.add_parser('review', help='Review a quarantined prompt')
    review_parser.add_argument('filename', help='Quarantine filename to review')
    
    # Approve command
    approve_parser = subparsers.add_parser('approve', help='Approve a quarantined prompt')
    approve_parser.add_argument('filename', help='Quarantine filename to approve')
    approve_parser.add_argument('reviewer', help='Reviewer name')
    approve_parser.add_argument('--notes', default='', help='Review notes')
    
    # Reject command
    reject_parser = subparsers.add_parser('reject', help='Reject a quarantined prompt')
    reject_parser.add_argument('filename', help='Quarantine filename to reject')
    reject_parser.add_argument('reviewer', help='Reviewer name')
    reject_parser.add_argument('--notes', default='', help='Review notes')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show quarantine statistics')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old quarantine files')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Days to keep (default: 30)')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize quarantine system
    try:
        quarantine = SecureQuarantine()
    except Exception as e:
        print(f"❌ Failed to initialize quarantine system: {e}")
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == 'list':
            list_quarantined_prompts(quarantine, args.all)
        elif args.command == 'review':
            review_quarantined_prompt(quarantine, args.filename)
        elif args.command == 'approve':
            approve_quarantine(quarantine, args.filename, args.reviewer, args.notes)
        elif args.command == 'reject':
            reject_quarantine(quarantine, args.filename, args.reviewer, args.notes)
        elif args.command == 'stats':
            show_quarantine_stats(quarantine)
        elif args.command == 'cleanup':
            cleanup_quarantine(quarantine, args.days)
        else:
            print(f"❌ Unknown command: {args.command}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()