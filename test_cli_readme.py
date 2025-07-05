#!/usr/bin/env python3
"""
Test script to verify all CLI commands documented in README work correctly.
Run this after refactoring to ensure nothing is broken.
"""

import tempfile
import os
import toml
from pathlib import Path
from simulchip.cli.main import NetrunnerProxyCLI


def test_init_commands():
    """Test initialization commands."""
    print("🧪 Testing init commands...")
    cli = NetrunnerProxyCLI()
    
    # Test TOML init
    with tempfile.NamedTemporaryFile(suffix='.toml', delete=True) as f:
        temp_file = f.name
    
    try:
        cli.init(temp_file)
        assert Path(temp_file).exists()
        print("✅ TOML init works")
        os.unlink(temp_file)
    except Exception as e:
        print(f"❌ TOML init failed: {e}")
    
    # Test default extension
    temp_file = "test_collection"
    
    try:
        cli.init(temp_file)
        expected_file = Path(temp_file + '.toml')
        assert expected_file.exists()
        print("✅ Default .toml extension added")
        os.unlink(expected_file)
    except Exception as e:
        print(f"❌ Default extension failed: {e}")


def test_pack_management():
    """Test pack management commands."""
    print("\n🧪 Testing pack management...")
    cli = NetrunnerProxyCLI()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        toml.dump({'packs': ['core'], 'cards': {}}, f)
        temp_file = f.name
    
    try:
        # Test add_pack
        cli.add_pack(temp_file, 'sg')
        print("✅ add_pack works")
        
        # Test remove_pack  
        cli.remove_pack(temp_file, 'core')
        print("✅ remove_pack works")
        
        # Test list_packs
        cli.list_packs()
        print("✅ list_packs works")
        
    except Exception as e:
        print(f"❌ Pack management failed: {e}")
    finally:
        os.unlink(temp_file)


def test_card_management():
    """Test individual card management."""
    print("\n🧪 Testing card management...")
    cli = NetrunnerProxyCLI()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        toml.dump({'packs': ['sg'], 'cards': {'34080': 3}}, f)
        temp_file = f.name
    
    try:
        # Test add
        cli.add(temp_file, '30001', count=2)
        print("✅ add works")
        
        # Test remove
        cli.remove(temp_file, '34080', count=1)
        print("✅ remove works")
        
        # Test mark_missing
        cli.mark_missing(temp_file, '34080', count=1)
        print("✅ mark_missing works")
        
        # Test found
        cli.found(temp_file, '34080', count=1)
        print("✅ found works")
        
    except Exception as e:
        print(f"❌ Card management failed: {e}")
    finally:
        os.unlink(temp_file)


def test_collection_info():
    """Test collection information commands."""
    print("\n🧪 Testing collection info...")
    cli = NetrunnerProxyCLI()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        toml.dump({
            'packs': ['sg'], 
            'cards': {'34080': 2},
            'missing': {'34080': 1}
        }, f)
        temp_file = f.name
    
    try:
        # Test stats
        cli.stats(temp_file)
        print("✅ stats works")
        
    except Exception as e:
        print(f"❌ Collection info failed: {e}")
    finally:
        os.unlink(temp_file)


def test_comparison():
    """Test decklist comparison."""
    print("\n🧪 Testing decklist comparison...")
    cli = NetrunnerProxyCLI()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        toml.dump({'packs': ['sg'], 'cards': {}}, f)
        temp_file = f.name
    
    try:
        # Test compare with full URL
        cli.compare('https://netrunnerdb.com/en/decklist/7a9e2d43-bd55-45d0-bd2c-99cad2d17d4c/test-deck', collection=temp_file)
        print("✅ compare with full URL works")
        
    except Exception as e:
        print(f"❌ Comparison failed: {e}")
    finally:
        os.unlink(temp_file)


def test_cache_management():
    """Test cache management."""
    print("\n🧪 Testing cache management...")
    cli = NetrunnerProxyCLI()
    
    try:
        # Test cache stats
        cli.cache(stats=True)
        print("✅ cache stats works")
        
        # Test cache clear
        cli.cache(clear=True)
        print("✅ cache clear works")
        
    except Exception as e:
        print(f"❌ Cache management failed: {e}")


def main():
    """Run all tests."""
    print("🚀 Testing all CLI commands from README...\n")
    
    test_init_commands()
    test_pack_management() 
    test_card_management()
    test_collection_info()
    test_comparison()
    test_cache_management()
    
    print("\n🎉 All CLI tests completed!")


if __name__ == '__main__':
    main()