#!/usr/bin/env python3
"""
Test Phase 2 ML module structure without loading torch.

This test verifies the code structure, imports, and basic
functionality without requiring ML dependencies to be installed.
"""
import sys
import os
from pathlib import Path
import ast

# Add python/src to path
project_root = Path(__file__).parent.parent
python_src = project_root / "python" / "src"

def test_file_exists(filepath: Path, name: str) -> bool:
    """Test if a file exists."""
    if filepath.exists():
        print(f"✅ {name} exists")
        return True
    else:
        print(f"❌ {name} missing")
        return False

def test_file_syntax(filepath: Path, name: str) -> bool:
    """Test if a Python file has valid syntax."""
    try:
        with open(filepath, 'r') as f:
            code = f.read()
        ast.parse(code)
        print(f"✅ {name} has valid syntax")
        return True
    except SyntaxError as e:
        print(f"❌ {name} has syntax error: {e}")
        return False

def test_file_has_classes(filepath: Path, expected_classes: list, name: str) -> bool:
    """Test if a file contains expected classes."""
    try:
        with open(filepath, 'r') as f:
            code = f.read()
        tree = ast.parse(code)
        
        classes_found = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        missing = set(expected_classes) - set(classes_found)
        if missing:
            print(f"⚠️  {name} missing classes: {missing}")
            return False
        else:
            print(f"✅ {name} has all expected classes: {expected_classes}")
            return True
    except Exception as e:
        print(f"❌ Failed to check classes in {name}: {e}")
        return False

def test_file_has_functions(filepath: Path, expected_functions: list, name: str) -> bool:
    """Test if a file contains expected functions."""
    try:
        with open(filepath, 'r') as f:
            code = f.read()
        tree = ast.parse(code)
        
        functions_found = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        
        missing = set(expected_functions) - set(functions_found)
        if missing:
            print(f"⚠️  {name} missing functions: {missing}")
            return False
        else:
            print(f"✅ {name} has all expected functions")
            return True
    except Exception as e:
        print(f"❌ Failed to check functions in {name}: {e}")
        return False

def main():
    """Run all structure tests."""
    print("=" * 70)
    print("Phase 2 ML Modules Structure Test")
    print("=" * 70)
    print()
    
    results = []
    
    # Test translation_pipeline.py
    print("=" * 70)
    print("TRANSLATION PIPELINE MODULE")
    print("=" * 70)
    translation_file = python_src / "ai" / "translation_pipeline.py"
    results.append(test_file_exists(translation_file, "translation_pipeline.py"))
    results.append(test_file_syntax(translation_file, "translation_pipeline.py"))
    results.append(test_file_has_classes(
        translation_file,
        ["TranslationConfig", "DeviceManager", "ASRModule", "NMTModule", "TTSModule", "TranslationPipeline"],
        "translation_pipeline.py"
    ))
    print()
    
    # Test video_lipsync.py
    print("=" * 70)
    print("VIDEO LIPSYNC MODULE")
    print("=" * 70)
    lipsync_file = python_src / "ai" / "video_lipsync.py"
    results.append(test_file_exists(lipsync_file, "video_lipsync.py"))
    results.append(test_file_syntax(lipsync_file, "video_lipsync.py"))
    results.append(test_file_has_classes(
        lipsync_file,
        ["LipsyncConfig", "FaceDetector", "LipsyncModel", "VideoLipsync", "VideoTranslationPipeline"],
        "video_lipsync.py"
    ))
    print()
    
    # Test federated_learning.py
    print("=" * 70)
    print("FEDERATED LEARNING MODULE")
    print("=" * 70)
    fl_file = python_src / "ai" / "federated_learning.py"
    results.append(test_file_exists(fl_file, "federated_learning.py"))
    results.append(test_file_syntax(fl_file, "federated_learning.py"))
    results.append(test_file_has_classes(
        fl_file,
        ["FederatedConfig", "CustomSerializationModel", "ModelWeightManager", 
         "LocalTrainer", "FederatedAggregator", "P2PFederatedLearning"],
        "federated_learning.py"
    ))
    print()
    
    # Test documentation
    print("=" * 70)
    print("DOCUMENTATION")
    print("=" * 70)
    doc_file = project_root / "docs" / "PHASE2_ML_IMPLEMENTATION.md"
    results.append(test_file_exists(doc_file, "PHASE2_ML_IMPLEMENTATION.md"))
    print()
    
    # Check file sizes (should have substantial content)
    print("=" * 70)
    print("FILE SIZES")
    print("=" * 70)
    files_to_check = [
        (translation_file, "translation_pipeline.py", 10000),
        (lipsync_file, "video_lipsync.py", 10000),
        (fl_file, "federated_learning.py", 10000),
        (doc_file, "PHASE2_ML_IMPLEMENTATION.md", 10000)
    ]
    
    for filepath, name, min_size in files_to_check:
        if filepath.exists():
            size = filepath.stat().st_size
            if size >= min_size:
                print(f"✅ {name}: {size:,} bytes (>= {min_size:,})")
                results.append(True)
            else:
                print(f"⚠️  {name}: {size:,} bytes (< {min_size:,})")
                results.append(False)
    print()
    
    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL STRUCTURE TESTS PASSED!")
        print("\nNote: Full module tests require PyTorch to be installed.")
        print("Run: pip install torch>=2.0.0 numpy>=1.24.0")
        return 0
    else:
        print(f"\n❌ {total - passed} TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
