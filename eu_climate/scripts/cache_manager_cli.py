#!/usr/bin/env python3
"""
EU Climate Cache Management CLI
==============================

Command-line interface for managing the EU Climate Risk Assessment caching system.
Provides tools for viewing cache statistics, clearing cache data, and performing maintenance.

Usage:
    python cache_manager_cli.py --stats              # Show cache statistics
    python cache_manager_cli.py --clear all          # Clear all cache data
    python cache_manager_cli.py --clear raster_data  # Clear specific cache type
    python cache_manager_cli.py --cleanup 7          # Remove files older than 7 days
    python cache_manager_cli.py --size               # Show detailed size breakdown
"""

import sys
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from eu_climate.config.config import ProjectConfig
from eu_climate.utils.cache_utils import get_cache_integrator
from eu_climate.utils.utils import setup_logging

logger = setup_logging(__name__)


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description='EU Climate Risk Assessment Cache Management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --stats                    Show cache statistics
  %(prog)s --clear all                Clear all cache data
  %(prog)s --clear raster_data        Clear raster data cache only
  %(prog)s --cleanup 7                Remove files older than 7 days
  %(prog)s --size                     Show detailed size breakdown
  %(prog)s --info                     Show cache configuration
        """
    )
    
    parser.add_argument('--stats', action='store_true',
                       help='Show cache statistics')
    parser.add_argument('--clear', 
                       choices=['all', 'raster_data', 'calculations', 'final_results'],
                       help='Clear cache data')
    parser.add_argument('--cleanup', type=int, metavar='DAYS',
                       help='Remove cache files older than N days')
    parser.add_argument('--size', action='store_true',
                       help='Show cache size breakdown')
    parser.add_argument('--info', action='store_true',
                       help='Show cache configuration information')
    parser.add_argument('--enable', action='store_true',
                       help='Enable caching (modifies config)')
    parser.add_argument('--disable', action='store_true',
                       help='Disable caching (modifies config)')
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    try:
        # Initialize project configuration
        config = ProjectConfig()
        logger.info(f"Using project directory: {config.data_dir}")
        
        # Get cache integrator
        integrator = get_cache_integrator(config)
        
        # Handle different commands
        if args.stats:
            show_statistics(integrator)
            
        if args.clear:
            clear_cache(integrator, args.clear)
            
        if args.cleanup:
            cleanup_cache(integrator, args.cleanup)
            
        if args.size:
            show_size_breakdown(integrator)
            
        if args.info:
            show_cache_info(integrator)
            
        if args.enable:
            toggle_caching(config, True)
            
        if args.disable:
            toggle_caching(config, False)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def show_statistics(integrator):
    """Show cache statistics."""
    print("\n" + "="*60)
    print("EU CLIMATE CACHE STATISTICS")
    print("="*60)
    
    integrator.print_cache_statistics()


def clear_cache(integrator, cache_type):
    """Clear cache data."""
    print(f"\nClearing {cache_type} cache...")
    
    if cache_type == 'all':
        removed = integrator.clear_cache()
    else:
        removed = integrator.clear_cache(cache_type)
        
    print(f"✓ Cleared {cache_type} cache")


def cleanup_cache(integrator, max_age_days):
    """Clean up old cache files."""
    print(f"\nCleaning up cache files older than {max_age_days} days...")
    
    integrator.cleanup_cache(max_age_days)
    print(f"✓ Cache cleanup completed")


def show_size_breakdown(integrator):
    """Show detailed cache size breakdown."""
    cache_info = integrator.get_cache_info()
    
    print(f"\n" + "="*50)
    print("CACHE SIZE BREAKDOWN")
    print("="*50)
    print(f"Total Cache Size: {cache_info['total_size_gb']:.2f} GB")
    print(f"Max Cache Size: {cache_info['max_size_gb']} GB")
    print()
    
    if cache_info['breakdown']:
        for cache_type, info in cache_info['breakdown'].items():
            print(f"{cache_type.replace('_', ' ').title()}:")
            print(f"  Files: {info['file_count']}")
            print(f"  Size: {info['size_mb']:.1f} MB")
            print(f"  Directory: {info['directory']}")
            print()
    else:
        print("No cache data found.")


def show_cache_info(integrator):
    """Show cache configuration information."""
    cache_info = integrator.get_cache_info()
    
    print(f"\n" + "="*50)
    print("CACHE CONFIGURATION")
    print("="*50)
    print(f"Status: {'Enabled' if cache_info['enabled'] else 'Disabled'}")
    print(f"Cache Directory: {cache_info['cache_dir']}")
    print(f"Current Size: {cache_info['total_size_gb']:.2f} GB")
    print(f"Maximum Size: {cache_info['max_size_gb']} GB")
    print(f"Auto Cleanup: {integrator.cache_manager.auto_cleanup}")
    print()
    
    print("Cache Types:")
    for cache_type, cache_dir in integrator.cache_manager.cache_dirs.items():
        exists = "✓" if cache_dir.exists() else "✗"
        print(f"  {exists} {cache_type}: {cache_dir}")


def toggle_caching(config, enable):
    """Toggle caching on/off (requires config modification)."""
    status = "enabled" if enable else "disabled"
    print(f"\nNote: To {'enable' if enable else 'disable'} caching, modify the 'caching.enabled' ")
    print(f"setting in your configuration file: eu_climate/config/data_config.yaml")
    print(f"Set 'enabled: {'true' if enable else 'false'}' in the caching section.")


if __name__ == "__main__":
    main() 